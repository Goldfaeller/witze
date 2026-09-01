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

    for joke in jokes:
        pairs = de = hu = []
        hu = to_paragraphs(joke["body"])
        pair_box = next((b for b in joke["boxes"] if "-" in b["title"]), None)
        de_box = next((b for b in joke["boxes"] if b is not pair_box), None)
        pairs = to_paragraphs(pair_box["lines"]) if pair_box else []
        de = to_paragraphs(de_box["lines"]) if de_box else []

        label = joke["heading"].replace(" - ", " – ")
        o.append(SEP)
        o.append("")
        o.append('<!-- wp:heading {"level":3} -->')
        o.append(f'<h3 class="wp-block-heading">{cfg["joke_word"]} {esc(label)}</h3>')
        o.append("<!-- /wp:heading -->")
        o.append("")
        o.append("<!-- wp:paragraph -->")
        for html, cls in pairs:
            o.append(p_tag(html, cls))
        o.append("<!-- /wp:paragraph -->")
        o.append("")
        o.append(collapsible("magyar", hu))
        o.append("")
        o.append(collapsible("német", de))
        o.append("")

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


CFG = {
    "title": "Witze 1",
    # Seiten-Metadaten. Stehen NICHT im Seitencode - WordPress speichert sie
    # getrennt vom Inhalt. Sie landen in der .meta.json neben der Textdatei und
    # werden entweder von Hand in der Seitenleiste eingetragen oder spaeter vom
    # Upload-Programm ueber die REST-API mitgeschickt.
    "slug": "witze-1",
    "parent": "Witze",
    "menu_order": 1,
    "joke_word": "Witz",
    "home_nav": ('<a href="/">« Home</a> &nbsp;|&nbsp; '
                 '<a href="/lesebuecher/">« zurück zu Lesebücher</a> &nbsp;|&nbsp; '
                 '<a href="/startseite/lesebuecher/inhalt-witze/">« zurück zu Inhaltsverzeichnis</a>'),
    "chapter_nav": ('<a href="/witze-0/">« Zurück zu Witze 0</a> &nbsp;|&nbsp; '
                    '<span>Witze 1</span> &nbsp;|&nbsp; '
                    '<a href="/witze-2/">Weiter zu Witze 2 »</a>'),
}


def main():
    src, dst = sys.argv[1], sys.argv[2]
    with open(src, encoding="utf-8") as f:
        text = f.read()
    intro, jokes = parse(text)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(build(intro, jokes, CFG))

    meta = {
        "post_type": "page",
        "post_title": CFG["title"],
        "post_name": CFG["slug"],
        "post_parent": CFG["parent"],
        "menu_order": CFG["menu_order"],
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
