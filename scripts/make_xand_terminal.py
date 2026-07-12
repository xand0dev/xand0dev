"""Generate the animated XAND terminal card shown in the profile README."""
from pathlib import Path

OUTPUT = Path("assets/xand-terminal.svg")
W, H = 472, 326
PAD, TITLE_H = 22, 34
ART_X, ART_Y, ART_W = 25, 108, 422

GLYPHS = {
    "X": (
        "##       ##", " ###     ###", "  ###   ###", "   ### ### ", "    #####  ",
        "   ### ### ", "  ###   ###", " ###     ###", "##       ##",
    ),
    "A": (
        "    ###    ", "   ## ##   ", "  ##   ##  ", " ##     ## ", " ######### ",
        " ##     ## ", " ##     ## ", " ##     ## ", " ##     ## ",
    ),
    "N": (
        "##       ##", "###      ##", "####     ##", "## ##    ##", "##  ##   ##",
        "##   ##  ##", "##    ## ##", "##     ####", "##      ###",
    ),
    "D": (
        "########   ", "##      ## ", "##       ##", "##       ##", "##       ##",
        "##       ##", "##       ##", "##      ## ", "########   ",
    ),
}
SYMBOLS = {"X": "#", "A": "@", "N": "%", "D": "$"}
ART = [
    "   ".join(GLYPHS[letter][row].replace("#", SYMBOLS[letter]) for letter in "XAND")
    for row in range(9)
]


def typed_text(value: str, x: float, y: float, delay: float, *, color="#c9d1d9", size=13, bold=False) -> str:
    weight = ' font-weight="700"' if bold else ""
    width = max(1, len(value) * size * 0.64)
    return (
        f'<clipPath id="clip-{delay}"><rect x="{x}" y="{y - size}" width="0" height="{size + 6}">'
        f'<animate attributeName="width" from="0" to="{width:.0f}" begin="{delay}s" dur="0.52s" fill="freeze"/>'
        f'</rect></clipPath>'
        f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}"{weight} clip-path="url(#clip-{delay})">{value}</text>'
    )


parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace">',
    '<defs><linearGradient id="background" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#111827"/><stop offset="1" stop-color="#0d1117"/></linearGradient></defs>',
    f'<rect width="{W}" height="{H}" rx="12" fill="url(#background)"/>',
    f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="12" fill="none" stroke="#30363d"/>',
    f'<line x2="{W}" y1="{TITLE_H}" y2="{TITLE_H}" stroke="#30363d"/>',
]
for index, color in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
    parts.append(f'<circle cx="{PAD + index * 16}" cy="17" r="5" fill="{color}"/>')
parts.append(f'<text x="{W / 2}" y="21" fill="#8b949e" font-size="12" text-anchor="middle">oleksandr@fitgym:~$ ./identity.sh</text>')

parts.append(typed_text("booting founder mode...", PAD, 62, 0.1, color="#8b949e"))
parts.append(typed_text("loading: full-stack builder", PAD, 84, 0.8, color="#58a6ff"))

for index, row in enumerate(ART):
    delay = 1.55 + index * 0.1
    y = ART_Y + index * 17
    parts.append(
        f'<clipPath id="art-{index}"><rect x="{ART_X}" y="{y - 14}" width="0" height="20">'
        f'<animate attributeName="width" from="0" to="{ART_W}" begin="{delay}s" dur="0.36s" fill="freeze"/>'
        f'</rect></clipPath>'
        f'<text xml:space="preserve" x="{ART_X}" y="{y}" fill="#34d399" font-size="10.5" font-weight="700" textLength="{ART_W}" lengthAdjust="spacing" clip-path="url(#art-{index})">{row}</text>'
    )

parts.append(typed_text("XAND — build. ship. repeat.", PAD, 274, 2.65, color="#c9d1d9", bold=True))
parts.append(typed_text("status: FITGYM pilot in progress", PAD, 298, 3.25, color="#8b949e"))
parts.extend((
    f'<rect x="{PAD + 275}" y="286" width="8" height="15" fill="#34d399">'
    '<animate attributeName="opacity" values="1;1;0;0" keyTimes="0;0.5;0.51;1" dur="1s" repeatCount="indefinite"/></rect>',
    '</svg>',
))

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("".join(parts), encoding="utf-8")
print(f"Wrote {OUTPUT}")
