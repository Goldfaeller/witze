#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Liest fertige WordPress-Witzeseiten und gibt die einzelnen Bloecke zurueck.

Ein Block ist alles, was zu einem Witz gehoert: die sichtbaren Satzpaare
und die beiden Aufklappboxen. Die Ueberschrift "Witz 12a" wird zerlegt in
Nummer und Buchstabe, damit zusammengehoerige Fassungen zusammenbleiben.
Gruppenueberschriften (h2 pc-gruppe) werden mitgelesen, aber getrennt
gehalten - beim Neustapeln fallen sie weg.
"""

import glob
import re

H3 = re.compile(r'<!-- wp:heading \{"level":3\} -->\s*'
                r'<h3[^>]*>(.*?)</h3>\s*<!-- /wp:heading -->', re.S)
H2 = re.compile(r'<!-- wp:heading \{"level":2,"className":"pc-gruppe"\} -->\s*'
                r'<h2[^>]*>(.*?)</h2>\s*<!-- /wp:heading -->\s*', re.S)
SEP = re.compile(r'<!-- wp:separator -->\s*<hr[^>]*>\s*<!-- /wp:separator -->\s*')
FUSS = '<div class="pc-footer-nav">'


def ohne_markup(text):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", text)).strip()


def seite_lesen(pfad):
    text = open(pfad, encoding="utf-8").read()
    treffer = list(H3.finditer(text))
    if not treffer:
        return []

    ende = text.find(FUSS)
    if ende == -1:
        ende = len(text)

    bloecke = []
    for i, m in enumerate(treffer):
        schluss = treffer[i + 1].start() if i + 1 < len(treffer) else ende
        koerper = text[m.end():schluss]

        # Was hinten am Koerper haengt, leitet schon den naechsten Block ein
        koerper = H2.sub("", koerper)
        koerper = SEP.sub("", koerper)

        # Gruppenueberschrift, die VOR diesem Block stand
        davor = text[treffer[i - 1].end() if i else 0:m.start()]
        gruppe = H2.search(davor)

        titel = ohne_markup(m.group(1))
        zahl = re.match(r"^\D*(\d+)([a-z]?)", titel)
        bloecke.append({
            "quelle": pfad,
            "titel": titel,
            "nummer": int(zahl.group(1)) if zahl else 0,
            "fassung": zahl.group(2) if zahl else "",
            "gruppe": ohne_markup(gruppe.group(1)) if gruppe else "",
            "koerper": koerper.strip(),
        })
    return bloecke


def sichtbarer_text(block):
    """Die Satzpaare, die ohne Aufklappen zu sehen sind."""
    vor = block["koerper"].split("<details", 1)[0]
    return ohne_markup(vor)


def box_inhalt(teil):
    """Nur der Text im Aufklappkasten, ohne Rahmen und Beschriftung."""
    stelle = teil.find('pc-collapsible-body')
    if stelle != -1:
        teil = teil[stelle + len('pc-collapsible-body'):]
    return ohne_markup(teil).lstrip('">').strip()


def deutscher_text(block):
    """Der Inhalt der Box 'német' - die Grundlage fuer den Doppelungsvergleich."""
    teile = block["koerper"].split("<details")
    if len(teile) >= 3:
        return box_inhalt(teile[2])
    return sichtbarer_text(block)


def ungarischer_text(block):
    teile = block["koerper"].split("<details")
    if len(teile) >= 2:
        return box_inhalt(teile[1])
    return ""


def alle_lesen(muster_liste):
    bloecke = []
    for muster in muster_liste:
        for pfad in sorted(glob.glob(muster)):
            bloecke.extend(seite_lesen(pfad))
    return bloecke


if __name__ == "__main__":
    import sys
    b = alle_lesen(sys.argv[1:])
    print(f"{len(b)} Bloecke aus {len(set(x['quelle'] for x in b))} Seiten")
