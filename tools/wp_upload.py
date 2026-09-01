#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schiebt die fertigen Seiten über die WordPress-REST-API auf die Internetseite.

Zu jeder Seite gehören zwei Dateien:
    wordpress/witze01-v01.txt        der Seiteninhalt
    wordpress/witze01-v01.meta.json  Titel, Permalink, Übergeordnet, Reihenfolge

Gibt es die Seite auf der Website schon (erkannt am Permalink), wird sie
aktualisiert, sonst neu angelegt.

Zugangsdaten kommen aus Umgebungsvariablen, nie aus dem Programm:
    WP_URL           https://modjor.de
    WP_USER          dein WordPress-Benutzername
    WP_APP_PASSWORD  ein Anwendungspasswort, NICHT das Anmeldepasswort

Ohne weitere Angabe wird nur geprüft und angezeigt, was geschähe. Erst
--hochladen schreibt wirklich auf die Website.
"""

import argparse
import base64
import glob
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


class Wordpress:
    def __init__(self, basis, benutzer, passwort):
        self.basis = basis.rstrip("/") + "/wp-json/wp/v2"
        schluessel = base64.b64encode(
            f"{benutzer}:{passwort}".encode("utf-8")).decode("ascii")
        self.kopf = {
            "Authorization": f"Basic {schluessel}",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": "witze-upload/1.0",
        }

    def _ruf(self, weg, methode="GET", daten=None):
        rumpf = json.dumps(daten).encode("utf-8") if daten is not None else None
        anfrage = urllib.request.Request(self.basis + weg, data=rumpf,
                                         headers=self.kopf, method=methode)
        try:
            with urllib.request.urlopen(anfrage, timeout=60) as antwort:
                return json.loads(antwort.read().decode("utf-8"))
        except urllib.error.HTTPError as fehler:
            text = fehler.read().decode("utf-8", "replace")[:400]
            raise SystemExit(
                f"\nWordPress antwortet mit {fehler.code} auf {methode} {weg}\n"
                f"{text}\n\n"
                "401/403 heißt meist: Benutzername oder Anwendungspasswort\n"
                "stimmen nicht, oder der Webserver reicht den Authorization-Kopf\n"
                "nicht an PHP weiter.\n"
                "404 auf /wp-json/ heißt: die REST-API ist abgeschaltet oder die\n"
                "Permalinks stehen auf 'Einfach'.")
        except urllib.error.URLError as fehler:
            raise SystemExit(f"\nKeine Verbindung zu {self.basis}: {fehler.reason}")

    def seite_zu_permalink(self, slug):
        weg = "/pages?" + urllib.parse.urlencode(
            {"slug": slug, "status": "publish,draft,pending,private", "per_page": 1})
        treffer = self._ruf(weg)
        return treffer[0] if treffer else None

    def seite_zu_titel(self, titel):
        weg = "/pages?" + urllib.parse.urlencode(
            {"search": titel, "status": "publish,draft,pending,private",
             "per_page": 100})
        for seite in self._ruf(weg):
            if seite["title"]["rendered"].strip() == titel:
                return seite
        return None

    def anlegen(self, felder):
        return self._ruf("/pages", "POST", felder)

    def aendern(self, seiten_id, felder):
        return self._ruf(f"/pages/{seiten_id}", "POST", felder)


def seiten_einlesen(muster):
    """Alle Seiten mit ihren Metadaten, nach Dateinamen sortiert."""
    out = []
    for pfad in sorted(glob.glob(muster)):
        meta_pfad = pfad[:-4] + ".meta.json"
        if not os.path.exists(meta_pfad):
            print(f"  übersprungen (keine Metadaten): {pfad}")
            continue
        with open(meta_pfad, encoding="utf-8") as f:
            meta = json.load(f)
        with open(pfad, encoding="utf-8") as f:
            meta["content"] = f.read()
        meta["_datei"] = pfad
        out.append(meta)
    return out


def main():
    p = argparse.ArgumentParser(
        description="Witzeseiten auf die WordPress-Seite schieben.")
    p.add_argument("muster", nargs="?", default="wordpress/*.txt",
                   help="welche Dateien (Vorgabe: wordpress/*.txt)")
    p.add_argument("--hochladen", action="store_true",
                   help="wirklich schreiben; ohne das wird nur angezeigt")
    p.add_argument("--veroeffentlichen", action="store_true",
                   help="neue Seiten sofort veröffentlichen statt als Entwurf")
    p.add_argument("--ohne-uebergeordnet", action="store_true",
                   help="das Feld Übergeordnet nicht setzen (Permalink bleibt flach)")
    args = p.parse_args()

    basis = os.environ.get("WP_URL")
    benutzer = os.environ.get("WP_USER")
    passwort = os.environ.get("WP_APP_PASSWORD")
    if not (basis and benutzer and passwort):
        raise SystemExit(
            "Es fehlen Zugangsdaten. Erwartet werden die Umgebungsvariablen\n"
            "  WP_URL           z.B. https://modjor.de\n"
            "  WP_USER          dein WordPress-Benutzername\n"
            "  WP_APP_PASSWORD  ein Anwendungspasswort\n\n"
            "Setze sie in hochladen.bat und starte das Programm darüber.")

    seiten = seiten_einlesen(args.muster)
    if not seiten:
        raise SystemExit(f"Keine Dateien gefunden zu: {args.muster}")

    # Zwei Dateien mit demselben Permalink wären zwei Fassungen derselben Seite -
    # die zweite überschriebe die erste. Lieber vorher abbrechen.
    doppelt = {}
    for s in seiten:
        doppelt.setdefault(s["post_name"], []).append(s["_datei"])
    mehrfach = {k: v for k, v in doppelt.items() if len(v) > 1}
    if mehrfach:
        zeilen = "\n".join(f"  {k}: " + ", ".join(v) for k, v in mehrfach.items())
        raise SystemExit(
            "Mehrere Dateien wollen auf denselben Permalink:\n" + zeilen +
            "\n\nDie zweite würde die erste überschreiben. Entweder eine der\n"
            "Dateien aussortieren oder das Muster enger fassen, zum Beispiel:\n"
            '  python tools/wp_upload.py "wordpress/*-v02.txt"')

    wp = Wordpress(basis, benutzer, passwort)
    print(f"Website : {basis}")
    print(f"Benutzer: {benutzer}")
    print(f"Dateien : {len(seiten)}")
    print("Modus   : " + ("HOCHLADEN - es wird geschrieben"
                          if args.hochladen else
                          "nur prüfen - es wird nichts geändert"))
    print()

    # Übergeordnete Seiten einmal nachschlagen und merken, nicht je Seite neu
    eltern_cache = {}

    def eltern_suchen(name):
        if args.ohne_uebergeordnet or not name:
            return None
        if name not in eltern_cache:
            gefunden = wp.seite_zu_titel(name)
            eltern_cache[name] = gefunden
            if gefunden:
                print(f"Übergeordnete Seite '{name}': Nummer {gefunden['id']}, "
                      f"Permalink /{gefunden['slug']}/")
                print(f"  ACHTUNG: die Adressen lauten damit "
                      f"/{gefunden['slug']}/<permalink>/ statt /<permalink>/.")
                print("  Soll das nicht sein: mit --ohne-uebergeordnet starten.")
            else:
                print(f"Übergeordnete Seite '{name}' nicht gefunden - "
                      f"das Feld bleibt leer.")
        return eltern_cache[name]

    neu = geaendert = 0
    for s in seiten:
        vorhanden = wp.seite_zu_permalink(s["post_name"])
        felder = {
            "title": s["post_title"],
            "slug": s["post_name"],
            "content": s["content"],
            "menu_order": s.get("menu_order", 0),
        }
        eltern = eltern_suchen(s.get("post_parent"))
        if eltern:
            felder["parent"] = eltern["id"]

        if vorhanden:
            zustand = f"ändern  (Nummer {vorhanden['id']})"
            geaendert += 1
        else:
            felder["status"] = "publish" if args.veroeffentlichen else "draft"
            zustand = f"anlegen ({felder['status']})"
            neu += 1
        print(f"  {s['post_name']:<14} {s['post_title']:<12} "
              f"{len(s['content']):>7} Zeichen  {zustand}")

        if args.hochladen:
            ergebnis = (wp.aendern(vorhanden["id"], felder) if vorhanden
                        else wp.anlegen(felder))
            print(f"      -> {ergebnis.get('link', '(keine Adresse gemeldet)')}")

    print(f"\n{neu} anzulegen, {geaendert} zu ändern.")
    if not args.hochladen:
        print("Nichts geschrieben. Zum wirklichen Hochladen: --hochladen anhängen.")


if __name__ == "__main__":
    main()
