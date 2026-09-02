#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zerlegt eine fertige WordPress-Seite in mehrere kürzere Seiten.

Arbeitet auf dem fertigen Seitencode, nicht auf der Wikivorlage - die Seiten
sind von Hand nachbearbeitet, und diese Arbeit soll erhalten bleiben.
Stilblock, Kopf, Vorspann und Fußzeile werden auf jede Teilseite kopiert, die
Kapitelnavigation neu gesetzt.
"""

import re
import sys

H3 = '<!-- wp:heading {"level":3} -->'
H2 = '<!-- wp:heading {"level":2'
SEP = "<!-- wp:separator -->"
FUSS = '<div class="pc-footer-nav">'


def zerlegen(text):
    """-> (kopf, vorspann, [bloecke], fuss)"""
    stellen = [m.start() for m in re.finditer(re.escape(H3), text)]
    if not stellen:
        raise SystemExit("Keine Witzüberschriften gefunden.")

    def blockanfang(pos, grenze):
        """Trennlinie und etwaige Abschnittsüberschrift vor der Überschrift."""
        anfang = text.rfind(SEP, grenze, pos)
        if anfang == -1:
            return pos
        h2 = text.rfind(H2, grenze, anfang)
        if h2 != -1 and "<!-- /wp:heading -->" in text[h2:anfang]:
            return h2
        return anfang

    anfaenge = []
    vorherige = 0
    for pos in stellen:
        a = blockanfang(pos, vorherige)
        anfaenge.append(a)
        vorherige = pos

    fuss_marke = text.index(FUSS)
    fuss_anfang = blockanfang(fuss_marke, stellen[-1])

    bloecke = [text[anfaenge[i]:(anfaenge[i + 1] if i + 1 < len(anfaenge)
                                 else fuss_anfang)]
               for i in range(len(anfaenge))]

    kopf_ende = text.index('<div class="pc-chapter-nav">')
    nav_ende = text.index("</div>", kopf_ende) + len("</div>\n")
    return (text[:kopf_ende], text[nav_ende:anfaenge[0]], bloecke,
            text[fuss_anfang:])


def nav(nr, gesamt_von, gesamt_bis):
    zurueck = nr - 1 if nr > gesamt_von else gesamt_von - 1
    weiter = nr + 1 if nr < gesamt_bis else gesamt_bis + 1
    return (f'<div class="pc-chapter-nav">\n'
            f'  <a href="/{zurueck}-witze/">« Zurück zu Seite {zurueck}</a>'
            f' &nbsp;|&nbsp; <span>Seite {nr}</span> &nbsp;|&nbsp; '
            f'<a href="/{weiter}-witze/">Weiter zu Seite {weiter} »</a>\n'
            f'</div>\n')


def verteilen(laengen, grenze):
    """Gruppen der Reihe nach auf Seiten verteilen, keine über der Grenze."""
    seiten, jetzt, summe = [], [], 0
    for i, l in enumerate(laengen):
        if jetzt and summe + l > grenze:
            seiten.append(jetzt)
            jetzt, summe = [], 0
        jetzt.append(i)
        summe += l
    if jetzt:
        seiten.append(jetzt)
    return seiten
