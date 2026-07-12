"""Render the FITGYM profile card used in the README hero."""
from __future__ import annotations

import html
from pathlib import Path

OUTPUT = Path("assets/fitgym-card.svg")
W, H = 472, 326
PAD, TITLE_H, LINE_H = 22, 32, 23
ROWS = [
    ("host",),
    ("kv", "Now", "Building FITGYM"),
    ("kv", "Role", "Founder · Full-stack developer"),
    ("kv", "Focus", "SaaS · payments · multi-tenancy"),
    ("kv", "Stack", "Django · React · React Native"),
    ("gap",),
    ("section", "By day / By night"),
    ("kv", "By day", "Sysadmin & programming instructor"),
    ("kv", "By night", "Shipping FITGYM end-to-end"),
    ("gap",),
    ("section", "Current milestone"),
    ("bullet", "Preparing the Berdychiv Sky pilot"),
]


def text(x: float, y: float, value: str, fill: str, size: float, weight: int = 400) -> str:
    return f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}">{html.escape(value)}</text>'


parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
    '<defs><linearGradient id="background" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#111827"/><stop offset="1" stop-color="#0d1117"/></linearGradient></defs>',
    f'<rect width="{W}" height="{H}" rx="12" fill="url(#background)"/>',
    f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="#30363d"/>',
    f'<line x2="{W}" y1="{TITLE_H}" y2="{TITLE_H}" stroke="#30363d"/>',
]
for index, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
    parts.append(f'<circle cx="{PAD + index * 16}" cy="16" r="5" fill="{color}"/>')
parts.append(text(W / 2, 20, "oleksandr@fitgym:~$ neofetch", "#8b949e", 12))

y = TITLE_H + 29
for row in ROWS:
    kind = row[0]
    if kind == "gap":
        y += LINE_H * 0.45
    elif kind == "host":
        parts.append(text(PAD, y, "oleksandr@github", "#3fb950", 14, 700))
        parts.append(f'<line x1="{PAD + 145}" x2="{W - PAD}" y1="{y - 5}" y2="{y - 5}" stroke="#30363d"/>')
        y += LINE_H
    elif kind == "section":
        title = row[1]
        parts.append(text(PAD, y, f"— {title}", "#58a6ff", 12.5, 700))
        parts.append(f'<line x1="{PAD + 155}" x2="{W - PAD}" y1="{y - 4}" y2="{y - 4}" stroke="#30363d"/>')
        y += LINE_H
    elif kind == "kv":
        parts.append(text(PAD, y, row[1], "#ffa657", 12.5, 700))
        parts.append(text(PAD + 88, y, row[2], "#c9d1d9", 12.5))
        y += LINE_H
    elif kind == "bullet":
        parts.append(f'<circle cx="{PAD + 4}" cy="{y - 4}" r="3" fill="#3fb950"/>')
        parts.append(text(PAD + 16, y, row[1], "#c9d1d9", 12.5))
        y += LINE_H

parts.append('</svg>')
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("".join(parts), encoding="utf-8")
print(f"Wrote {OUTPUT}")
