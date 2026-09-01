#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trennt eine gemischte Zeile "ungarisch - deutsch" in ihre beiden Hälften.

Im Rohmaterial steht das Satzpaar in einer Zeile, getrennt durch einen
Gedankenstrich. Der Strich kommt aber auch innerhalb der ungarischen wie der
deutschen Hälfte vor ("mosolys - mosolygás - das Lächeln"), deshalb wird
nicht stur am ersten Strich getrennt: jede mögliche Trennstelle wird bewertet,
und es gewinnt die Stelle, bei der links am ungarischsten und rechts am
deutschsten gelesen wird.
"""

import re
import unicodedata

DE_WORDS = set("""
der die das dem den des ein eine einen einem einer eines und ist sind war waren
nicht kein keine keinen ich du er sie es wir ihr man dass daß mit von zu zum zur
auf für sich hat habe haben hatte hatten wird werden wurde wurden worden so auch
aber wie was wer warum weil wenn im in an am bei aus nach über unter vor durch
gegen ohne oder als nur noch schon sehr mehr etwas nichts jemand niemand machen
macht tun sagen sagt sagte kann können muss müssen soll sollen will wollen möchte
gut schlecht viel wenig sein seine ihre unser euer dieser diese dieses jeder alle
herr frau mann kind jahr tag mal sich zurück wieder immer nie jetzt dann dort hier
""".split())

HU_WORDS = set("""
a az egy és s hogy nem van vannak nincs sincs ez ezt ebben azt annak abban mi ki
te ti ők ön önök is de mint csak már még nagyon volt lesz lenne legyen lehet kell
tud tudja akar megy jön ad vesz lát hall mond mondja kérdez így úgy ott itt ide oda
amikor mert vagy vagyok vagyunk sem se meg el fel le be át rá hozzá neki nekem
neked minden semmi valaki valami olyan ilyen ilyen aki ami amely után előtt alatt
felett között nélkül miatt szerint való való ha majd talán persze igen jó rossz sok
kevés ember év nap alkalommal fog fogja kérem köszönöm uram
""".split())

HU_ONLY_CHARS = "őűŐŰ"
DE_ONLY_CHARS = "ßäÄ"

# Tippfehler der Vorlage, die die Trennung sonst ins Leere laufen lassen
KORREKTUREN = {
    "hajléktalan . obdachlos": "hajléktalan - obdachlos",  # Punkt statt Strich
    "fuldoklik -": "fuldoklik",                            # Strich ohne Übersetzung
}
# Zeilen, denen das ungarische Gegenstück fehlt
NUR_DEUTSCH = {"wetten"}


def words(text):
    return [w for w in re.split(r"[^0-9A-Za-zÀ-ÖØ-öø-ÿőűŐŰ]+", text.lower()) if w]


def german_score(text):
    """> 0 heißt: liest sich deutsch, < 0 heißt: liest sich ungarisch."""
    if not text.strip():
        return 0.0
    ws = words(text)
    de = sum(1 for w in ws if w in DE_WORDS)
    hu = sum(1 for w in ws if w in HU_WORDS)
    score = float(de - hu)
    score += 2.0 * sum(text.count(c) for c in DE_ONLY_CHARS)
    score -= 2.0 * sum(text.count(c) for c in HU_ONLY_CHARS)
    # Anführungszeichen: „…“ ist deutsch, „…” ist ungarisch gesetzt
    score += 1.0 * text.count("“")
    score -= 1.0 * text.count("”")
    # deutsche Substantivgroßschreibung mitten im Satz
    inner = re.findall(r"(?<=[a-zäöüß] )([A-ZÄÖÜ][a-zäöüß]{3,})", text)
    score += 0.5 * len(inner)
    return score


# Gedankenstrich mit Leerzeichen. Beim Halbgeheimnis " -die Seele" fehlt rechts
# das Leerzeichen, beim Gedankenstrich hinter einer Klammer ")– " links.
SPLIT_RE = re.compile(r"\s*[–—]\s+|\s+-\s*(?=\S)|(?<=\S)-\s+")
EQ_RE = re.compile(r"\s+=\s+")


def nur_klammern(text):
    return text.count("(") == text.count(")") and text.count("[") == text.count("]")


def ausgewogen(text):
    """Klammern und Anführungszeichen paarweise geschlossen?"""
    if text.count("(") != text.count(")"):
        return False
    if text.count("[") != text.count("]"):
        return False
    if sum(text.count(c) for c in "„“”\"") % 2:
        return False
    return True


def split_pair(line):
    """
    Liefert (ungarisch, deutsch, sicherheit).
    sicherheit: 'sicher' | 'unsicher' | 'nur-ungarisch' | 'nur-deutsch'
    Bei 'nur-*' ist die jeweils andere Hälfte None.
    """
    text = KORREKTUREN.get(line.strip(), line.strip())
    if text in NUR_DEUTSCH:
        return (None, text, "nur-deutsch")

    # Ganz eingeklammerte Zeile: innen trennen, Klammern bleiben auf beiden Seiten
    if (text.startswith("(") and text.endswith(")")
            and ausgewogen(text[1:-1])):
        hu, de, status = split_pair(text[1:-1])
        if status in ("sicher", "unsicher"):
            return (f"({hu})", f"({de})", status)

    cands = [(m.start(), m.end()) for m in SPLIT_RE.finditer(text)]
    if not cands:
        cands = [(m.start(), m.end()) for m in EQ_RE.finditer(text)]
    if not cands:
        s = german_score(text)
        if s > 0:
            return (None, text, "nur-deutsch")
        return (text, None, "nur-ungarisch")

    def kandidaten(pruefung):
        out = []
        for a, b in cands:
            left, right = text[:a].strip(), text[b:].strip()
            if not left or not right or not pruefung(left) or not pruefung(right):
                continue
            out.append((german_score(right) - german_score(left), left, right))
        return out

    # Erst streng: weder Klammer noch Zitat aufschneiden.
    bewertet = kandidaten(ausgewogen)
    if not bewertet:
        # Dann nachsichtig: in mehrzeiligen Zitaten steht das schließende
        # Anführungszeichen erst Zeilen später, Klammern bleiben aber tabu.
        bewertet = kandidaten(nur_klammern)
    if not bewertet:
        if ausgewogen(text):
            # Der Strich steckt in einer Klammer - die Zeile bleibt ganz
            return (text, text, "ungetrennt")
        # Klammer oder Anführungszeichen in der Vorlage nicht geschlossen:
        # dann ohne die Klammerprüfung trennen und zum Nachsehen melden
        for a, b in cands:
            left, right = text[:a].strip(), text[b:].strip()
            if left and right:
                bewertet.append((german_score(right) - german_score(left),
                                 left, right))
        if not bewertet:
            return (text, text, "ungetrennt")
        wert, left, right = max(bewertet, key=lambda t: t[0])
        return (left, right, "unsicher")

    # Bester Wert; bei Gleichstand die spätere Trennstelle (Wortlisten führen
    # erst mehrere ungarische Varianten auf und danach die Übersetzung)
    hoechst = max(v for v, _, _ in bewertet)
    value, left, right = [t for t in bewertet if t[0] >= hoechst - 0.01][-1]

    # Bei nur einer möglichen Trennstelle gibt es nichts zu verwechseln
    if len(bewertet) == 1:
        return (left, right, "sicher")

    werte = sorted((v for v, _, _ in bewertet), reverse=True)
    sicher = "unsicher" if werte[0] - werte[1] < 1.0 or value <= 0 else "sicher"
    return (left, right, sicher)
