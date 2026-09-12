#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streicht Doppelungen aus dem Bestand.

Zwei Schritte:
1. Die Fassungen a, b, c einer Seite aus Lager 101 bleiben nur, wenn sich
   ihre ungarischen Saetze wirklich unterscheiden. Zu aehnliche Fassungen
   sind keine Lernhilfe, sondern Wiederholung.
2. Danach faellt jeder Block weg, dessen deutscher Text schon einmal
   vorkam - wortgleich oder zu ueber 90 Prozent uebereinstimmend. Der
   erste Fund bleibt stehen.

Fassungen desselben Witzes werden dabei nicht gegeneinander geprueft; sie
sollen einander aehneln.
"""

import difflib
import json
import re
import sys
from collections import defaultdict

sys.path.insert(0, "tools")
from seiten_einlesen import deutscher_text, ungarischer_text   # noqa: E402

AEHNLICH_FASSUNG = 0.85
AEHNLICH_DOPPEL = 0.90


def norm(text):
    text = re.sub(r"\s*\d+\.\s*", " ", " " + text)
    return re.sub(r"[^\wáéíóöőúüűÁÉÍÓÖŐÚÜŰ ]", "", text.lower()).strip()


def fassungen_ausduennen(bloecke, bericht):
    """Nur bei den Seiten aus Lager 101 - dort stammen a/b/c von mir."""
    gruppen = defaultdict(list)
    for b in bloecke:
        if b["fassung"] and re.search(r"/?20[012] witze", b["quelle"]):
            gruppen[(b["quelle"], b["nummer"])].append(b)

    raus = set()
    for teilnehmer in gruppen.values():
        behalten = []
        for b in teilnehmer:
            text = norm(ungarischer_text(b))
            if any(difflib.SequenceMatcher(None, text, t).ratio()
                   > AEHNLICH_FASSUNG for t in behalten):
                raus.add(b["lfd"])
                bericht.append(f'Fassung weg: {b["quelle"]} {b["titel"]}')
            else:
                behalten.append(text)
    return raus


def wortmenge(text):
    return set(w for w in text.split() if len(w) > 3)


def doppelungen_finden(bloecke, bericht):
    """Gleiche Witze, die an mehreren Stellen im Bestand stehen."""
    gesehen = []          # (wortmenge, normtext, block)
    raus = set()
    # Wer zu wem als Fassung gehoert, darf sich aehneln
    familie = {b["lfd"]: (b["quelle"], b["nummer"]) if b["fassung"] else None
               for b in bloecke}

    for b in bloecke:
        text = norm(deutscher_text(b))
        if not text:
            continue
        menge = wortmenge(text)
        doppelt = None
        for m, t, anderer in gesehen:
            if familie[b["lfd"]] and familie[b["lfd"]] == familie[anderer["lfd"]]:
                continue
            if t == text:
                doppelt = anderer
                break
            if not menge or not m:
                continue
            gemeinsam = len(menge & m) / max(len(menge | m), 1)
            if gemeinsam < 0.5:
                continue
            if abs(len(t) - len(text)) > 0.25 * max(len(t), len(text)):
                continue
            if difflib.SequenceMatcher(None, t, text).ratio() > AEHNLICH_DOPPEL:
                doppelt = anderer
                break
        if doppelt is not None:
            raus.add(b["lfd"])
            bericht.append(f'Doppelt: {b["quelle"]} {b["titel"]} '
                           f'= {doppelt["quelle"]} {doppelt["titel"]}')
        else:
            gesehen.append((menge, text, b))
    return raus


def main():
    bloecke = json.load(open(sys.argv[1], encoding="utf-8"))
    bericht = []

    raus = fassungen_ausduennen(bloecke, bericht)
    anzahl_fassungen = len(raus)
    uebrig = [b for b in bloecke if b["lfd"] not in raus]

    raus2 = doppelungen_finden(uebrig, bericht)
    uebrig = [b for b in uebrig if b["lfd"] not in raus2]

    json.dump(uebrig, open(sys.argv[2], "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    open(sys.argv[3], "w", encoding="utf-8").write("\n".join(bericht) + "\n")

    print(f"{anzahl_fassungen} ueberfluessige Fassungen gestrichen")
    print(f"{len(raus2)} Doppelungen gestrichen")
    print(f"{len(uebrig)} Bloecke bleiben")


if __name__ == "__main__":
    main()
