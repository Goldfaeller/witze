#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baut aus den Eintraegen von Lager 102 und den Uebersetzungschargen die
Wikivorlagen, die wiki2wp.py in Seiten verwandelt - getrennt nach Witzen
und Spruechen.

Aufgeteilt wird nach der Menge an Satzpaaren, nicht nach der Zahl der
Eintraege: ein Eintrag kann ein Zweizeiler sein oder ein langer Witz.
"""

import json
import re
import sys

sys.path.insert(0, "tools")
from ung_pruefen import chargen_lesen           # noqa: E402


def stuecke_sammeln(eintraege, ung):
    """-> Liste von (art, [(ungarisch, deutsch), ...]) in Quellreihenfolge."""
    out = []
    for e in eintraege:
        teile = ung.get(e["nr"])
        if not teile:
            continue
        i = 0
        for t in teile:
            n = len(t["zeilen"])
            out.append((t["art"],
                        list(zip(t["zeilen"], e["dt"][i:i + n]))))
            i += n
    return out


def wiki_eintrag(nummer, paare):
    o = [f"=== {nummer} ==="]
    o += [f":{i}. {hu}" for i, (hu, _) in enumerate(paare, start=1)]
    o += ["{|", "!'''magyar - német'''", "|-", "|"]
    o += [f":{i}. {hu} - {de}" for i, (hu, de) in enumerate(paare, start=1)]
    o += ["|}", "{|", "!'''deutsch'''", "|-", "|"]
    o += [f":{i}. {de}" for i, (_, de) in enumerate(paare, start=1)]
    o += ["|}", ""]
    return o


def vorspann(art):
    kopf = ("rövid viccek - kurze Witze" if art == "witz"
            else "mondások - Sprüche")
    return [f";{kopf}",
            ":An einigen Stellen steht hinter dem ungarischen Wort zusätzlich "
            "die Aussprache in eckigen Klammern. Beispiel: Segíts [segíccs] "
            "magadon!",
            ""]


def aufteilen(stuecke, paare_pro_seite):
    seiten, aktuell, menge = [], [], 0
    for art, paare in stuecke:
        if aktuell and menge + len(paare) > paare_pro_seite:
            seiten.append(aktuell)
            aktuell, menge = [], 0
        aktuell.append(paare)
        menge += len(paare)
    if aktuell:
        seiten.append(aktuell)
    return seiten


def main():
    eintraege = json.load(open(sys.argv[1], encoding="utf-8"))
    ung = chargen_lesen(sys.argv[2])
    art = sys.argv[3]
    erste_nummer = int(sys.argv[4])
    paare_pro_seite = int(sys.argv[5])

    stuecke = [s for s in stuecke_sammeln(eintraege, ung) if s[0] == art]
    seiten = aufteilen(stuecke, paare_pro_seite)

    for versatz, seite in enumerate(seiten):
        nr = erste_nummer + versatz
        o = vorspann(art)
        for lfd, paare in enumerate(seite, start=1):
            o += wiki_eintrag(str(lfd), paare)
        ziel = f"arbeit/wiki/{nr}.txt"
        open(ziel, "w", encoding="utf-8").write("\n".join(o) + "\n")
        sys.stderr.write(f"{len(seite)} Eintraege, "
                         f"{sum(len(p) for p in seite)} Satzpaare -> {ziel}\n")
    print(f"{len(seiten)} Seiten, Nummern {erste_nummer} bis "
          f"{erste_nummer + len(seiten) - 1}")


if __name__ == "__main__":
    main()
