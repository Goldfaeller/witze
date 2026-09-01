#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tauscht bei ausgewählten Witzen den sichtbaren Text mit dem Inhalt der ersten
Aufklappbox und benennt deren Titel um.

Vorher:  sichtbar die Satzpaare, in der Box "magyar" der ungarische Text
Nachher: sichtbar der ungarische Text, in der Box die Satzpaare

Die zweite Box ("német") und alles außerhalb der gewählten Witze bleiben
unangetastet.
"""

import re
import sys

BOX_AUF = """<!-- wp:html -->
<details class="pc-collapsible">
  <summary><span class="pc-collapsible-hint">(aufklappen)</span><span class="pc-collapsible-title">TITEL</span></summary>
  <div class="pc-collapsible-body">
<!-- /wp:html -->
"""

BOX_ZU = """<!-- wp:html -->
  </div>
</details>
<!-- /wp:html -->
"""

P_TAG = re.compile(r"<p(?: class=\"[^\"]*\")?>.*?</p>", re.S)


def absaetze(text):
    """Alle <p>-Zeilen eines Bereichs, Klassen bleiben erhalten."""
    return P_TAG.findall(text)


def umbauen(block, titel):
    """Einen Witzblock umstellen. Gibt None zurück, wenn er nicht passt."""
    # Bereich vom Ende der Überschrift bis zum Beginn der zweiten Box
    boxen = [m.start() for m in re.finditer(r"<!-- wp:html -->\n<details", block)]
    if len(boxen) != 2:
        return None
    kopf_ende = block.index("<!-- /wp:heading -->\n") + len("<!-- /wp:heading -->\n")

    sichtbar_teil = block[kopf_ende:boxen[0]]
    erste_box = block[boxen[0]:boxen[1]]

    sichtbar = absaetze(sichtbar_teil)
    # Nur der Rumpf der Box, nicht die Zeile mit dem Titel
    rumpf_start = erste_box.index("<!-- /wp:html -->\n") + len("<!-- /wp:html -->\n")
    in_box = absaetze(erste_box[rumpf_start:])
    if not sichtbar or not in_box:
        return None

    neu = [block[:kopf_ende],
           "\n<!-- wp:paragraph -->\n",
           "\n".join(in_box),
           "\n<!-- /wp:paragraph -->\n\n",
           BOX_AUF.replace("TITEL", titel),
           "\n"]
    for p in sichtbar:
        neu.append("<!-- wp:paragraph -->\n" + p + "\n<!-- /wp:paragraph -->\n\n")
    neu.append(BOX_ZU)
    neu.append("\n")
    neu.append(block[boxen[1]:])
    return "".join(neu)


def main():
    quelle, ziel, von, bis, titel = (sys.argv[1], sys.argv[2],
                                     int(sys.argv[3]), int(sys.argv[4]), sys.argv[5])
    text = open(quelle, encoding="utf-8").read()

    # An den Witzüberschriften zerteilen, damit nur die gewählten angefasst werden
    marke = re.compile(r'(?=<!-- wp:heading \{"level":3\} -->)')
    teile = marke.split(text)
    geaendert, uebersprungen = [], []
    for i, teil in enumerate(teile):
        m = re.search(r'<h3 class="wp-block-heading">\w+ (\d+)</h3>', teil)
        if not m:
            continue
        nr = int(m.group(1))
        if not (von <= nr <= bis):
            continue
        neu = umbauen(teil, titel)
        if neu is None:
            uebersprungen.append(nr)
            continue
        teile[i] = neu
        geaendert.append(nr)

    open(ziel, "w", encoding="utf-8").write("".join(teile))
    print(f"umgestellt: {len(geaendert)} Witze ({min(geaendert)} bis {max(geaendert)})")
    if uebersprungen:
        print(f"ÜBERSPRUNGEN (Aufbau passte nicht): {uebersprungen}")


if __name__ == "__main__":
    main()
