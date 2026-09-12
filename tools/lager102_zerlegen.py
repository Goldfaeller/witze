#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zerlegt "102 google docs Lager.txt" in einzelne Eintraege.

Die Datei ist reines Deutsch. Eintraege sind durch Strichlinien getrennt.
Jeder Eintrag wird in Zeilen zerlegt; eine Zeile mit mehreren Saetzen wird
an den Satzenden aufgeteilt, damit spaeter Satz fuer Satz uebersetzt werden
kann - so wie es das Format der Seiten 01 bis 23 verlangt.

Ergebnis ist eine JSON-Datei, die beim Uebersetzen Eintrag fuer Eintrag
gefuellt wird. Das Feld "art" ("witz" oder "spruch") und das Feld "ung"
bleiben zunaechst leer.
"""

import json
import re
import sys

# Satzende: Punkt, Frage-, Ausrufezeichen, evtl. mit schliessendem
# Anfuehrungszeichen oder Klammer, gefolgt von Leerzeichen und Grossbuchstabe
# oder Gedankenstrich. Abkuerzungen wie "z.B." bleiben so verschont.
# Nicht nach einer Ziffer trennen - "im 10. Stock" ist kein Satzende.
SATZENDE = re.compile(r'(?<=[.!?])(?<!\d\.)(["“”»\')\]]*)\s+(?=[-–—A-ZÄÖÜ„"])')

ABKUERZUNG = re.compile(r"\b(z\.\s?B|d\.\s?h|u\.\s?a|bzw|usw|ca|Nr|Dr|St|ggf|"
                        r"evtl|inkl|zzgl|Hr|Fr|Prof|Abb|vgl|bspw)\.$")


def saetze(zeile):
    """Eine Zeile in Saetze zerlegen, Abkuerzungen nicht als Satzende werten."""
    roh = SATZENDE.split(zeile)
    # re.split mit Gruppe liefert abwechselnd Text und Gruppeninhalt
    teile, i = [], 0
    while i < len(roh):
        stueck = roh[i]
        if i + 1 < len(roh) and roh[i + 1]:
            stueck += roh[i + 1]
        teile.append(stueck)
        i += 2

    out = []
    for teil in teile:
        teil = teil.strip()
        if not teil:
            continue
        if out and ABKUERZUNG.search(out[-1]):
            out[-1] = out[-1] + " " + teil
        else:
            out.append(teil)
    return out


def eintraege_lesen(pfad):
    lines = open(pfad, encoding="utf-8").read().splitlines()
    bloecke, cur = [], []
    for zeile in lines:
        # Manche Eintraege tragen mitten im Text noch eine Strichlinie,
        # die aus dem Google-Doc stammt - sie trennt genauso.
        if re.fullmatch(r"[_ ]*-{3,}[_ ]*", zeile.strip()):
            if any(l.strip() for l in cur):
                bloecke.append(cur)
            cur = []
        else:
            cur.append(zeile)
    if any(l.strip() for l in cur):
        bloecke.append(cur)

    eintraege = []
    for nr, block in enumerate(bloecke, start=1):
        zeilen = []
        for roh in block:
            s = roh.strip()
            if not s:
                continue
            # Mehrzeilige Eintraege sind schon von Hand umbrochen; nur
            # einzeilige Eintraege muessen in Saetze zerlegt werden.
            zeilen.extend(saetze(s) if len([x for x in block if x.strip()]) == 1
                          else [s])
        if zeilen:
            eintraege.append({"nr": nr, "art": "", "dt": zeilen, "ung": []})
    return eintraege


def main():
    quelle, ziel = sys.argv[1], sys.argv[2]
    eintraege = eintraege_lesen(quelle)
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump(eintraege, f, ensure_ascii=False, indent=1)
        f.write("\n")
    zeilen = sum(len(e["dt"]) for e in eintraege)
    sys.stderr.write(f"{len(eintraege)} Eintraege, {zeilen} Zeilen -> {ziel}\n")


if __name__ == "__main__":
    main()
