#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wandelt "101 google docs Lager - schon uebersetzt.txt" in Wikivorlagen um,
die wiki2wp.py versteht.

Quellstruktur je Witz:
    ----------------------
    :Version 1
    :ungarischer Satz - deutscher Satz
    ...
    :Version 2
    ...

Jede Version wird ein eigener Witz mit Buchstabensuffix (1a, 1b, 1c), so wie
es auf den Seiten 01 bis 23 schon steht. Die Versionen bleiben erhalten -
fuer Sprachschueler sind mehrere Fassungen desselben Witzes ein Gewinn.
"""

import re
import sys

# Der Bindestrich zwischen ungarischem und deutschem Satz ist mal ein
# Halbgeviertstrich, mal ein einfacher Bindestrich. Beide gelten.
TRENNER = re.compile(r" [-–—] ")

UNG_WOERTER = set("""a az és hogy nem egy van meg de is már csak mint ki fel le
azt ez ezt mondja kérdezi felel ha még nincy nincs lesz volt vagy sem itt ott
nő férfi mit mi miért hol akkor majd ön te én mi ti ők""".split())

DE_WOERTER = set("""der die das den dem des ein eine einen einem einer ist sind
war nicht und sich zu von mit auf für dass er sie es ich du wir ihr man aber
sagt fragt antwortet wenn als noch nur schon auch so dann bei nach vor über""".split())

UNG_ZEICHEN = set("őűáéíóúŐŰÁÉÍÓÚ")


def woerter(text):
    return re.findall(r"[^\W\d_]+", text.lower(), flags=re.UNICODE)


def ung_punkte(text):
    w = woerter(text)
    if not w:
        return 0.0
    treffer = sum(1 for x in w if x in UNG_WOERTER)
    zeichen = sum(1 for c in text if c in UNG_ZEICHEN)
    return treffer / len(w) + min(zeichen, 8) / 40.0


def de_punkte(text):
    w = woerter(text)
    if not w:
        return 0.0
    return sum(1 for x in w if x in DE_WOERTER) / len(w)


def klammern_richten(links, rechts):
    """"(ung - dt)" wird beim Teilen zu "(ung" und "dt)" - beides reparieren."""
    if links.startswith("(") and not links.endswith(")"):
        links += ")"
    if rechts.endswith(")") and not rechts.startswith("("):
        rechts = "(" + rechts
    return links, rechts


def teilen(zeile):
    """Zerlegt "ungarisch - deutsch" in beide Haelften.

    Mehrere Trennstriche in einer Zeile sind moeglich ("Nur der Tod ist
    umsonst - und nicht einmal der."). Deshalb wird nicht der erste Strich
    genommen, sondern der, bei dem links am meisten Ungarisch und rechts am
    meisten Deutsch steht.
    """
    stellen = [m.span() for m in TRENNER.finditer(zeile)]
    if not stellen:
        return None
    bestes, bester_wert = None, None
    for a, b in stellen:
        links, rechts = zeile[:a].strip(), zeile[b:].strip()
        if not links or not rechts:
            continue
        wert = (ung_punkte(links) + de_punkte(rechts)
                - ung_punkte(rechts) - de_punkte(links))
        if bester_wert is None or wert > bester_wert:
            bestes, bester_wert = (links, rechts), wert
    if bestes is None:
        return None
    return klammern_richten(*bestes)


def bloecke_lesen(pfad):
    """Die Datei zerfaellt an den Strichlinien in Witze, die Witze in Versionen."""
    roh = open(pfad, encoding="utf-8").read().splitlines()
    bloecke, cur = [], []
    for zeile in roh:
        if re.fullmatch(r"-{4,}", zeile.strip()):
            if any(l.strip() for l in cur):
                bloecke.append(cur)
            cur = []
        else:
            cur.append(zeile)
    if any(l.strip() for l in cur):
        bloecke.append(cur)

    witze = []
    for block in bloecke:
        versionen, aktuell = [], None
        for zeile in block:
            s = zeile.strip()
            if not s:
                continue
            if s.startswith("[[File:"):
                # Wikimedia-Bilder gibt es auf modjor.de nicht.
                continue
            if s.startswith(":Version"):
                aktuell = []
                versionen.append(aktuell)
                continue
            if aktuell is None:
                # Witz ohne ":Version"-Zeile - eine einzige Fassung
                aktuell = []
                versionen.append(aktuell)
            aktuell.append(s.lstrip(":").strip())
        versionen = [v for v in versionen if v]
        if versionen:
            witze.append(versionen)
    return witze


def wiki_witz(nummer, zeilen, bericht):
    """Eine Fassung als Wikivorlage: ungarisch, Satzpaare, deutsch."""
    paare = []
    for zeile in zeilen:
        geteilt = teilen(zeile)
        if geteilt is None:
            bericht.append(f"Witz {nummer}: kein Trennstrich -> {zeile[:90]}")
            geteilt = (zeile, zeile)
        paare.append(geteilt)

    o = [f"=== {nummer} ==="]
    for i, (hu, _) in enumerate(paare, start=1):
        o.append(f":{i}. {hu}")
    o += ["{|", "!'''magyar - német'''", "|-", "|"]
    for i, (hu, de) in enumerate(paare, start=1):
        o.append(f":{i}. {hu} - {de}")
    o += ["|}", "{|", "!'''deutsch'''", "|-", "|"]
    for i, (_, de) in enumerate(paare, start=1):
        o.append(f":{i}. {de}")
    o += ["|}", ""]
    return o


VORSPANN = [";rövid viccek - kurze Witze",
            ":An einigen Stellen steht hinter dem ungarischen Wort zusätzlich "
            "die Aussprache in eckigen Klammern. Beispiel: Segíts [segíccs] "
            "magadon!",
            ""]


def main():
    quelle, seiten = sys.argv[1], int(sys.argv[2])
    ziele = sys.argv[3:]
    if len(ziele) != seiten:
        sys.exit("Anzahl der Zieldateien passt nicht zur Seitenzahl")

    witze = bloecke_lesen(quelle)
    bericht = []

    # Gleichmaessig aufteilen, ohne einen Witz von seinen Fassungen zu trennen
    pro_seite = -(-len(witze) // seiten)
    haufen = [witze[i:i + pro_seite] for i in range(0, len(witze), pro_seite)]
    while len(haufen) < seiten:
        haufen.append([])

    for ziel, haufen_seite in zip(ziele, haufen):
        o = list(VORSPANN)
        for nr, versionen in enumerate(haufen_seite, start=1):
            if len(versionen) == 1:
                o += wiki_witz(str(nr), versionen[0], bericht)
            else:
                for stelle, zeilen in enumerate(versionen):
                    o += wiki_witz(f"{nr}{chr(ord('a') + stelle)}", zeilen,
                                   bericht)
        open(ziel, "w", encoding="utf-8").write("\n".join(o) + "\n")
        sys.stderr.write(f"{len(haufen_seite)} Witze -> {ziel}\n")

    for zeile in bericht:
        sys.stderr.write("HINWEIS: " + zeile + "\n")


if __name__ == "__main__":
    main()
