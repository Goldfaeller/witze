#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Stapelt den gesamten Bestand neu, ab Seite 500.

Grundreihenfolge ist die alte: erst die Witze der Seiten 01 bis 23, dann
die laengeren Witze, dann die neu uebersetzten, danach die Sprueche und
zuletzt Anekdoten und Sprichwoerter.

Drei Themen werden gebuendelt und beginnen jeweils eine neue Seite:
Blondinen, Elefanten, Radio Jerewan. Wo eine solche Gruppe eine Seite
nicht fuellt, wird mit den nicht zugeordneten Witzen aufgefuellt - halb
leere Seiten soll es nicht geben. Die fuenf DDR-Witze bekommen keine
eigene Seite, sie fuellen ein Seitenende.

Zwischenueberschriften fallen weg.
"""

import json
import re
import sys

sys.path.insert(0, "tools")
from seiten_einlesen import sichtbarer_text, deutscher_text   # noqa: E402

THEMEN = [
    ("blondine", r"szőke|[Bb]londin"),
    ("elefant",  r"[Ee]lefánt|[Ee]lefant"),
    ("jerewan",  r"Jereván|Jerewan|Eriwan"),
]
SCHLUSSTHEMA = ("ddr", r"\bNDK\b|\bDDR\b")

ZIEL = 62000          # angestrebte Zeichenzahl Inhalt je Seite
GRENZE = 105000       # im Einzelfall darf es so weit gehen


def einheiten_bilden(bloecke):
    """Fassungen a, b, c eines Witzes gehoeren auf dieselbe Seite."""
    einheiten, offen = [], None
    for b in bloecke:
        schluessel = (b["quelle"], b["nummer"]) if b["fassung"] else None
        if schluessel and offen and offen["schluessel"] == schluessel:
            offen["bloecke"].append(b)
            continue
        offen = {"schluessel": schluessel, "bloecke": [b], "art": b["art"]}
        einheiten.append(offen)
    for e in einheiten:
        e["umfang"] = sum(len(b["koerper"]) + 420 for b in e["bloecke"])
        text = " ".join(sichtbarer_text(b) + " " + deutscher_text(b)
                        for b in e["bloecke"])
        e["thema"] = ""
        for name, muster in THEMEN + [SCHLUSSTHEMA]:
            if re.search(muster, text):
                e["thema"] = name
                break
    return einheiten


def seiten_fuellen(fluss, gruppen, schluss):
    """Baut die Seitenliste.

    Vor einer Themengruppe wird die laufende Seite erst mit nicht
    zugeordneten Witzen vollgemacht und dann geschlossen; so faengt die
    Gruppe sauber oben an, ohne dass eine halb leere Seite stehen bleibt.
    Dasselbe am Ende einer Gruppe.
    """
    seiten, seite = [], []
    umfang = 0
    stelle = 0
    schluss = list(schluss)

    def anhaengen(e):
        nonlocal umfang
        seite.append(e)
        umfang += e["umfang"]

    def schliessen():
        nonlocal seite, umfang
        if not seite:
            return
        while schluss and umfang + schluss[0]["umfang"] < GRENZE:
            anhaengen(schluss.pop(0))
        seiten.append(seite)
        seite, umfang = [], 0

    def aus_dem_fluss(bis_voll):
        """Nimmt Einheiten aus dem Fluss, bis die Seite voll genug ist."""
        nonlocal stelle
        while stelle < len(fluss) and umfang < bis_voll:
            e = fluss[stelle]
            if seite and umfang + e["umfang"] > GRENZE:
                break
            anhaengen(e)
            stelle += 1

    for gruppe in gruppen:
        # bis zur Stelle laufen, an der die Gruppe im Bestand zuerst auftauchte
        while stelle < gruppe["ab"] and stelle < len(fluss):
            e = fluss[stelle]
            if seite and umfang + e["umfang"] > ZIEL:
                schliessen()
            anhaengen(e)
            stelle += 1
        aus_dem_fluss(ZIEL)        # angebrochene Seite vollmachen
        schliessen()
        for g in gruppe["einheiten"]:
            if seite and umfang + g["umfang"] > ZIEL:
                schliessen()
            anhaengen(g)
        aus_dem_fluss(ZIEL)        # Rest der letzten Gruppenseite fuellen
        schliessen()

    while stelle < len(fluss):
        e = fluss[stelle]
        if seite and umfang + e["umfang"] > ZIEL:
            schliessen()
        anhaengen(e)
        stelle += 1
    schliessen()
    for e in schluss:
        anhaengen(e)
    schliessen()

    # Ein kurzer Rest am Schluss wandert auf die Seite davor
    if len(seiten) > 1:
        letzte = sum(e["umfang"] for e in seiten[-1])
        vorletzte = sum(e["umfang"] for e in seiten[-2])
        if letzte < 40000 and letzte + vorletzte < GRENZE:
            seiten[-2].extend(seiten.pop())
    return seiten


def main():
    bloecke = json.load(open(sys.argv[1], encoding="utf-8"))
    ziel = sys.argv[2]
    einheiten = einheiten_bilden(bloecke)

    fluss = [e for e in einheiten if not e["thema"]]
    schluss = [e for e in einheiten if e["thema"] == "ddr"]

    # Themengruppen in der Reihenfolge ihres ersten Vorkommens
    gruppen = []
    for name, _ in THEMEN:
        mitglieder = [e for e in einheiten if e["thema"] == name]
        if not mitglieder:
            continue
        erste = einheiten.index(mitglieder[0])
        vorher = sum(1 for e in einheiten[:erste] if not e["thema"])
        gruppen.append({"name": name, "ab": vorher, "einheiten": mitglieder})
    gruppen.sort(key=lambda g: g["ab"])

    seiten = seiten_fuellen(fluss, gruppen, schluss)

    json.dump([[e["bloecke"] for e in s] for s in seiten],
              open(ziel, "w", encoding="utf-8"), ensure_ascii=False)

    print(f"{len(seiten)} Seiten, Nummern 500 bis {499 + len(seiten)}")
    gesamt = 0
    for i, s in enumerate(seiten):
        n = sum(len(e["bloecke"]) for e in s)
        gesamt += n
        umfang = sum(e["umfang"] for e in s)
        if i < 5 or i >= len(seiten) - 3:
            print(f"  {500+i}: {n:4d} Bloecke, rund {umfang//1000} KB")
    print(f"  Bloecke insgesamt: {gesamt}")


if __name__ == "__main__":
    main()
