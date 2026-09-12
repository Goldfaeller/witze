#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prueft die Uebersetzungschargen zu Lager 102 und baut daraus zwei
Lagerdateien im Format von Datei 101 (":ungarisch - deutsch"), getrennt
nach Witzen und Spruechen.

Chargenformat (arbeit/ung/*.txt):

    @17 spruch
    <ungarische Zeile zu deutscher Zeile 1>

    @18 witz
    <ungarisch zu Zeile 1>
    <ungarisch zu Zeile 2>

In der Quelle stecken mitunter zwei Sachen in einem Eintrag. Dann wird der
Eintrag geteilt; die Teile heissen @18.1, @18.2 und teilen sich die
deutschen Zeilen der Reihe nach auf.
"""

import glob
import json
import re
import sys

KOPF = re.compile(r"^@(\d+)(?:\.(\d+))?\s+(witz|spruch|streichen)\s*$")


def chargen_lesen(ordner):
    """-> {eintragsnummer: [teil, ...]} in Lesereihenfolge."""
    ung, gesehen = {}, set()
    for pfad in sorted(glob.glob(ordner + "/*.txt")):
        teil = None
        for zeilennr, zeile in enumerate(
                open(pfad, encoding="utf-8").read().splitlines(), start=1):
            m = KOPF.match(zeile.strip())
            if m:
                nr, teilnr = int(m.group(1)), m.group(2)
                schluessel = (nr, teilnr)
                if schluessel in gesehen:
                    sys.exit(f"{pfad}:{zeilennr}: {zeile.strip()} kommt doppelt")
                gesehen.add(schluessel)
                teil = {"art": m.group(3), "zeilen": []}
                ung.setdefault(nr, []).append(teil)
                continue
            if not zeile.strip():
                continue
            if teil is None:
                sys.exit(f"{pfad}:{zeilennr}: Text vor der ersten @-Zeile")
            teil["zeilen"].append(zeile.strip())
    return ung


def main():
    argumente = [a for a in sys.argv[1:] if not a.startswith("--")]
    eintraege = json.load(open(argumente[0], encoding="utf-8"))
    ung = chargen_lesen(argumente[1])
    ziele = argumente[2:4]

    fehlt, schief, stuecke = [], [], []
    for e in eintraege:
        teile = ung.get(e["nr"])
        if not teile:
            fehlt.append(e["nr"])
            continue
        # "streichen" nimmt die Zeilen auf, die nicht auf die Seite sollen
        gestrichen = [t for t in teile if t["art"] == "streichen"]
        if len(gestrichen) > 1:
            schief.append(f'{e["nr"]}: mehr als ein Streichteil')
            continue
        summe = sum(len(t["zeilen"]) for t in teile)
        if gestrichen:
            rest = len(e["dt"]) - summe
            if rest < 0:
                schief.append(f'{e["nr"]}: zu viele ungarische Zeilen')
                continue
            gestrichen[0]["zeilen"] = [""] * rest
            summe = len(e["dt"])
        if summe != len(e["dt"]):
            schief.append(f'{e["nr"]}: {summe} ungarische Zeilen, '
                          f'{len(e["dt"])} deutsche')
            continue
        # deutsche Zeilen der Reihe nach auf die Teile verteilen
        i = 0
        for t in teile:
            n = len(t["zeilen"])
            if t["art"] != "streichen":
                stuecke.append((t["art"], t["zeilen"], e["dt"][i:i + n]))
            i += n

    unbekannt = sorted(set(ung) - {e["nr"] for e in eintraege})
    witze = sum(1 for a, _, _ in stuecke if a == "witz")
    sprueche = len(stuecke) - witze
    print(f"{len(ung)} von {len(eintraege)} Eintraegen uebersetzt "
          f"-> {witze} Witze, {sprueche} Sprueche")
    if fehlt:
        print(f"fehlen noch {len(fehlt)}, naechster: {fehlt[0]}")
    for z in schief:
        print("  ZEILENZAHL: " + z)
    if unbekannt:
        print(f"  UNBEKANNTE NUMMERN: {unbekannt[:10]}")
    if schief or unbekannt:
        sys.exit(1)

    if len(ziele) == 2 and (not fehlt or "--unvollstaendig" in sys.argv):
        for ziel, art in zip(ziele, ("witz", "spruch")):
            o = []
            for a, hu, de in stuecke:
                if a != art:
                    continue
                o.append("-" * 22)
                o += [f":{h} - {d}" for h, d in zip(hu, de)]
            open(ziel, "w", encoding="utf-8").write("\n".join(o) + "\n")
            print(f"-> {ziel}")


if __name__ == "__main__":
    main()
