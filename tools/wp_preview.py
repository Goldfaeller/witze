#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baut aus dem WordPress-Blockmarkup eine Vorschau-HTML-Datei zum Ansehen im Browser."""

import re
import sys

HEAD = """<title>Witze 1 – Seitenvorschau</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&family=Source+Serif+4:opsz,wght@8..60,600&display=swap">
<style>
:root{
  --ink:#1c1b1a;
  --ink-soft:#55514c;
  --ground:#ffffff;
  --shell:#e8e5df;
  --rule:#a2a9b1;
  --box-head:#eaecf0;
  --accent:#7a1f52;
  --magenta:#F0F;
}
*{box-sizing:border-box}
body{
  background:var(--shell);
  color:var(--ink);
  font-family:"Source Sans 3","Segoe UI",system-ui,sans-serif;
  font-size:17px;
  line-height:1.6;
  margin:0;
  padding:0 16px 64px;
}
.preview-bar{
  position:sticky;top:0;z-index:5;
  margin:0 -16px 24px;padding:10px 16px;
  background:var(--ink);color:#f4f1ec;
  display:flex;flex-wrap:wrap;gap:8px 18px;align-items:baseline;
  font-size:13px;letter-spacing:.04em;
}
.preview-bar strong{font-weight:600;text-transform:uppercase;letter-spacing:.09em}
.preview-bar span{color:#bdb6ad}
.page{
  max-width:52rem;margin:0 auto;padding:36px 40px 44px;
  background:var(--ground);
  border:1px solid #d5d1c9;
}
.page p{margin:0 0 12px;max-width:62ch}
.page a{color:var(--accent)}
h3.wp-block-heading{
  font-family:"Source Serif 4",Georgia,serif;
  font-size:1.28rem;font-weight:600;text-wrap:balance;
  margin:28px 0 10px;
}
hr.wp-block-separator{border:0;border-top:1px solid var(--rule);opacity:.5;margin:22px 0}
.pc-home-link,.pc-chapter-nav{font-size:.92rem;color:var(--ink-soft);margin-bottom:6px}
.pc-footer-nav{margin-top:28px;display:flex;flex-direction:column;gap:6px}
.pc-top-link{font-size:.92rem}
.pc-collapsible{text-align:left;margin:0 0 20px;border:1px solid var(--rule);border-radius:4px;overflow:hidden}
.pc-collapsible summary{position:relative;cursor:pointer;list-style:none;padding:10px 14px;background-color:var(--box-head);font-weight:700;text-align:center}
.pc-collapsible summary::-webkit-details-marker{display:none}
.pc-collapsible summary::marker{content:""}
.pc-collapsible summary::before{content:"\\25BA";position:absolute;left:14px;top:50%;transform:translateY(-50%);color:#333;font-weight:400;line-height:1}
.pc-collapsible[open] summary::before{content:"\\25BC"}
.pc-collapsible summary:focus-visible{outline:2px solid var(--accent);outline-offset:-2px}
.pc-collapsible .pc-collapsible-hint{position:absolute;left:34px;top:50%;transform:translateY(-50%);font-size:0.8rem;font-weight:400;line-height:1;color:#333}
.pc-collapsible .pc-collapsible-title{color:var(--magenta)}
.pc-collapsible-body{padding:14px 16px;background-color:#fff;border-top:1px solid var(--rule)}
.pc-collapsible-body p{margin:0 0 10px}
.pc-collapsible-body p:last-child{margin-bottom:0}
.pc-note{margin-left:1.5em;font-size:0.95em;color:var(--ink-soft)}
@media (max-width:640px){.page{padding:24px 18px 32px}body{font-size:16px}}
</style>"""


def main():
    src, dst = sys.argv[1], sys.argv[2]
    body = open(src, encoding="utf-8").read()
    # <style>-Block der WP-Seite entfernen: die Vorschau bringt eigene Typografie mit
    body = re.sub(r"<style>.*?</style>", "", body, flags=re.S)
    jokes = body.count('<h3 class="wp-block-heading">')
    bar = (f'<div class="preview-bar"><strong>Vorschau</strong>'
           f'<span>witze01 → WordPress · {jokes} Witze · '
           f'Aufklappboxen anklickbar</span></div>')
    html = HEAD + "\n" + bar + '\n<div class="page">\n' + body + "\n</div>\n"
    open(dst, "w", encoding="utf-8").write(html)
    sys.stderr.write(f"Vorschau geschrieben: {dst}\n")


if __name__ == "__main__":
    main()
