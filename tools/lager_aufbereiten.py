#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bringt das Rohmaterial aus "1 Lager witze" in dasselbe Wiki-Format wie
witze01.txt ... witze17.txt:

  - Satzzeilen durchnummerieren
  - jede Zeile in ungarisch und deutsch trennen
  - daraus die beiden Aufklappboxen bauen (magyar - német / deutsch)
  - Witze fortlaufend neu nummerieren (die a/b/c-Varianten bleiben beisammen)

Abschnitte, die die Boxen schon haben, bleiben unverändert.
Ein Prüfbericht listet alle Zeilen auf, bei denen die Trennung unsicher war.
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


def box(titel, zeilen):
    return BOX.replace("TITEL", titel).replace("INHALT", "\n".join(zeilen))


def sections(text):
    """Zerlegt den Wikitext in (Vorspann, [(Überschrift, Rumpf), ...])."""
    parts = re.split(r"^=+\s*(.*?)\s*=+\s*$", text, flags=re.M)
    return parts[0], [(parts[i], parts[i + 1]) for i in range(1, len(parts), 2)]


def strip_nav(text):
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("{{"):
            while i < len(lines) and not lines[i].rstrip().endswith("}}"):
                i += 1
            i += 1
            continue
        break
    return "\n".join(lines[i:])


def umbauen(body, bericht, witz):
    """Rohabschnitt -> (ungarisch, paare, deutsch) als Listen von Wikizeilen."""
    hu_lines, pair_lines, de_lines = [], [], []
    nummer = 0
    for raw in body.splitlines():
        s = raw.strip()
        if not s.startswith(":"):
            continue
        tiefe = len(s) - len(s.lstrip(":"))
        inhalt = s.lstrip(":").strip()
        if not inhalt:
            continue
        vor = ""
        if tiefe == 1:
            nummer += 1
            vor = f"{nummer}. "
        pfx = ":" * tiefe
        hu, de, status = split_pair(inhalt)

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
        else:  # ungetrennt: bleibt nur im sichtbaren Satzpaar-Teil stehen
            pair_lines.append(f"{pfx}{vor}{inhalt}")

        if status != "sicher":
            bericht.append((witz, status, inhalt))
    return hu_lines, pair_lines, de_lines


def main():
    src, dst, rep = sys.argv[1], sys.argv[2], sys.argv[3]
    text = strip_nav(open(src, encoding="utf-8").read())
    _, secs = sections(text)

    # Fortlaufend neu nummerieren; 260 ist in witze17.txt schon vergeben
    start = int(sys.argv[4]) if len(sys.argv) > 4 else 261
    # Arbeitsmarken des Autors ("== WEITER WEITER ==") sind keine Witze
    verworfen = [(n, b) for n, b in secs if not re.match(r"^\d", n)]
    secs = [(n, b) for n, b in secs if re.match(r"^\d", n)]

    basen, neu = [], {}
    for name, _ in secs:
        m = re.match(r"^(\d+)", name)
        base = m.group(1) if m else name
        if base not in neu:
            neu[base] = start + len(basen)
            basen.append(base)

    out, bericht, unveraendert = [], [], 0
    for name, body in secs:
        m = re.match(r"^(\d+)(.*)$", name)
        titel = f"{neu[m.group(1)]}{m.group(2)}" if m else name
        out.append(f"=== {titel} ===\n")
        if "mw-collapsible" in body:
            out.append(body.strip("\n") + "\n")
            unveraendert += 1
        else:
            hu, paare, de = umbauen(body, bericht, titel)
            out.append("\n".join(hu) + "\n")
            out.append(box("magyar - német", paare))
            out.append(box("deutsch", de) + "\n")
        out.append("")

    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(out))

    with open(rep, "w", encoding="utf-8") as f:
        f.write("Pruefbericht Sprachtrennung\n")
        f.write(f"Abschnitte gesamt: {len(secs)}, davon unveraendert uebernommen: "
                f"{unveraendert}\n")
        f.write(f"Zeilen zum Nachsehen: {len(bericht)}\n")
        for n, b in verworfen:
            f.write(f"Arbeitsmarke uebersprungen: '{n}' "
                    f"({len(b.strip())} Zeichen Inhalt)\n")
        f.write("\n")
        for witz, status, zeile in bericht:
            f.write(f"[{status}] Witz {witz}: {zeile}\n")

    sys.stderr.write(f"{len(secs)} Abschnitte -> {dst}\n")
    sys.stderr.write(f"{len(bericht)} Zeilen im Pruefbericht -> {rep}\n")


if __name__ == "__main__":
    main()
