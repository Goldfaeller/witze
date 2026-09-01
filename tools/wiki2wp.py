#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wandelt eine Wikibooks-Witzeseite (Wiki-Syntax) in WordPress-Blockmarkup um.

Quellstruktur je Witz:
    === N ===
    :ungarische Zeilen (nur ungarisch)
    {| ... !magyar - német ... |}   -> ungarisch-deutsche Satzpaare
    {| ... !deutsch ... |}          -> nur deutsch

Zielstruktur je Witz (wie internetseite-text.txt):
    Trennlinie + Überschrift "Witz N"
    ungarisch-deutsche Satzpaare (sichtbar)
    Aufklappbox "magyar" (nur ungarisch)
    Aufklappbox "német"  (nur deutsch)
"""

import json
import re
import sys

STYLE = """<!-- wp:html -->
<style>
.pc-collapsible{text-align:left;margin:0 0 20px;border:1px solid #a2a9b1;border-radius:4px;overflow:hidden}
.pc-collapsible summary{position:relative;cursor:pointer;list-style:none;padding:10px 14px;background-color:#eaecf0;font-weight:700;text-align:center}
.pc-collapsible summary::-webkit-details-marker{display:none}
.pc-collapsible summary::marker{content:""}
.pc-collapsible summary::before{content:"\\25BA";position:absolute;left:14px;top:50%;transform:translateY(-50%);color:#333;font-weight:400;line-height:1}
.pc-collapsible[open] summary::before{content:"\\25BC"}
.pc-collapsible .pc-collapsible-hint{position:absolute;left:34px;top:50%;transform:translateY(-50%);font-size:0.8rem;font-weight:400;line-height:1;color:#333}
.pc-collapsible .pc-collapsible-title{color:#F0F}
.pc-collapsible-body{padding:14px 16px;background-color:#fff;border-top:1px solid #a2a9b1}
.pc-collapsible-body p{margin:0 0 10px}
.pc-collapsible-body p:last-child{margin-bottom:0}
.pc-note{margin-left:1.5em;font-size:0.95em}
.pc-gruppe{margin:42px 0 4px;padding-top:16px;border-top:3px double #a2a9b1;font-size:1.5rem;line-height:1.25;color:#1a252f}
</style>
<!-- /wp:html -->"""

SEP = """<!-- wp:separator -->
<hr class="wp-block-separator has-alpha-channel-opacity"/>
<!-- /wp:separator -->"""


def esc(text):
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))


def inline(text):
    """Wiki-Inline-Auszeichnung -> HTML."""
    text = esc(text.strip())
    text = re.sub(r"'''(.+?)'''", r"<strong>\1</strong>", text)
    text = re.sub(r"''(.+?)''", r"<em>\1</em>", text)
    return text


def to_paragraphs(lines):
    """Wiki-Zeilen (':', '::') -> Liste von (html, css_klasse)."""
    out = []
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            continue
        depth = 0
        while line.startswith(":"):
            depth += 1
            line = line[1:]
        content = inline(line)
        if not content:
            continue
        if depth == 0 and out:
            # Fortsetzungszeile ohne Doppelpunkt -> an vorherigen Absatz anhängen
            prev, cls = out[-1]
            out[-1] = (prev + " " + content, cls)
            continue
        out.append((content, "pc-note" if depth >= 2 else ""))
    return out


def p_tag(html, cls):
    return f'<p class="{cls}">{html}</p>' if cls else f"<p>{html}</p>"


def wp_paragraph_block(html, cls):
    return "<!-- wp:paragraph -->\n" + p_tag(html, cls) + "\n<!-- /wp:paragraph -->"


def collapsible(title, paragraphs):
    parts = ["<!-- wp:html -->",
             '<details class="pc-collapsible">',
             f'  <summary><span class="pc-collapsible-hint">(aufklappen)</span>'
             f'<span class="pc-collapsible-title">{title}</span></summary>',
             '  <div class="pc-collapsible-body">',
             "<!-- /wp:html -->",
             ""]
    for html, cls in paragraphs:
        parts.append(wp_paragraph_block(html, cls))
        parts.append("")
    parts += ["<!-- wp:html -->", "  </div>", "</details>", "<!-- /wp:html -->"]
    return "\n".join(parts)


def parse(text):
    """Zerlegt den Wikitext in (Intro-Zeilen, Liste von Witzen)."""
    lines = text.splitlines()

    # 1) Navigationsvorlagen {{...}} am Seitenanfang entfernen
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("{{"):
            while i < len(lines) and not lines[i].rstrip().endswith("}}"):
                i += 1
            i += 1
            continue
        if s == "" or s == ":":
            i += 1
            continue
        break

    intro, jokes = [], []
    heading = None
    cur = {"body": [], "boxes": []}
    box = None

    def flush():
        if heading is not None:
            jokes.append({"heading": heading,
                          "body": cur["body"],
                          "boxes": cur["boxes"]})

    while i < len(lines):
        line = lines[i]
        s = line.strip()
        m = re.match(r"^=+\s*(.*?)\s*=+$", s)
        if m:
            flush()
            heading = m.group(1)
            cur = {"body": [], "boxes": []}
            box = None
            i += 1
            continue
        if s.startswith("{|"):
            box = {"title": "", "lines": []}
            i += 1
            continue
        if box is not None:
            if s.startswith("|}"):
                cur["boxes"].append(box)
                box = None
            elif s.startswith("!"):
                t = re.sub(r"<[^>]+>", "", s.lstrip("!"))
                box["title"] = t.replace("'''", "").strip()
            elif s in ("|-", "|"):
                pass
            else:
                box["lines"].append(line)
            i += 1
            continue
        if heading is None:
            intro.append(line)
        else:
            cur["body"].append(line)
        i += 1

    flush()
    return intro, jokes


def ohne_markup(html):
    return re.sub(r"<[^>]+>", "", html)


def gruppentitel(hu, pairs, heading):
    """Trägt der Witz einen Gruppentitel ("Szőke viccek", "Elefántviccek")?

    Diese Titel stehen im Quelltext als erste, unnummerierte Zeile des Witzes.
    Erkennungsmerkmal: kurz, ohne Satzzeichen am Ende, ohne Anführungszeichen -
    sonst ist es der erste Satz des Witzes und keine Überschrift.
    """
    zusatz = re.match(r"^\d+[a-z]?\s*[-–]\s*(.+)$", heading)
    aus_heading = zusatz.group(1).strip() if zusatz else None

    if hu and pairs and hu[0][1] == "" and pairs[0][1] == "":
        erste = ohne_markup(hu[0][0]).strip()
        paar = ohne_markup(pairs[0][0]).strip()
        # Nur wenn die erste Zeile in beiden Fassungen dieselbe ist, gehört sie
        # zusammen; sonst steht der Titel gar nicht im Satzpaar-Block und man
        # risse den ersten Satz des Witzes heraus.
        # Doppelpunkt am Zeilenende steht in den Vorlagen mal hier, mal dort
        kern = erste.rstrip(":.,; ")
        if (not re.match(r"^\d+\.", erste) and not re.match(r"^\d+\.", paar)
                and paar.startswith(kern) and len(erste) <= 30
                and not any(z in erste for z in "„”\"!?")):
            return pairs[0][0], True
    if aus_heading:
        return esc(aus_heading), False
    return None, False


def joke_block(joke, cfg):
    """Ein Witz als fertiges WordPress-Blockmarkup.

    Wird auch von seiten_aufteilen.py benutzt, um die Länge einer Seite am
    fertigen Seitencode zu messen statt an der Wikivorlage.
    """
    hu = to_paragraphs(joke["body"])
    pair_box = next((b for b in joke["boxes"] if "-" in b["title"]), None)
    de_box = next((b for b in joke["boxes"] if b is not pair_box), None)
    pairs = to_paragraphs(pair_box["lines"]) if pair_box else []
    de = to_paragraphs(de_box["lines"]) if de_box else []

    titel, aus_text = gruppentitel(hu, pairs, joke["heading"])
    if titel and aus_text:
        # Der Titel wandert in die Überschrift - im Fließtext wäre er doppelt.
        # In den einsprachigen Boxen bleibt er stehen, damit die für sich
        # gelesen werden können.
        pairs = pairs[1:]

    o = []
    if titel:
        o += ['<!-- wp:heading {"level":2,"className":"pc-gruppe"} -->',
              f'<h2 class="wp-block-heading pc-gruppe">{titel}</h2>',
              "<!-- /wp:heading -->",
              ""]

    o += [SEP,
          "",
          '<!-- wp:heading {"level":3} -->',
          f'<h3 class="wp-block-heading">{cfg["joke_word"]} '
          f'{esc(joke["nummer"])}</h3>',
          "<!-- /wp:heading -->",
          "",
          "<!-- wp:paragraph -->"]
    o += [p_tag(html, cls) for html, cls in pairs]
    o += ["<!-- /wp:paragraph -->",
          "",
          collapsible("magyar", hu),
          "",
          collapsible("német", de),
          ""]
    return "\n".join(o)


def build(intro, jokes, cfg):
    o = []
    o.append(STYLE)
    o.append("")
    o.append('<!-- wp:group {"className":"pc-container","anchor":"top"} -->')
    o.append('<div id="top" class="wp-block-group pc-container"><!-- wp:html -->')
    o.append('<div class="pc-home-link">')
    o.append(f'  {cfg["home_nav"]}')
    o.append("</div>")
    o.append('<div class="pc-chapter-nav">')
    o.append(f'  {cfg["chapter_nav"]}')
    o.append("</div>")
    o.append("<!-- /wp:html -->")
    o.append("")
    o.append(SEP)
    o.append("")
    o.append("<!-- wp:paragraph -->")
    o.append(f'<p><strong>{cfg["title"]}</strong></p>')
    o.append("<!-- /wp:paragraph -->")
    o.append("")

    # Vorspann der Wikiseite (";1. Teil - Kurze Witze", Hinweise usw.)
    for raw in intro:
        line = raw.strip()
        if not line:
            continue
        if line.startswith(";"):
            o.append("<!-- wp:paragraph -->")
            o.append(f"<p><strong>{inline(line[1:])}</strong></p>")
            o.append("<!-- /wp:paragraph -->")
            o.append("")
            continue
        for html, cls in to_paragraphs([raw]):
            o.append(wp_paragraph_block(html, cls))
            o.append("")

    # Auf jeder Seite beginnt die Zählung wieder bei 1. Zusammengehörig sind
    # die Varianten a/b/c eines Witzes - erkennbar an der fortlaufenden
    # Buchstabenfolge, nicht an der Nummer davor: in den Vorlagen stehen
    # Zahlendreher (zweimal "40b", "30b" statt "300b"), die Gruppen sonst
    # zerreißen oder doppelte Nummern erzeugen würden.
    gruppen, vorheriger = [], None
    for joke in jokes:
        buchstabe = re.match(r"^\d*([a-z]?)", joke["heading"]).group(1)
        fortsetzung = (buchstabe and vorheriger
                       and ord(buchstabe) == ord(vorheriger) + 1)
        if fortsetzung:
            gruppen[-1].append(joke)
        else:
            gruppen.append([joke])
        vorheriger = buchstabe or None

    for nr, gruppe in enumerate(gruppen, start=1):
        for stelle, joke in enumerate(gruppe):
            # Ein Buchstabe nur, wo es wirklich mehrere Varianten gibt
            joke["nummer"] = (f"{nr}{chr(ord('a') + stelle)}" if len(gruppe) > 1
                              else f"{nr}")

    for joke in jokes:
        o.append(joke_block(joke, cfg))

    o.append(SEP)
    o.append("")
    o.append("<!-- wp:html -->")
    o.append('<div class="pc-footer-nav">')
    o.append('  <div class="pc-top-link"><a href="#top">↑ Hoch zum Seitenanfang</a></div>')
    o.append('  <div class="pc-chapter-nav">')
    o.append(f'  {cfg["chapter_nav"]}')
    o.append("</div>")
    o.append('  <div class="pc-home-link">')
    o.append(f'  {cfg["home_nav"]}')
    o.append("</div>")
    o.append("</div>")
    o.append("<!-- /wp:html --></div>")
    o.append("<!-- /wp:group -->")
    return "\n".join(o) + "\n"


HOME_NAV = ('<a href="/">« Home</a> &nbsp;|&nbsp; '
            '<a href="/lesebuecher/">« zurück zu Lesebücher</a> &nbsp;|&nbsp; '
            '<a href="/startseite/lesebuecher/inhalt-witze/">'
            '« zurück zu Inhaltsverzeichnis</a>')


def konfiguration(nr):
    """Alles, was sich von Seite zu Seite unterscheidet - aus der Seitennummer.

    Die Metadaten (Titel, Permalink, übergeordnete Seite, Reihenfolge) stehen
    NICHT im Seitencode: WordPress speichert sie getrennt vom Inhalt. Sie landen
    in der .meta.json neben der Textdatei und werden entweder von Hand in der
    Seitenleiste eingetragen oder später vom Upload-Programm über die REST-API
    mitgeschickt.
    """
    return {
        "title": f"Witze {nr}",
        "slug": f"{nr}-witze",
        "parent": "Witze",
        "menu_order": nr,
        # Seite 41 sind Sprüche, keine Witze
        "joke_word": {41: "Spruch"}.get(nr, "Witz"),
        "home_nav": HOME_NAV,
        "chapter_nav": (f'<a href="/{nr - 1}-witze/">« Zurück zu Witze {nr - 1}</a>'
                        f' &nbsp;|&nbsp; <span>Witze {nr}</span> &nbsp;|&nbsp; '
                        f'<a href="/{nr + 1}-witze/">Weiter zu Witze {nr + 1} »</a>'),
    }


def main():
    src, dst, nr = sys.argv[1], sys.argv[2], int(sys.argv[3])
    cfg = konfiguration(nr)
    with open(src, encoding="utf-8") as f:
        text = f.read()
    intro, jokes = parse(text)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(build(intro, jokes, cfg))

    meta = {
        "post_type": "page",
        "post_title": cfg["title"],
        "post_name": cfg["slug"],
        "post_parent": cfg["parent"],
        "menu_order": cfg["menu_order"],
        "content_file": dst,
        "jokes": len(jokes),
    }
    meta_path = re.sub(r"\.txt$", "", dst) + ".meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")
    sys.stderr.write(f"{len(jokes)} Witze umgewandelt -> {dst}\n")
    sys.stderr.write(f"Metadaten (inkl. Uebergeordnet) -> {meta_path}\n")


if __name__ == "__main__":
    main()
