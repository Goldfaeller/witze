#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sammelt alle Bloecke des gesamten Bestands in einer festen Reihenfolge:
erst die Witze, dann die Sprueche, zuletzt Anekdoten und Sprichwoerter.

Die drei grossen Dateien 40, 41 und 42 im Hauptverzeichnis bleiben aussen
vor - ihr Inhalt steht in wordpress/40-witze.txt bis 67-witze.txt bereits
in vernuenftige Haeppchen zerlegt.
"""

import json
import sys

sys.path.insert(0, "tools")
from seiten_einlesen import seite_lesen                    # noqa: E402

QUELLEN = [
    ("witz",     [f"{n:02d} witze modjor-de.txt" for n in range(1, 24)]),
    ("witz",     [f"wordpress/{n}-witze.txt" for n in range(40, 49)]),
    ("witz",     [f"{n} witze modjor-de.txt" for n in range(200, 210)]),
    ("spruch",   [f"wordpress/{n}-witze.txt" for n in range(49, 62)]),
    ("spruch",   [f"{n} witze modjor-de.txt" for n in range(210, 230)]),
    ("anekdote", [f"wordpress/{n}-witze.txt" for n in range(62, 68)]),
]


def sammeln():
    alle = []
    for art, dateien in QUELLEN:
        for pfad in dateien:
            for b in seite_lesen(pfad):
                b["art"] = art
                b["lfd"] = len(alle)
                alle.append(b)
    return alle


def main():
    alle = sammeln()
    json.dump(alle, open(sys.argv[1], "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for art in ("witz", "spruch", "anekdote"):
        n = sum(1 for b in alle if b["art"] == art)
        print(f"{art:9s} {n:5d} Bloecke")
    print(f"{'gesamt':9s} {len(alle):5d} Bloecke")


if __name__ == "__main__":
    main()
