#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schreibt die neu gestapelten Seiten als WordPress-Blockcode.

Die Bloecke liegen fertig vor, sie werden nur neu nummeriert und mit Kopf,
Trennlinien und Fussnavigation umgeben. Zwischenueberschriften entstehen
keine.
"""

import json
import re
import sys

sys.path.insert(0, "tools")
from wiki2wp import STYLE, SEP, HOME_NAV                    # noqa: E402

VORSPANN = ("An einigen Stellen steht hinter dem ungarischen Wort zusätzlich "
            "die Aussprache in eckigen Klammern. Beispiel: Segíts [segíccs] "
            "magadon!")


def wort_von(titel):
    """"Witz 12a" -> "Witz", "Sprichwort 3" -> "Sprichwort"."""
    m = re.match(r"^(\D*?)\s*\d", titel)
    return m.group(1).strip() if m and m.group(1).strip() else "Witz"


def nav(nr):
    return (f'<a href="/{nr - 1}-witze/">« Zurück zu Witze {nr - 1}</a>'
            f' &nbsp;|&nbsp; <span>Witze {nr}</span> &nbsp;|&nbsp; '
            f'<a href="/{nr + 1}-witze/">Weiter zu Witze {nr + 1} »</a>')


def seite_bauen(nr, einheiten):
    o = [STYLE, "",
         '<!-- wp:group {"className":"pc-container","anchor":"top"} -->',
         '<div id="top" class="wp-block-group pc-container"><!-- wp:html -->',
         '<div class="pc-home-link">', f"  {HOME_NAV}", "</div>",
         '<div class="pc-chapter-nav">', f"  {nav(nr)}", "</div>",
         "<!-- /wp:html -->", "",
         SEP, "",
         "<!-- wp:paragraph -->",
         f"<p><strong>Witze {nr}</strong></p>",
         "<!-- /wp:paragraph -->", "",
         "<!-- wp:paragraph -->",
         f"<p>{VORSPANN}</p>",
         "<!-- /wp:paragraph -->", ""]

    lfd = 0
    for einheit in einheiten:
        lfd += 1
        mehrere = len(einheit) > 1
        for stelle, block in enumerate(einheit):
            zaehler = (f"{lfd}{chr(ord('a') + stelle)}" if mehrere
                       else str(lfd))
            o += [SEP, "",
                  '<!-- wp:heading {"level":3} -->',
                  f'<h3 class="wp-block-heading">'
                  f'{wort_von(block["titel"])} {zaehler}</h3>',
                  "<!-- /wp:heading -->", "",
                  block["koerper"], ""]

    o += [SEP, "",
          "<!-- wp:html -->",
          '<div class="pc-footer-nav">',
          '  <div class="pc-top-link">'
          '<a href="#top">↑ Hoch zum Seitenanfang</a></div>',
          '  <div class="pc-chapter-nav">', f"  {nav(nr)}", "</div>",
          '  <div class="pc-home-link">', f"  {HOME_NAV}", "</div>",
          "</div>",
          "<!-- /wp:html --></div>",
          "<!-- /wp:group -->"]
    return "\n".join(o) + "\n"


def main():
    seiten = json.load(open(sys.argv[1], encoding="utf-8"))
    erste = int(sys.argv[2])
    for versatz, einheiten in enumerate(seiten):
        nr = erste + versatz
        ziel = f"{nr} witze modjor-de.txt"
        open(ziel, "w", encoding="utf-8").write(seite_bauen(nr, einheiten))
    print(f"{len(seiten)} Seiten geschrieben: "
          f"{erste} bis {erste + len(seiten) - 1}")


if __name__ == "__main__":
    main()
