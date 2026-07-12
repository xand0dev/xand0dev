"""Render a portrait photo as a monochrome ASCII terminal card.

Usage:
    python3 scripts/make_ascii_svg.py /path/to/photo.jpg assets/oleksandr-ascii.svg
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("photo.jpg")
OUTPUT = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("assets/oleksandr-ascii.svg")

COLS, ROWS = 78, 50
CELL_W, CELL_H = 8, 13
PADDING, TITLE_H, FOOTER_H = 20, 32, 34
RAMP = " .`^\\\";:!i1t+*#%@"


def ascii_rows(source: Path) -> list[str]:
    image = Image.open(source).convert("L")
    image = ImageOps.autocontrast(image, cutoff=1)
    image = ImageEnhance.Contrast(image).enhance(1.45)
    image = ImageEnhance.Brightness(image).enhance(1.08)
    image = image.resize((COLS, ROWS), Image.Resampling.LANCZOS)

    rows = []
    for y in range(ROWS):
        chars = []
        for x in range(COLS):
            luminance = image.getpixel((x, y)) / 255
            if luminance > 0.86:
                chars.append(" ")
            else:
                chars.append(RAMP[round((1 - luminance) * (len(RAMP) - 1))])
        rows.append("".join(chars))
    return rows


def render(rows: list[str]) -> str:
    art_width, art_height = COLS * CELL_W, ROWS * CELL_H
    width = art_width + PADDING * 2
    height = TITLE_H + art_height + FOOTER_H + PADDING
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
        '<defs><linearGradient id="background" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#111827"/><stop offset="1" stop-color="#0d1117"/></linearGradient></defs>',
        f'<rect width="{width}" height="{height}" rx="12" fill="url(#background)"/>',
        f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" rx="12" fill="none" stroke="#30363d"/>',
        f'<line x2="{width}" y1="{TITLE_H}" y2="{TITLE_H}" stroke="#30363d"/>',
    ]
    for index, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        parts.append(f'<circle cx="{PADDING + index * 16}" cy="16" r="5" fill="{color}"/>')
    parts.append(f'<text x="{width / 2}" y="20" fill="#8b949e" font-size="12" text-anchor="middle">oleksandr@fitgym:~$ ./portrait.sh</text>')

    top = TITLE_H + 13
    for index, row in enumerate(rows):
        safe = html.escape(row)
        y = top + (index + 1) * CELL_H
        parts.append(f'<text xml:space="preserve" x="{PADDING}" y="{y}" fill="#c9d1d9" font-size="11" textLength="{art_width}" lengthAdjust="spacing">{safe}</text>')

    footer_y = TITLE_H + art_height + 14
    parts.extend((
        f'<line x2="{width}" y1="{footer_y}" y2="{footer_y}" stroke="#30363d"/>',
        f'<text x="{PADDING}" y="{footer_y + 21}" fill="#8b949e" font-size="12">oleksandr@fitgym:~$ whoami <tspan fill="#c9d1d9">Oleksandr Riasnyi</tspan></text>',
        '</svg>',
    ))
    return "".join(parts)


OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(render(ascii_rows(SOURCE)), encoding="utf-8")
print(f"Wrote {OUTPUT}")
