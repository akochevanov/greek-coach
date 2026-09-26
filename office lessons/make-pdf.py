#!/usr/bin/env python3
"""Собирает из md-файла темы одностраничную шпаргалку в PDF (печать через Chrome).

Использование: python3 "make-pdf.py" рецепты-еда-готовка.md
"""
import html
import re
import subprocess
import sys
from pathlib import Path

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CSS = """
@page { size: A4 portrait; margin: 8mm 8mm 6mm; }
* { box-sizing: border-box; }
body {
  font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
  font-size: __SIZE__pt; line-height: 1.28; margin: 0; color: #111;
}
h1 { font-size: 13pt; margin: 0 0 1mm; }
.lead { font-size: 6.6pt; color: #555; margin: 0 0 2.5mm; }
.cols { column-count: 2; column-gap: 6mm; column-fill: auto; }
section { break-inside: avoid-column; margin-bottom: 2.5mm; }
h2 {
  font-size: 8.4pt; margin: 0 0 1mm; padding-bottom: 0.6mm;
  border-bottom: 1px solid #111; break-after: avoid;
}
table { width: 100%; border-collapse: collapse; }
td { padding: 0.35mm 1mm 0.35mm 0; vertical-align: top; }
tr:nth-child(even) { background: #f4f4f4; }
td.ru { width: 47%; color: #333; }
td.el { width: 53%; font-weight: 600; }
"""


def parse(md: str):
    title = re.search(r"^# (.+)$", md, re.M).group(1)
    lead = md.split("---")[0].split("\n", 1)[1].strip().replace("\n", " ")
    sections = []
    for block in re.split(r"^## ", md, flags=re.M)[1:]:
        name, _, body = block.partition("\n")
        rows = [
            (c[0].strip(), c[1].strip())
            for line in body.splitlines()
            if line.startswith("|") and "---" not in line
            for c in [line.strip("|").split("|")]
            if len(c) == 2 and c[0].strip() not in ("Русский",)
        ]
        if rows:
            sections.append((name.strip().strip("-").strip(), rows))
    return title, lead, sections


def render(title, lead, sections, size):
    parts = []
    for name, rows in sections:
        body = "".join(
            f'<tr><td class="ru">{html.escape(ru)}</td>'
            f'<td class="el">{html.escape(el)}</td></tr>'
            for ru, el in rows
        )
        parts.append(
            f"<section><h2>{html.escape(name)} "
            f"<span style='font-weight:400;color:#777'>({len(rows)})</span></h2>"
            f"<table>{body}</table></section>"
        )
    return (
        f"<!doctype html><meta charset='utf-8'>"
        f"<style>{CSS.replace('__SIZE__', str(size))}</style>"
        f"<h1>{html.escape(title)}</h1><p class='lead'>{html.escape(lead)}</p>"
        f"<div class='cols'>{''.join(parts)}</div>"
    )


def page_count(pdf: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page[^s]", pdf.read_bytes()))


def main():
    src = Path(sys.argv[1] if len(sys.argv) > 1 else "рецепты-еда-готовка.md")
    if not src.is_absolute():
        src = Path(__file__).parent / src
    title, lead, sections = parse(src.read_text(encoding="utf-8"))
    tmp_html = src.with_suffix(".print.html")
    pdf = src.with_suffix(".pdf")

    # Шрифт подбираем вниз, пока всё не уместится на одном листе.
    for size in (8.0, 7.6, 7.2, 6.8, 6.4, 6.0, 5.6, 5.2):
        tmp_html.write_text(render(title, lead, sections, size), encoding="utf-8")
        subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf}", tmp_html.as_uri()],
            check=True, capture_output=True,
        )
        if page_count(pdf) == 1:
            print(f"готово: {pdf} (шрифт {size}pt)")
            break
    else:
        print(f"не уместилось на один лист: {pdf}")
    tmp_html.unlink()


if __name__ == "__main__":
    main()
