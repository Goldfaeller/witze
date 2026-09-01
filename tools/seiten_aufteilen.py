#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teilt die aufbereitete Lagerdatei auf mehrere Wikiseiten auf.

Aufgeteilt wird nach Textlänge, nicht nach Anzahl der Witze, damit die Seiten
ungefähr gleich lang werden. Keine Seite wird länger als die Vorgabeseite
(witze01.txt). Zusammengehörige Varianten - 282a, 282b, 282c - bleiben immer
auf derselben Seite.
"""

import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import wiki2wp  # noqa: E402

KOPF = """{{{{Navigation hoch|
 hochtext=Inhaltsverzeichnis: Ungarisch-Lesebuch|
 hochlink=Ungarisch#Ungarisch-Lesebuch}}}}
{{{{Navigation zurückhochvor|
 zurücklink=Ungarisch/Ungarisch-Lesebuch-Witze/Kurze Witze {vor}|
 zurücktext={vor}. Teil – Kurze Witze|
 hochlink=Ungarisch/Ungarisch-Lesebuch-Witze|
 hochtext=Witze, witzige Sprüche, Sprichwörter|
 vorlink=Ungarisch/Ungarisch-Lesebuch-Witze/Kurze Witze {nach}|
vortext={nach}. Teil – Kurze Witze 
}}}}

;{nr}. Teil - Kurze Witze 
:An einigen Stellen steht hinter dem ungarischen Wort zusätzlich die Aussprache in eckigen Klammern. Beispiel: Segíts [segíccs] magadon!

:'''rövid viccek - kurze Witze'''

"""


def laenge(pfad):
    """Länge einer fertigen Seite in Zeichen WordPress-Seitencode."""
    return len(open(pfad, encoding="utf-8").read())


def wp_laenge(name, body):
    """So lang wird dieser eine Witz im fertigen Seitencode."""
    _, witze = wiki2wp.parse(f"=== {name} ===\n{body}")
    cfg = wiki2wp.konfiguration(1)
    return sum(len(wiki2wp.joke_block(w, cfg)) for w in witze)


def gruppen(pfad):
    """Abschnitte, nach Grundnummer gebündelt (282a/b/c gehören zusammen)."""
    text = open(pfad, encoding="utf-8").read()
    teile = re.split(r"^=+\s*(.*?)\s*=+\s*$", text, flags=re.M)
    paare = [(teile[i], teile[i + 1]) for i in range(1, len(teile), 2)
             if re.match(r"^\d", teile[i])]
    out, aktuell, basis = [], [], None
    for name, body in paare:
        b = re.match(r"^(\d+)", name).group(1)
        if b != basis and aktuell:
            out.append(aktuell)
            aktuell = []
        basis = b
        aktuell.append((name, body))
    if aktuell:
        out.append(aktuell)
    return out


def aufteilen(gr, anzahl, grenze):
    """
    Verteilt die Gruppen in ihrer Reihenfolge auf 'anzahl' Seiten. Gesucht ist
    die gleichmäßigste Verteilung: die Summe der quadrierten Abweichungen vom
    Mittel wird kleinstmöglich, keine Seite überschreitet 'grenze'.
    """
    laengen = [sum(wp_laenge(n, b) for n, b in g) for g in gr]
    n = len(gr)
    summe = [0] * (n + 1)
    for i, l in enumerate(laengen):
        summe[i + 1] = summe[i] + l
    mittel = summe[n] / anzahl

    # bester[i][k] = (Kosten, Trennstelle) für die ersten i Gruppen auf k Seiten
    unmoeglich = float("inf")
    bester = [[(unmoeglich, -1)] * (anzahl + 1) for _ in range(n + 1)]
    bester[0][0] = (0.0, -1)
    for k in range(1, anzahl + 1):
        for i in range(1, n + 1):
            for j in range(k - 1, i):
                vorher = bester[j][k - 1][0]
                if vorher == unmoeglich:
                    continue
                seitenlaenge = summe[i] - summe[j]
                if seitenlaenge > grenze:
                    continue
                kosten = vorher + (seitenlaenge - mittel) ** 2
                if kosten < bester[i][k][0]:
                    bester[i][k] = (kosten, j)
    if bester[n][anzahl][0] == unmoeglich:
        raise SystemExit(f"Auf {anzahl} Seiten passt es nicht unter {grenze} "
                         f"Zeichen - mehr Seiten wählen.")

    grenzen, i = [], n
    for k in range(anzahl, 0, -1):
        j = bester[i][k][1]
        grenzen.append((j, i))
        i = j
    grenzen.reverse()
    return [[abschnitt for g in gr[j:i] for abschnitt in g] for j, i in grenzen]


def main():
    quelle, erste_nr, anzahl = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    # Obergrenze: so lang wie die schon abgenommene Seite 1
    grenze = int(sys.argv[4]) if len(sys.argv) > 4 else laenge("wordpress/witze01-v01.txt")
    gr = gruppen(quelle)
    seiten = aufteilen(gr, anzahl, grenze)
    for i, abschnitte in enumerate(seiten):
        nr = erste_nr + i
        pfad = f"witze{nr:02d}.txt"
        with open(pfad, "w", encoding="utf-8") as f:
            f.write(KOPF.format(nr=nr, vor=nr - 1, nach=nr + 1))
            for name, body in abschnitte:
                f.write(f"=== {name} ===\n")
                f.write(body.strip("\n") + "\n\n")
        zeichen = sum(wp_laenge(n, b) for n, b in abschnitte)
        print(f"{pfad}: {len(abschnitte)} Witze, {zeichen} Zeichen "
              f"({abschnitte[0][0]} bis {abschnitte[-1][0]})")
    print(f"Obergrenze war {grenze} Zeichen (Seite 1)")


if __name__ == "__main__":
    main()
