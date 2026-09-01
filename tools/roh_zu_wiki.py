#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bringt die Rohdateien 99-langwitz, 99-spruch und 99-anakdote in das Wiki-Format
der übrigen Witzeseiten, damit wiki2wp.py sie weiterverarbeiten kann.

Anders als das übrige Material:
  - die Witze sind nicht mit "=== N ===" überschrieben, sondern durch
    Strichzeilen (:------) voneinander getrennt
  - die Satzpaare stehen schon fertig in einer Zeile
  - 99-anakdote gliedert sich zusätzlich in "== Abschnitte =="

Erzeugt wird je Witz: durchnummerierte ungarische Zeilen, die Box mit den
Satzpaaren und die Box mit dem deutschen Text.
"""

import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from sprachtrenner import split_pair  # noqa: E402

BOX = ('{| class="mw-collapsible mw-collapsed wikitable" style="width: 100%" \n'
       "|-\n"
       "!'''<span style=\"color:#F0F;\">TITEL</span> '''\n"
       "|-\n"
       "|\n"
       "INHALT\n"
       "|}")

TRENNER = re.compile(r"^:?-{5,}\s*$")
BILD = re.compile(r"^\[\[(?:File|Datei):([^|\]]+)(.*)\]\]\s*$")
NUR_FETT = re.compile(r"^:?'''[^']+'''\s*$")


def box(titel, zeilen):
    return BOX.replace("TITEL", titel).replace("INHALT", "\n".join(zeilen))


def strip_nav(lines):
    i = 0
    while i < len(lines):
        if lines[i].strip().startswith("{{"):
            while i < len(lines) and not lines[i].rstrip().endswith("}}"):
                i += 1
            i += 1
            continue
        break
    return lines[i:]


def zerlegen(pfad, bericht):
    """-> (Vorspannzeilen, [(Abschnittsüberschrift oder None, [Zeilen]), ...])"""
    lines = strip_nav(open(pfad, encoding="utf-8").read().splitlines())
    vorspann, witze = [], []
    aktuell, gruppe, im_vorspann = [], None, True

    def abschliessen():
        nonlocal aktuell, gruppe
        if aktuell:
            witze.append((gruppe, aktuell))
            gruppe = None
        aktuell = []

    for roh in lines:
        s = roh.strip()
        if not s:
            continue
        if TRENNER.match(s):
            abschliessen()
            continue
        if s.startswith("=="):
            abschliessen()
            gruppe = s.strip("= ").strip()
            im_vorspann = False
            continue
        if im_vorspann and (s.startswith(";")
                            or "An einigen Stellen" in s
                            or NUR_FETT.match(s)):
            vorspann.append(roh)
            continue
        im_vorspann = False

        if s.startswith("<br"):
            continue
        bild = BILD.match(s)
        if bild:
            # Das Bild liegt auf Wikimedia Commons und kann nicht mitwandern;
            # eine etwaige Bildunterschrift ist aber Teil des Witzes.
            teile = [t for t in bild.group(2).split("|") if t.strip()]
            unterschrift = next(
                (t.strip() for t in teile
                 if t.strip() not in ("thumb",) and not re.match(r"^\d+\s*px$", t.strip())),
                None)
            bericht.append(("Bild nicht übernommen", pfad, bild.group(1)))
            if unterschrift:
                aktuell.append(":" + unterschrift)
            continue
        aktuell.append(roh if roh.startswith(":") else ":" + s)

    abschliessen()
    return vorspann, witze


VERSION = re.compile(r"^:?\s*(Version \d+)\s*$")


def umbauen(zeilen, bericht, pfad, witznr):
    hu_lines, pair_lines, de_lines = [], [], []
    nummer = 0
    for roh in zeilen:
        s = roh.strip()
        marke = VERSION.match(s)
        if marke:
            # "Version 1/2/3" kennzeichnet mehrere Fassungen desselben Witzes.
            # Die Marke steht in allen drei Blöcken, und die Zählung der Sätze
            # beginnt bei jeder Fassung wieder bei 1.
            for ziel in (hu_lines, pair_lines, de_lines):
                ziel.append("::'''" + marke.group(1) + "'''")
            nummer = 0
            continue
        tiefe = len(s) - len(s.lstrip(":"))
        inhalt = s.lstrip(":").strip()
        if not inhalt:
            continue
        vor = ""
        if tiefe <= 1:
            nummer += 1
            vor = f"{nummer}. "
        pfx = ":" * max(tiefe, 1)

        # Eine ganz fett gesetzte Zeile erst auszeichnungsfrei trennen, sonst
        # bekommt die eine Hälfte die öffnenden und die andere die schließenden
        # Hochkommata und keine von beiden wird fett.
        fett = re.match(r"^'''(.+)'''$", inhalt)
        if fett:
            inhalt = fett.group(1)

        hu, de, status = split_pair(inhalt)
        if fett:
            hu = f"'''{hu}'''" if hu else hu
            de = f"'''{de}'''" if de else de
            inhalt = f"'''{inhalt}'''"

        if status in ("sicher", "unsicher"):
            hu_lines.append(f"{pfx}{vor}{hu}")
            pair_lines.append(f"{pfx}{vor}{hu} - {de}")
            de_lines.append(f"{pfx}{vor}{de}")
        elif status == "nur-ungarisch":
            hu_lines.append(f"{pfx}{vor}{hu}")
            pair_lines.append(f"{pfx}{vor}{hu}")
        elif status == "nur-deutsch":
            pair_lines.append(f"{pfx}{vor}{de}")
            de_lines.append(f"{pfx}{vor}{de}")
        else:
            pair_lines.append(f"{pfx}{vor}{inhalt}")
        if status != "sicher":
            bericht.append((status, f"{pfx}Witz {witznr}", inhalt))
    return hu_lines, pair_lines, de_lines


def main():
    quelle, ziel, rep = sys.argv[1], sys.argv[2], sys.argv[3]
    bericht = []
    vorspann, witze = zerlegen(quelle, bericht)

    out = list(vorspann) + [""]
    for i, (gruppe, zeilen) in enumerate(witze, start=1):
        titel = f"{i} - {gruppe}" if gruppe else str(i)
        hu, paare, de = umbauen(zeilen, bericht, quelle, i)
        out.append(f"=== {titel} ===\n")
        out.append("\n".join(hu) + "\n")
        out.append(box("magyar - német", paare))
        out.append(box("deutsch", de) + "\n")
        out.append("")

    open(ziel, "w", encoding="utf-8").write("\n".join(out))
    with open(rep, "w", encoding="utf-8") as f:
        f.write(f"Pruefbericht {quelle}\nWitze: {len(witze)}\n"
                f"Meldungen: {len(bericht)}\n\n")
        for art, wo, was in bericht:
            f.write(f"[{art}] {wo}: {was}\n")
    sys.stderr.write(f"{quelle}: {len(witze)} Witze -> {ziel} "
                     f"({len(bericht)} Meldungen)\n")


if __name__ == "__main__":
    main()
