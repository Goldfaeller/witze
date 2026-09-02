#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zerlegt die drei langen Seiten in kürzere und nummeriert sie neu.

Seite 42 wird an ihren Abschnittsüberschriften getrennt, die beiden anderen
nach Länge - dort gibt es keine thematische Gliederung.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from seite_zerlegen import zerlegen  # noqa: E402

GRENZE = 45000

FUSS = """<!-- wp:separator -->
<hr class="wp-block-separator has-alpha-channel-opacity"/>
<!-- /wp:separator -->

<!-- wp:html -->
<div class="pc-footer-nav">
  <div class="pc-top-link"><a href="#top">↑ Hoch zum Seitenanfang</a></div>
NAV  <div class="pc-home-link">
  HOME
</div>
</div>
<!-- /wp:html --></div>
<!-- /wp:group -->
"""


def ausgeglichen(laengen, anzahl, grenze):
    """Gleichmäßigste Aufteilung in 'anzahl' Teile, keiner über 'grenze'."""
    n = len(laengen)
    summe = [0] * (n + 1)
    for i, l in enumerate(laengen):
        summe[i + 1] = summe[i] + l
    mittel = summe[n] / anzahl
    unendlich = float("inf")
    bester = [[(unendlich, -1)] * (anzahl + 1) for _ in range(n + 1)]
    bester[0][0] = (0.0, -1)
    for k in range(1, anzahl + 1):
        for i in range(1, n + 1):
            for j in range(k - 1, i):
                vorher = bester[j][k - 1][0]
                if vorher == unendlich:
                    continue
                laenge = summe[i] - summe[j]
                if laenge > grenze:
                    continue
                kosten = vorher + (laenge - mittel) ** 2
                if kosten < bester[i][k][0]:
                    bester[i][k] = (kosten, j)
    if bester[n][anzahl][0] == unendlich:
        return None
    grenzen, i = [], n
    for k in range(anzahl, 0, -1):
        j = bester[i][k][1]
        grenzen.append((j, i))
        i = j
    return [list(range(j, i)) for j, i in reversed(grenzen)]


def nach_laenge(bloecke, grenze):
    laengen = [len(b) for b in bloecke]
    anzahl = max(1, -(-sum(laengen) // grenze))
    while anzahl <= len(bloecke):
        loesung = ausgeglichen(laengen, anzahl, grenze)
        if loesung:
            return loesung
        anzahl += 1
    raise SystemExit("Aufteilung nicht möglich")


def nach_abschnitten(bloecke, grenze):
    """An den Abschnittsüberschriften trennen, kleine Abschnitte bündeln,
    zu große weiter unterteilen."""
    grenzen = [i for i, b in enumerate(bloecke) if "pc-gruppe" in b]
    if not grenzen:
        return nach_laenge(bloecke, grenze)
    if grenzen[0] != 0:
        grenzen.insert(0, 0)
    abschnitte = []
    for k, start in enumerate(grenzen):
        ende = grenzen[k + 1] if k + 1 < len(grenzen) else len(bloecke)
        abschnitte.append(list(range(start, ende)))

    seiten, jetzt = [], []
    for absch in abschnitte:
        gross = sum(len(bloecke[i]) for i in absch)
        offen = sum(len(bloecke[i]) for i in jetzt)
        if gross > grenze:
            if jetzt:
                seiten.append(jetzt)
                jetzt = []
            teile = nach_laenge([bloecke[i] for i in absch], grenze)
            seiten.extend([[absch[i] for i in t] for t in teile])
            continue
        if jetzt and offen + gross > grenze:
            seiten.append(jetzt)
            jetzt = []
        jetzt.extend(absch)
    if jetzt:
        seiten.append(jetzt)
    return seiten


def neu_nummerieren(bloecke):
    """Zählung auf jeder Seite wieder ab 1, das Wort davor bleibt stehen."""
    out, n = [], 0
    for b in bloecke:
        def ersetze(m):
            nonlocal n
            n += 1
            return f'<h3 class="wp-block-heading">{m.group(1).strip()} {n}</h3>'
        out.append(re.sub(r'<h3 class="wp-block-heading">(.*?)\s+\d+</h3>',
                          ersetze, b))
    return out


def navzeile(nr, teil, teile, basis, zurueck_aussen, weiter_aussen):
    """Beschriftet wird mit der Seitennummer, nicht mit der Nummer innerhalb
    der Reihe - so tragen Permalink und Aufschrift dieselbe Zahl."""
    links = (zurueck_aussen if teil == 1 else
             f'<a href="/{nr - 1}-witze/">« Zurück zu {basis} {nr - 1}</a>')
    rechts = (weiter_aussen if teil == teile else
              f'<a href="/{nr + 1}-witze/">Weiter zu {basis} {nr + 1} »</a>')
    return (f'<div class="pc-chapter-nav">\n  {links} &nbsp;|&nbsp; '
            f'<span>{basis} {nr}</span> &nbsp;|&nbsp; {rechts}\n</div>\n')


def main():
    plan = json.load(open(sys.argv[1], encoding="utf-8"))
    grenze = plan.get("grenze", GRENZE)

    # Erster Durchgang: aufteilen und zählen, damit die Verweise zwischen den
    # Reihen auf die richtigen Nummern zeigen können
    reihen = []
    for auftrag in plan["seiten"]:
        text = open(auftrag["datei"], encoding="utf-8").read()
        kopf, vorspann, bloecke, _ = zerlegen(text)
        weg = set(auftrag.get("entfernen", []))
        if weg:
            bloecke = [b for i, b in enumerate(bloecke) if i not in weg]
        aufteilung = (nach_abschnitten if auftrag.get("thematisch")
                      else nach_laenge)(bloecke, grenze)
        home = re.search(r'<div class="pc-home-link">\s*\n\s*(.*)', text).group(1)
        reihen.append({"auftrag": auftrag, "kopf": kopf, "vorspann": vorspann,
                       "bloecke": bloecke, "aufteilung": aufteilung, "home": home})

    nr = plan["erste_nummer"]
    for r in reihen:
        r["erste"] = nr
        nr += len(r["aufteilung"])
    letzte = nr - 1

    # Zweiter Durchgang: schreiben
    uebersicht = []
    for k, r in enumerate(reihen):
        auftrag = r["auftrag"]
        teile = len(r["aufteilung"])
        # Der Verweis nach außen zeigt auf die erste Seite der nächsten Reihe
        if k + 1 < len(reihen):
            ziel = reihen[k + 1]
            weiter = (f'<a href="/{ziel["erste"]}-witze/">Weiter zu - '
                      f'{ziel["auftrag"]["basis"]} {ziel["erste"]} »</a>')
        else:
            weiter = auftrag["weiter"]
        if k > 0:
            vorige = reihen[k - 1]
            letzte_vorige = vorige["erste"] + len(vorige["aufteilung"]) - 1
            zurueck = (f'<a href="/{letzte_vorige}-witze/">« Zurück zu - '
                       f'{vorige["auftrag"]["basis"]} {letzte_vorige}</a>')
        else:
            zurueck = auftrag["zurueck"]

        for t, gruppe in enumerate(r["aufteilung"], start=1):
            nummer = r["erste"] + t - 1
            nav = navzeile(nummer, t, teile, auftrag["basis"], zurueck, weiter)
            inhalt = neu_nummerieren([r["bloecke"][i] for i in gruppe])
            seite = (r["kopf"] + nav + r["vorspann"] + "".join(inhalt)
                     + FUSS.replace("NAV", "  " + nav).replace("HOME", r["home"]))
            pfad = f"wordpress/{nummer}-witze.txt"
            open(pfad, "w", encoding="utf-8").write(seite)
            json.dump({"post_type": "page",
                       "post_title": f"{auftrag['basis']} {nummer}",
                       "post_name": f"{nummer}-witze", "post_parent": "Witze",
                       "menu_order": nummer, "content_file": pfad},
                      open(f"wordpress/{nummer}-witze.meta.json", "w",
                           encoding="utf-8"), ensure_ascii=False, indent=2)
            uebersicht.append((pfad, auftrag["basis"], t, teile,
                               len(gruppe), len(seite)))

    print(f"{'Datei':<26}{'Reihe':<22}{'Teil':>6}{'Eintraege':>11}{'Zeichen':>9}")
    for pfad, basis, t, teile, eintraege, zeichen in uebersicht:
        print(f"{pfad:<26}{basis:<22}{f'{t}/{teile}':>6}{eintraege:>11}{zeichen:>9}")
    print(f"\n{len(uebersicht)} Seiten, Nummern {plan['erste_nummer']} bis {letzte}")


if __name__ == "__main__":
    main()
