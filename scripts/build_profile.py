#!/usr/bin/env python3
"""Generate the SVG assets for the xand0dev profile README.

Copy lives in this file; live numbers (contributions, stars, releases) come
from the GitHub GraphQL API. Runs locally (falls back to `gh auth token`) and
in CI (GITHUB_TOKEN). Standard library only.

    python3 scripts/build_profile.py
"""
import datetime as dt
import json
import math
import os
import random
import re
import subprocess
import urllib.request
from html import escape
from pathlib import Path

USER = "xand0dev"
OUT = Path(__file__).resolve().parent.parent / "assets"

SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# brushed steel on black, red light from the core
BG, CARD = "#000000", "#050506"
TEXT, STEEL, BODY, MUTED, DIM = "#F2F3F5", "#C9CDD3", "#9A9FA7", "#8B8F96", "#5E636B"
RED, HOT = "#E0101A", "#FF2A2A"
STEEL_RIM = "#9EA4AD"

CSS = f"""
.s{{font-family:{SANS}}} .m{{font-family:{MONO}}}
@keyframes breathe{{0%,100%{{opacity:1}}50%{{opacity:.45}}}}
.breathe{{animation:breathe 4s ease-in-out infinite}}
"""

DEFS = f"""
<linearGradient id="edge" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#34363B"/><stop offset=".5" stop-color="#16171A"/><stop offset="1" stop-color="#26282C"/>
</linearGradient>
<filter id="glow" x="-100%" y="-100%" width="300%" height="300%">
  <feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
</filter>
<radialGradient id="redLight"><stop offset="0" stop-color="{RED}" stop-opacity=".5"/>
  <stop offset=".4" stop-color="{RED}" stop-opacity=".12"/><stop offset="1" stop-color="{RED}" stop-opacity="0"/></radialGradient>
"""


# ---------------------------------------------------------------- data

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
    voidbar: repository(name: "VoidBar") { stargazerCount latestRelease { tagName } }
  }
}
"""


def token():
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        if os.environ.get(key):
            return os.environ[key]
    return subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def fetch():
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token()}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(payload["errors"])
    return payload["data"]["user"]


STATS = Path(__file__).resolve().parent / "stats.json"
PRIVATE_REPOS = {
    "fitgym": ["FITGYM-backend", "FITGYM-frontend", "FITGYM-mobile", "FITGYM-packages"],
    "skillforge": ["skillforge"],
    "leadforge": ["leadforge"],
    "cognitrace": ["CogniTrace"],
}


def proof():
    """My commit counts in private repos and TraceFlow's Marketplace downloads.

    CI's token cannot read private repos, so whatever a run can't fetch comes from the last
    cached value in scripts/stats.json (refreshed whenever the script runs locally)."""
    cached = json.loads(STATS.read_text()) if STATS.exists() else {}
    fresh = dict(cached)
    for key, repos in PRIVATE_REPOS.items():
        try:
            total = 0
            for repo in repos:
                req = urllib.request.Request(
                    f"https://api.github.com/repos/{USER}/{repo}/contributors?per_page=100",
                    headers={"Authorization": f"bearer {token()}"},
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    total += next((c["contributions"] for c in json.load(resp) if c["login"] == USER), 0)
            fresh[key] = total
        except Exception:
            pass
    try:
        req = urllib.request.Request(
            "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery",
            data=json.dumps({"filters": [{"criteria": [{"filterType": 7, "value": "xand0dev.traceflow-viz"}]}], "flags": 256}).encode(),
            headers={"Content-Type": "application/json", "Accept": "application/json;api-version=7.1-preview.1"},
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            ext = json.load(resp)["results"][0]["extensions"][0]
        fresh["traceflow_downloads"] = int(next(x["value"] for x in ext["statistics"] if x["statisticName"] == "downloadCount"))
    except Exception:
        pass
    if fresh != cached:
        STATS.write_text(json.dumps(fresh, indent=2) + "\n")
    return fresh


def calendar_stats(weeks):
    days = [d for w in weeks for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in days]
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    best = max(days, key=lambda d: d["contributionCount"])
    return dict(longest=longest, best=best)


# ---------------------------------------------------------------- svg helpers


def static(body):
    """Layout groups carry no entry animation: every frame, including the first, shows everything."""
    return re.sub(r'<g class="in"(?: style="animation-delay:[\d.]+s")?>', "<g>", body)


def svg(w, h, title, body, narrow=None):
    """narrow: below this rendered width (px) the `.full` layout swaps for `.compact`, so
    cards stay readable when GitHub shrinks them on a phone."""
    css = CSS + (
        f".compact{{display:none}} @media (max-width:{narrow}px){{.full{{display:none}} .compact{{display:inline}}}}"
        if narrow else ""
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-label="{escape(title)}">\n<title>{escape(title)}</title>\n'
        f"<style>{css}</style>\n<defs>{DEFS}</defs>\n{static(body)}\n</svg>\n"
    )


def text(x, y, s, size, fill, cls="s", weight=None, anchor=None, ls=None, extra=""):
    attrs = f'x="{x}" y="{y}" class="{cls}" font-size="{size}" fill="{fill}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    if ls is not None:
        attrs += f' letter-spacing="{ls}"'
    return f"<text {attrs} {extra}>{s}</text>"


def delay(s):
    return f'style="animation-delay:{s:.2f}s"'


def hexpts(cx, cy, r, start=-90):
    return [
        (cx + r * math.cos(math.radians(start + 60 * i)), cy + r * math.sin(math.radians(start + 60 * i)))
        for i in range(6)
    ]


def pts(ps):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in ps)


def closed(ps):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in ps) + " Z"


def frame(w, h, rx=16):
    return (
        f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{rx}" fill="{CARD}" stroke="url(#edge)" stroke-width="1.5"/>'
    )


# ---------------------------------------------------------------- hero


def sparks(x, y, t, T, rnd, count=5, spread=1.0):
    """Hot sparks thrown out of a contact point at time t: short arcs that fall and fade."""
    out = []
    for _ in range(count):
        dx = rnd.choice((-1, 1)) * rnd.uniform(18, 62) * spread
        h, dy = rnd.uniform(10, 38) * spread, rnd.uniform(12, 42)
        life = rnd.uniform(0.35, 0.6)
        t0 = t + rnd.uniform(0, 0.04)
        kt = f"0;{t0 / T:.4f};{(t0 + life) / T:.4f};1"
        col = rnd.choice(("#FFFFFF", "#FFF1E0", "#FFD9C2"))
        out.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.uniform(0.8, 1.4):.1f}" fill="{col}" opacity="0">'
            f'<animateMotion dur="{T}s" repeatCount="indefinite" path="M0 0 Q{dx * 0.55:.0f} {-h:.0f} {dx:.0f} {dy:.0f}" '
            f'keyPoints="0;0;1;1" keyTimes="{kt}" calcMode="linear"/>'
            f'<animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" values="0;0;1;0;0" '
            f'keyTimes="0;{(t0 - 0.01) / T:.4f};{t0 / T:.4f};{(t0 + life) / T:.4f};1"/></circle>'
        )
    return "".join(out)


def aura(cx, cy, u, ignite, E, T):
    """Light that lives only while the core burns: rays through the frame, a humming floor field.
    Embers drift up around the cube all the time, so the scene never goes dead."""
    lit = (
        f'<animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" '
        f'keyTimes="0;{(E - 0.05) / T:.4f};{E / T:.4f};{(ignite + 0.05) / T:.4f};{(ignite + 0.6) / T:.4f};1" values="1;1;0;0;1;1"/>'
    )
    R = u * 10

    def rays(count, width, dur, direction, opacity):
        wedges = []
        for i in range(count):
            a = 2 * math.pi * i / count
            p1 = (cx + R * math.cos(a - width), cy + R * math.sin(a - width))
            p2 = (cx + R * math.cos(a + width), cy + R * math.sin(a + width))
            wedges.append(f'<polygon points="{cx},{cy} {p1[0]:.0f},{p1[1]:.0f} {p2[0]:.0f},{p2[1]:.0f}"/>')
        spin = "0;360" if direction > 0 else "360;0"
        return (
            f'<g fill="url(#rayLight)" opacity="{opacity}"><animateTransform attributeName="transform" type="rotate" '
            f'values="{spin.split(";")[0]} {cx} {cy};{spin.split(";")[1]} {cx} {cy}" dur="{dur}s" repeatCount="indefinite"/>'
            + "".join(wedges) + "</g>"
        )

    fy = cy + 2.5 * u  # the cube's floor plane
    field = "".join(
        f'<ellipse cx="{cx}" cy="{fy:.0f}" rx="{u * 3}" ry="{u * 1.73:.0f}" fill="none" stroke="{HOT}" stroke-width="1.4">'
        f'<animate attributeName="rx" values="{u * 3};{u * 8.5:.0f}" dur="2.4s" begin="{d}s" repeatCount="indefinite"/>'
        f'<animate attributeName="ry" values="{u * 1.73:.0f};{u * 4.9:.0f}" dur="2.4s" begin="{d}s" repeatCount="indefinite"/>'
        f'<animate attributeName="stroke-opacity" values=".55;0" dur="2.4s" begin="{d}s" repeatCount="indefinite"/></ellipse>'
        for d in (0, 0.8, 1.6)
    )
    rnd = random.Random(23)
    embers = []
    for _ in range(10):
        x0 = cx + rnd.uniform(-7, 7) * u
        y0 = cy + rnd.uniform(2, 5.5) * u
        rise = rnd.uniform(4.5, 8) * u
        sway = rnd.uniform(-1, 1) * u
        dur = rnd.uniform(5, 9)
        embers.append(
            f'<circle cx="{x0:.0f}" cy="{y0:.0f}" r="{rnd.uniform(0.9, 2):.1f}" fill="{rnd.choice((HOT, "#FF8A3D", "#FFB199"))}">'
            f'<animateMotion path="M0 0 C{sway:.0f} {-rise / 3:.0f} {-sway:.0f} {-rise * 2 / 3:.0f} {sway / 2:.0f} {-rise:.0f}" '
            f'dur="{dur:.1f}s" begin="-{rnd.uniform(0, dur):.1f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;.55;.35;0" keyTimes="0;.15;.7;1" dur="{dur:.1f}s" begin="-{rnd.uniform(0, dur):.1f}s" repeatCount="indefinite"/></circle>'
        )
    defs = (
        f'<radialGradient id="rayLight" gradientUnits="userSpaceOnUse" cx="{cx}" cy="{cy}" r="{R}">'
        f'<stop offset="0" stop-color="{HOT}" stop-opacity=".55"/><stop offset=".35" stop-color="{HOT}" stop-opacity=".14"/>'
        f'<stop offset="1" stop-color="{HOT}" stop-opacity="0"/></radialGradient>'
    )
    behind = ""
    front = f'<g clip-path="url(#cardClip)">{"".join(embers)}</g>'
    return defs, behind, front


def code_rain(x0, x1, top, height, E, build0, T):
    """Columns of 0/1 falling where the cube was: the cube dissolves into code and is rebuilt from it."""
    rnd = random.Random(31)
    cols, step = [], 30
    for i in range(int((x1 - x0) / step)):
        x = x0 + i * step + rnd.uniform(-3, 3)
        n = rnd.randint(9, 16)
        digits = "".join(
            f'<tspan x="{x:.0f}" dy="{20 if j else 0}">{rnd.choice("01")}</tspan>' for j in range(n)
        )
        dur = rnd.uniform(2.2, 4.2)
        lag = rnd.uniform(0, dur)
        span = n * 20
        cols.append(
            f'<text class="m" font-size="15" font-weight="600" fill="url(#rainFade)" y="{top - span}">'
            f'<animateTransform attributeName="transform" type="translate" values="0 0;0 {height + span:.0f}" '
            f'dur="{dur:.1f}s" begin="-{lag:.1f}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.2;.75;1" dur="{dur:.1f}s" begin="-{lag:.1f}s" repeatCount="indefinite"/>'
            f"{digits}</text>"
        )
    gate = (
        f'<animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" '
        f'keyTimes="0;{(E + 0.25) / T:.4f};{(E + 1.1) / T:.4f};{(build0 + 1.5) / T:.4f};{(build0 + 3.5) / T:.4f};1" values="0;0;1;1;0;0"/>'
    )
    defs = (
        '<linearGradient id="rainFade" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{STEEL_RIM}" stop-opacity="0"/><stop offset=".6" stop-color="{STEEL_RIM}" stop-opacity=".45"/>'
        f'<stop offset=".9" stop-color="#FFC2C2"/><stop offset="1" stop-color="{HOT}"/></linearGradient>'
    )
    return defs, f'<g clip-path="url(#cardClip)" opacity="0">{gate}{"".join(cols)}</g>'


BEAM_EDGES = [
    ((0, 1, 1), (1, 1, 1), "x"), ((1, 0, 1), (1, 1, 1), "y"), ((1, 1, 1), (1, 1, 0), "z"),
    ((0, 0, 1), (1, 0, 1), "x"), ((0, 0, 1), (0, 1, 1), "y"),
    ((0, 1, 1), (0, 1, 0), "z"), ((1, 0, 1), (1, 0, 0), "z"), ((0, 1, 0), (1, 1, 0), "x"), ((1, 0, 0), (1, 1, 0), "y"),
]


def voxel_drop(cx, cy, u, H, T=16.0, n=5, material="metal"):
    """Endless build loop that breaks out of the card.

    Steel voxels fall in from above the canvas, crossing the card's top edge, and stack
    into the avatar's cube frame; the red core lands last and ignites. Then the whole
    thing collapses through the card's bottom edge. The cycle starts fully built, so a
    frozen first frame still shows the finished cube.
    """
    k = 0.866 * u
    P = lambda x, y, z: ((x - y) * k, (x + y) * 0.5 * u - z * u)
    off = (n / 2, n / 2, n / 2)
    face = lambda ps: pts([P(*p) for p in ps])
    rim = lambda a, b, w=1.6, o=1: (
        f'<path d="M{P(*a)[0]:.1f} {P(*a)[1]:.1f} L{P(*b)[0]:.1f} {P(*b)[1]:.1f}" stroke="currentColor" '
        f'stroke-width="{w}" stroke-opacity="{o}" stroke-linecap="round"/>'
    )
    cube = lambda top, left, right: (
        f'<polygon points="{face([(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)])}" fill="{left}"/>'
        f'<polygon points="{face([(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)])}" fill="{right}"/>'
        f'<polygon points="{face([(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)])}" fill="{top}"/>'
    )
    # black metal: near-black faces, light only on the edges (currentColor, so each block can glow hot)
    rims = (
        rim((0, 0, 1), (1, 0, 1), 1.2, 0.55) + rim((0, 0, 1), (0, 1, 1), 1.2, 0.55)
        + rim((0, 1, 1), (1, 1, 1)) + rim((1, 0, 1), (1, 1, 1)) + rim((1, 1, 1), (1, 1, 0), 1.4, 0.7)
    )
    srnd = random.Random(41)
    streaks = []
    for y in range(23):
        if srnd.random() < 0.85:
            bx = srnd.uniform(-20, 40)
            streaks.append((y, round(bx), round(srnd.uniform(30, 110)), srnd.choice((0.6, 1, 1)),
                            srnd.choice(("#FFFFFF", "#FFFFFF", "#000000")), srnd.uniform(0.015, 0.05)))
    defs = (
        f'<linearGradient id="vxTop" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#26282D"/><stop offset="1" stop-color="#0E0F11"/></linearGradient>'
        f'<linearGradient id="vxRight" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#121316"/><stop offset="1" stop-color="#040405"/></linearGradient>'
        f'<linearGradient id="trail" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{STEEL_RIM}" stop-opacity="0"/><stop offset="1" stop-color="{STEEL_RIM}" stop-opacity=".22"/></linearGradient>'
        f'<linearGradient id="trailRed" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{HOT}" stop-opacity="0"/><stop offset="1" stop-color="{HOT}" stop-opacity=".55"/></linearGradient>'
        + (
            # brushed steel, read off the avatar: near-black bars, silver only in the sheen and the
            # bevels, fine streaks along each face. Each block draws edges only along its own beam,
            # so a run of blocks reads as one continuous bar instead of a grid of tiles.
            f'<linearGradient id="bsTop" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#1D1F23"/><stop offset="1" stop-color="#0B0C0E"/></linearGradient>'
            f'<linearGradient id="bsLeft" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#16171A"/><stop offset=".55" stop-color="#0A0A0C"/>'
            f'<stop offset="1" stop-color="#040405"/></linearGradient>'
            f'<linearGradient id="bsRight" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#08080A"/><stop offset="1" stop-color="#010101"/></linearGradient>'
            + "".join(
                f'<pattern id="{pid}" width="90" height="23" patternUnits="userSpaceOnUse" patternTransform="rotate({rot})">'
                + "".join(
                    f'<rect x="{bx}" y="{y}" width="{bw}" height="{h}" fill="{fill}" fill-opacity="{op:.2f}"/>'
                    for y, bx, bw, h, fill, op in streaks
                )
                + "</pattern>"
                for pid, rot in (("brushA", 30), ("brushB", -30))
            )
            + "".join(
                f'<g id="vx{axis}">{cube("url(#bsTop)", "url(#bsLeft)", "url(#bsRight)")}'
                f'<polygon points="{face([(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)])}" fill="url(#brushA)"/>'
                f'<polygon points="{face([(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)])}" fill="url(#brushA)"/>'
                f'<polygon points="{face([(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)])}" fill="url(#brushB)" opacity=".4"/>'
                + "".join(rim(a, b, 1.2, 0.42) for a, b, ax in BEAM_EDGES if axis == "c" or ax == axis)
                + "".join(
                    f'<path d="M{P(*a)[0]:.1f} {P(*a)[1]:.1f} L{P(*b)[0]:.1f} {P(*b)[1]:.1f}" stroke="#fff" stroke-opacity=".18" stroke-width=".8"/>'
                    for a, b, ax in BEAM_EDGES[:5] if axis == "c" or ax == axis
                )
                + "</g>"
                for axis in "xyzc"
            )
            if material == "brushed"
            else f'<g id="vx">{cube("url(#vxTop)", "#08090A", "url(#vxRight)")}{rims}</g>'
        )
        + f'<g id="vc">{cube(HOT, RED, "#8E0A11")}'
        f'<g color="#FFC9C9">{rims}</g></g>'
    )
    edge = lambda c: c in (0, n - 1)
    blocks = [
        (x, y, z) for x in range(n) for y in range(n) for z in range(n) if edge(x) + edge(y) + edge(z) >= 2
    ]
    blocks.sort(key=lambda b: (b[0] + b[1] + b[2], b[2]))  # back-to-front, bottom-up: build order == paint order
    core = (n // 2, n // 2, n // 2)

    rnd = random.Random(11)
    collapse0, empty, build0, step, drop = 2.6, 4.6, 5.0, 0.18, 0.55
    ignite = build0 + len(blocks) * step + 0.25 + drop  # the core touches down
    order = blocks + [core]
    kts = lambda ts: ";".join(f"{t / T:.4f}" for t in ts)
    anim = lambda attr, ts, vs, extra="": (
        f'<animate attributeName="{attr}" dur="{T}s" repeatCount="indefinite" keyTimes="{kts(ts)}" values="{";".join(map(str, vs))}"{extra}/>'
    )
    out = []
    for i, b in enumerate(order):
        is_core = b == core
        px, py = P(b[0] - off[0], b[1] - off[1], b[2] - off[2])
        sx, sy = cx + px, cy + py
        above = -(sy + 3 * u)
        # blast: straight out from the core, slightly upward, far past the card
        bx0, by0 = P(b[0] + 0.5 - off[0], b[1] + 0.5 - off[1], b[2] + 0.5 - off[2])
        ang = math.atan2(by0 - 0.25 * u, bx0) + math.radians(rnd.uniform(-14, 14))
        reach = rnd.uniform(140, 250)
        ex, ey = (0, 0) if is_core else (math.cos(ang) * reach, math.sin(ang) * reach)
        c0 = collapse0 + math.dist(b, core) * 0.012
        c1 = c0 + rnd.uniform(0.75, 1.05)
        r0 = build0 + i * step + (0.25 if is_core else 0)
        r1 = r0 + drop
        times = [0, c0, c1, r0 - 0.01, r0, r1, r1 + 0.09, r1 + 0.18, T]
        vals = ["0 0", "0 0", f"{ex:.0f} {ey:.0f}", f"{ex:.0f} {ey:.0f}", f"0 {above:.0f}", "0 0", "0 -7", "0 0", "0 0"]
        splines = [".5 0 .5 1", ".05 .7 .3 1", "0 0 1 1", "0 0 1 1", ".55 0 1 .6", "0 0 .4 1", ".6 0 1 1", "0 0 1 1"]
        move = (
            f'<animateTransform attributeName="transform" type="translate" dur="{T}s" repeatCount="indefinite" '
            f'calcMode="spline" keyTimes="{kts(times)}" values="{";".join(vals)}" keySplines="{";".join(splines)}"/>'
        )

        # a motion streak behind the block, only while it is falling
        streak = anim("opacity", [0, r0 - 0.01, r0 + 0.06, r1 - 0.05, r1, T], [0, 0, 1, 1, 0, 0])
        trail = (
            f'<rect x="{sx - k * 0.8:.1f}" y="{sy - u - 170:.1f}" width="{k * 1.6:.1f}" height="170" '
            f'fill="url(#{"trailRed" if is_core else "trail"})" opacity="0">{streak}</rect>'
        )

        if is_core:
            # unstable just before the collapse, then lit again when it lands
            E = collapse0
            fl = [0, E - 0.7, E - 0.62, E - 0.55, E - 0.45, E - 0.36, E - 0.26, E - 0.18, E - 0.1, E, E + 0.06, r0 - 0.01, r0, T]
            look = anim("opacity", fl, [1, 1, 0.25, 1, 0.1, 1, 0.35, 1, 0.15, 1, 0, 0, 1, 1])
        else:
            # forged hot on landing, cooled, then lit by the ignition wave rolling out from the core
            dist = math.dist(b, core)
            w = max(ignite + 0.08 + dist * 0.13, r1 + 0.95)
            look = anim(
                "color",
                [0, r0 - 0.01, r0, r1, r1 + 0.9, w, w + 0.07, w + 0.6, T],
                [STEEL_RIM, STEEL_RIM, HOT, "#FF6A3D", STEEL_RIM, STEEL_RIM, HOT, STEEL_RIM, STEEL_RIM],
            )
        if is_core:
            sym = "vc"
        elif material == "brushed":
            free = [a for a, c in zip("xyz", b) if c not in (0, n - 1)]
            sym = "vx" + (free[0] if free else "c")
        else:
            sym = "vx"
        block = (
            f'<use href="#{sym}" x="{sx:.1f}" y="{sy:.1f}" color="{STEEL_RIM}"'
            + (' filter="url(#glow)"' if is_core else "") + f">{look}</use>"
        )

        # sparks thrown out where it touches down
        spark = sparks(sx, sy + 0.5 * u, r1, T, rnd, count=4 if is_core else 2)
        fade = "" if is_core else anim("opacity", [0, c0 + 0.3, c1, r0 - 0.02, r0 - 0.01, T], [1, 1, 0, 0, 1, 1])
        out.append(f"<g>{move}{fade}{trail}{block}</g>{spark}")
    land = ignite / T
    gone = (collapse0 + 0.25) / T
    light = (
        f'<circle cx="{cx}" cy="{cy}" r="{u * 6.5:.0f}" fill="url(#redLight)">'
        f'<animate attributeName="opacity" values=".8;.8;0;0;1;.8" keyTimes="0;{collapse0 / T:.4f};{gone:.4f};{land:.4f};{land + 0.02:.4f};1" '
        f'dur="{T}s" repeatCount="indefinite"/></circle>'
    )
    ring = (
        f'<ellipse cx="{cx}" cy="{cy}" rx="0" ry="0" fill="none" stroke="{HOT}" stroke-width="2" opacity="0">'
        f'<animate attributeName="rx" values="0;0;{u * 6.5:.0f};{u * 6.5:.0f}" keyTimes="0;{land:.4f};{land + 0.06:.4f};1" dur="{T}s" repeatCount="indefinite"/>'
        f'<animate attributeName="ry" values="0;0;{u * 4.5:.0f};{u * 4.5:.0f}" keyTimes="0;{land:.4f};{land + 0.06:.4f};1" dur="{T}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0;0;.9;0;0" keyTimes="0;{land:.4f};{land + 0.005:.4f};{land + 0.06:.4f};1" dur="{T}s" repeatCount="indefinite"/></ellipse>'
    )
    E = collapse0
    blast = (
        f'<circle cx="{cx}" cy="{cy}" r="0" fill="url(#blastLight)" opacity="0">'
        f'<animate attributeName="r" dur="{T}s" repeatCount="indefinite" keyTimes="0;{E / T:.4f};{(E + 0.5) / T:.4f};1" values="0;0;{u * 4.5:.0f};{u * 4.5:.0f}" calcMode="spline" keySplines="0 0 1 1;.1 .8 .3 1;0 0 1 1"/>'
        f'<animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" keyTimes="0;{(E - 0.01) / T:.4f};{E / T:.4f};{(E + 0.7) / T:.4f};1" values="0;0;1;0;0"/></circle>'
        + "".join(
            f'<ellipse cx="{cx}" cy="{cy}" rx="0" ry="0" fill="none" stroke="{c}" stroke-width="{w}" opacity="0">'
            f'<animate attributeName="rx" dur="{T}s" repeatCount="indefinite" keyTimes="0;{(E + d) / T:.4f};{(E + d + 0.8) / T:.4f};1" values="0;0;{u * 6.5:.0f};{u * 6.5:.0f}" calcMode="spline" keySplines="0 0 1 1;.1 .7 .3 1;0 0 1 1"/>'
            f'<animate attributeName="ry" dur="{T}s" repeatCount="indefinite" keyTimes="0;{(E + d) / T:.4f};{(E + d + 0.8) / T:.4f};1" values="0;0;{u * 3.75:.0f};{u * 3.75:.0f}" calcMode="spline" keySplines="0 0 1 1;.1 .7 .3 1;0 0 1 1"/>'
            f'<animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" keyTimes="0;{(E + d - 0.01) / T:.4f};{(E + d) / T:.4f};{(E + d + 0.8) / T:.4f};1" values="0;0;1;0;0"/></ellipse>'
            for c, w, d in ((HOT, 3, 0), ("#FFE3D6", 1.5, 0.08))
        )
    )
    shake = (
        f'<animateTransform attributeName="transform" type="translate" dur="{T}s" repeatCount="indefinite" '
        f'keyTimes="0;{land:.4f};{land + 0.004:.4f};{land + 0.008:.4f};{land + 0.012:.4f};{land + 0.018:.4f};1" '
        f'values="0 0;0 0;0 5;-4 -3;3 2;0 0;0 0"/>'
    )
    defs += (
        f'<radialGradient id="blastLight"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".18" stop-color="#FFD9CF"/>'
        f'<stop offset=".45" stop-color="{HOT}" stop-opacity=".55"/><stop offset="1" stop-color="{HOT}" stop-opacity="0"/></radialGradient>'
    )
    a_defs, a_behind, a_front = aura(cx, cy, u, ignite, E, T)
    r_defs, rain = code_rain(cx - 7 * u, cx + 7 * u, cy - 200, 400, E, build0, T)
    defs += a_defs + r_defs
    return (
        defs,
        light + a_behind + rain + ring
        + '<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -6;0 0" dur="6s" repeatCount="indefinite" calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1"/>'
        + f"<g>{shake}" + "".join(out) + "</g></g>" + blast,
        a_front + satellites(cx, cy, land * T, collapse0, T),
    )


# the layers a whole product needs; they dock around the cube once its core ignites
SATELLITES = [("API", -250, -110), ("WEB", -265, 80), ("iOS", 235, -140), ("AI", 250, 40), ("DB", 228, 132), ("CI", -232, 136)]


def satellites(cx, cy, land, leave, T, u=30):
    """Small red cubes labelled with a product layer; they dock once the core burns."""
    k = 0.866 * u
    P = lambda x, y, z: ((x - y) * k, (x + y) * 0.5 * u - z * u)
    face = lambda ps: pts([(P(*p)[0], P(*p)[1] + u) for p in ps])  # centred on the cube's middle
    rim = lambda a, b: (
        f'<path d="M{P(*a)[0]:.1f} {P(*a)[1] + u:.1f} L{P(*b)[0]:.1f} {P(*b)[1] + u:.1f}" stroke="#FFB3B3" stroke-width="1.3" stroke-opacity=".8"/>'
    )
    ox, oy = P(0, 1, 1)
    srnd = random.Random(5)
    out = []
    for i, (label, dx, dy) in enumerate(SATELLITES):
        n = math.hypot(dx, dy)
        ux, uy = dx / n, dy / n
        off = f"{ux * 700:.0f} {uy * 700:.0f}"
        l0, l1 = leave + 0.02, leave + 0.9
        a1 = land + 0.55 + i * 0.12  # docks as the ignition wave reaches the cube's edge
        a0 = a1 - 0.75
        times = [0, l0, l1, a0, a1, a1 + 0.16, T]
        vals = ["0 0", "0 0", off, off, f"{-ux * 12:.0f} {-uy * 12:.0f}", "0 0", "0 0"]
        splines = ["0 0 1 1", ".05 .7 .3 1", "0 0 1 1", ".1 .7 .3 1", ".4 0 .6 1", "0 0 1 1"]
        cube = (
            f'<circle cx="0" cy="0" r="{u * 1.35:.0f}" fill="url(#redLight)" class="breathe" style="animation-delay:-{i * 0.6:.1f}s"/>'
            f'<g filter="url(#glow)">'
            f'<polygon points="{face([(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)])}" fill="{RED}"/>'
            f'<polygon points="{face([(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)])}" fill="#7A0810"/>'
            f'<polygon points="{face([(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)])}" fill="{HOT}"/></g>'
            + rim((0, 1, 1), (1, 1, 1)) + rim((1, 0, 1), (1, 1, 1)) + rim((1, 1, 1), (1, 1, 0))
            # the label sits on the front-left face, skewed into its plane
            + f'<text transform="matrix(0.866 0.5 0 1 {ox:.1f} {oy + u:.1f})" x="{u / 2}" y="{u / 2 + 4.3}" '
            f'text-anchor="middle" class="m" font-size="12.5" font-weight="800" fill="#FFF1F1" letter-spacing=".5">{label}</text>'
        )
        bob = (
            f'<animateTransform attributeName="transform" type="translate" values="0 0;0 -7;0 0" '
            f'dur="{3.2 + i * 0.35:.2f}s" repeatCount="indefinite" calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1"/>'
        )
        beam = (
            f'<path d="M{cx + dx} {cy + dy} L{cx} {cy}" stroke="{HOT}" stroke-width="1" pathLength="1" '
            f'stroke-dasharray="1 1" stroke-dashoffset="1" opacity="0" filter="url(#glow)">'
            f'<animate attributeName="stroke-dashoffset" dur="{T}s" repeatCount="indefinite" '
            f'keyTimes="0;{a1 / T:.4f};{(a1 + 0.22) / T:.4f};1" values="1;1;0;0"/>'
            f'<animate attributeName="opacity" dur="{T}s" repeatCount="indefinite" '
            f'keyTimes="0;{(a1 - 0.01) / T:.4f};{a1 / T:.4f};{(a1 + 0.35) / T:.4f};{(a1 + 0.9) / T:.4f};1" values="0;0;.9;.9;0;0"/></path>'
        )
        out.insert(0, beam)
        out.append(sparks(cx + dx, cy + dy, a1, T, srnd, count=3, spread=0.7))
        out.append(
            f'<g transform="translate({cx + dx} {cy + dy})"><g>'
            f'<animateTransform attributeName="transform" type="translate" dur="{T}s" repeatCount="indefinite" calcMode="spline" '
            f'keyTimes="{";".join(f"{t / T:.4f}" for t in times)}" values="{";".join(vals)}" keySplines="{";".join(splines)}"/>'
            f"<g>{bob}{cube}</g></g></g>"
        )
    # docked inside the card: they enter through its edges, never past them
    return '<g clip-path="url(#cardClip)">' + "".join(out) + "</g>"


def hero(material="brushed"):
    # the card sits inside a taller transparent canvas so the build can break out of it
    W, H, top, ch = 1200, 560, 80, 400
    vx_defs, vx, sats = voxel_drop(905, top + 200, 45, H, material=material)
    name = lambda y, s: text(60, top + y, s, 80, TEXT, "s", 800, ls=-3)
    body = f"""
<defs>
  {vx_defs}
  <linearGradient id="fall" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".05" stop-color="#fff"/>
    <stop offset=".94" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <mask id="fade"><rect width="{W}" height="{H}" fill="url(#fall)"/></mask>
  <clipPath id="cardClip"><rect x="2" y="{top + 2}" width="{W - 4}" height="{ch - 4}" rx="19"/></clipPath>
</defs>
<g>
<animateTransform attributeName="transform" type="translate" dur="16s" repeatCount="indefinite"
  keyTimes="0;.1625;.165;.168;.171;.175;.18;1" values="0 0;0 0;-3 2;3 -2;-2 1;1 0;0 0;0 0"/>
<rect x="1" y="{top + 1}" width="{W - 2}" height="{ch - 2}" rx="20" fill="{BG}" stroke="url(#edge)" stroke-width="1.5"/>
<g>
  {name(176, "Oleksandr")}
  {name(258, "Riasnyi")}
</g>
<g class="full">
  <circle cx="69" cy="{top + 76}" r="4" fill="{HOT}" filter="url(#glow)" class="breathe"/>
  {text(84, top + 81, "OPEN TO FULL-STACK &amp; BACKEND ROLES", 12.5, MUTED, "m", 600, ls=2.4)}
  {text(64, top + 310, "Full-stack engineer &amp; product builder.", 23, BODY)}
  {text(64, top + 344, "DJANGO · REACT · REACT NATIVE · SWIFT", 12.5, DIM, "m", 600, ls=1.8)}
</g>
<g class="compact">
  <circle cx="72" cy="{top + 70}" r="9" fill="{HOT}" filter="url(#glow)" class="breathe"/>
  {text(64, top + 324, "Full-stack engineer", 44, BODY)}
  {text(64, top + 372, "&amp; product builder.", 44, BODY)}
</g>
<g mask="url(#fade)">{vx}</g>
{sats}
</g>
"""
    return svg(W, H, "Oleksandr Riasnyi — full-stack engineer and product builder", body, narrow=560)


# ---------------------------------------------------------------- section label


def label(title):
    W, H = 1200, 52
    end = 22 + len(title) * (13 * 0.6 + 4) + 18
    end2 = 26 + len(title) * (36 * 0.6 + 6) + 30
    body = f"""
<defs><linearGradient id="hair" x1="0" x2="1"><stop offset="0" stop-color="{MUTED}" stop-opacity=".45"/><stop offset="1" stop-color="{MUTED}" stop-opacity="0"/></linearGradient></defs>
<circle cx="5" cy="27" r="3.5" fill="{HOT}" filter="url(#glow)"/>
<g class="full">{text(22, 32, title, 13, MUTED, "m", 700, ls=4)}
<rect x="{end:.0f}" y="26.5" width="{W - end:.0f}" height="1.5" fill="url(#hair)"/></g>
<g class="compact">{text(26, 41, title, 36, MUTED, "m", 700, ls=6)}
<rect x="{end2:.0f}" y="26" width="{W - end2:.0f}" height="3" fill="url(#hair)"/></g>
"""
    return svg(W, H, title.title(), body, narrow=560)


# ---------------------------------------------------------------- glyphs (static steel, one red light)


def glyph_radar(cx, cy, r):
    axes = hexpts(cx, cy, r)
    grid = "".join(
        f'<polygon points="{pts(hexpts(cx, cy, r * f))}" fill="none" stroke="#202226" stroke-width="1.2"/>' for f in (0.5, 1)
    )
    spokes = "".join(f'<path d="M{cx} {cy} L{x:.1f} {y:.1f}" stroke="#202226" stroke-width="1.2"/>' for x, y in axes)
    fs = [0.86, 0.62, 0.92, 0.55, 0.78, 0.68]
    shape = [(cx + (x - cx) * f, cy + (y - cy) * f) for (x, y), f in zip(axes, fs)]
    hx, hy = shape[2]
    return (
        grid + spokes
        + f'<polygon points="{pts(shape)}" fill="#A9AEB5" fill-opacity=".07" stroke="#A9AEB5" stroke-width="1.5" stroke-linejoin="round"/>'
        + "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="#A9AEB5"/>' for x, y in shape)
        + f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="4.5" fill="{HOT}" filter="url(#glow)" class="breathe"/>'
    )


def glyph_qr(x0, y0, cell=10, n=11):
    rnd = random.Random(7)
    out = []
    for i in range(n):
        for j in range(n):
            if (i < 4 and j < 4) or (i < 4 and j > n - 5) or (i > n - 5 and j < 4):
                continue
            if rnd.random() < 0.45:
                out.append(f'<rect x="{x0 + i * cell + 1.5}" y="{y0 + j * cell + 1.5}" width="{cell - 3}" height="{cell - 3}" fill="#34373C"/>')
    size = n * cell
    for fx, fy in ((x0, y0), (x0 + size - cell * 3, y0), (x0, y0 + size - cell * 3)):
        out.append(
            f'<rect x="{fx + 1.5}" y="{fy + 1.5}" width="{cell * 3 - 3}" height="{cell * 3 - 3}" fill="none" stroke="#A9AEB5" stroke-width="2.5"/>'
            f'<rect x="{fx + cell}" y="{fy + cell}" width="{cell}" height="{cell}" fill="#A9AEB5"/>'
        )
    out.append(
        f'<g><rect x="{x0 - 10}" y="{y0}" width="{size + 20}" height="2" fill="{HOT}" filter="url(#glow)"/>'
        f'<animateTransform attributeName="transform" type="translate" values="0 0;0 {size};0 0" dur="6s" repeatCount="indefinite" '
        f'calcMode="spline" keyTimes="0;.5;1" keySplines=".45 0 .55 1;.45 0 .55 1"/></g>'
    )
    return "".join(out)


def glyph_funnel(x0, y0):
    out = []
    for i, (n, word) in enumerate([(400, "records"), (349, "unique"), (97, "qualified")]):
        w, y = 130 * n / 400, y0 + i * 44
        fill = f'{HOT}" filter="url(#glow)' if i == 2 else "#A9AEB5" if i == 0 else "#5E636B"
        out.append(
            f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="10" rx="2" fill="{fill}"/>'
            + text(x0, y + 30, f'<tspan fill="{STEEL}" font-weight="700">{n}</tspan> {word}', 12.5, DIM, "m")
        )
    return "".join(out)


def glyph_graph(cx, cy):
    nodes = [(-62, -46), (6, -64), (66, -30), (-70, 22), (0, 0), (62, 44), (-18, 62)]
    edges = [(4, 0), (4, 1), (4, 2), (4, 3), (4, 5), (4, 6), (0, 1), (2, 5), (3, 6), (1, 2)]
    p = lambda i: (cx + nodes[i][0], cy + nodes[i][1])
    out = [f'<path d="M{p(a)[0]} {p(a)[1]} L{p(b)[0]} {p(b)[1]}" stroke="#25272B" stroke-width="1.5"/>' for a, b in edges]
    for i in range(len(nodes)):
        x, y = p(i)
        if i == 4:
            out.append(f'<rect x="{x - 9}" y="{y - 9}" width="18" height="18" rx="3" fill="{HOT}" filter="url(#glow)" class="breathe"/>')
        else:
            out.append(f'<rect x="{x - 11}" y="{y - 8}" width="22" height="16" rx="3" fill="{CARD}" stroke="#8E949C" stroke-width="1.5"/>')
    return "".join(out)


# ---------------------------------------------------------------- cards


def fit(name, size, width, k=0.56):
    """Largest font size (up to `size`) at which `name` fits in `width` user units."""
    return round(min(size, width / (len(name) * k)), 1)


def product_card(p):
    W, H = 600, 300
    desc = "".join(text(36, 146 + i * 26, escape(line), 18, BODY) for i, line in enumerate(p["desc"]))
    body = f"""
{frame(W, H)}
<g class="full">
  {text(36, 52, p["label"], 12, DIM, "m", 700, ls=2.4, extra='xml:space="preserve"')}
  {text(34, 104, p["name"], 38, TEXT, "s", 800, ls=-1.2)}
  {desc}
  {text(36, 244, escape(p["role"]), 13.5, "#B5BAC1", "m", 500)}
  {text(36, 268, escape("  ·  ".join(p["stack"])), 12.5, DIM, "m", 500, extra='xml:space="preserve"')}
  {p["glyph"]}
</g>
<g class="compact">
  <circle cx="44" cy="62" r="7" fill="{HOT}" filter="url(#glow)"/>
  {text(66, 72, p["tag"], 28, DIM, "m", 700, ls=2)}
  {text(34, 172, p["name"], fit(p["name"], 78, 530), TEXT, "s", 800, ls=-2)}
  {text(36, 236, escape(p["short"]), 36, BODY)}
</g>
"""
    return svg(W, H, f'{p["name"]} — {" ".join(p["desc"])}', body, narrow=300)


# small looping glyphs for the open-source tiles: steel line-work, one red accent each
SP = ".45 0 .55 1"


def g_notch(cx, cy):
    """VoidBar: the notch grows into a live island and back."""
    x0, y0, w, h = cx - 62, cy - 40, 124, 78
    kt, ks = "0;.18;.6;.78;1", f"{SP};0 0 1 1;{SP};0 0 1 1"
    pill = lambda attr, vals: f'<animate attributeName="{attr}" values="{vals}" keyTimes="{kt}" dur="5s" repeatCount="indefinite" calcMode="spline" keySplines="{ks}"/>'
    bars = "".join(
        f'<rect x="{cx - 26 + i * 8}" y="{y0 + 13}" width="4" height="12" rx="2" fill="{HOT if i == 3 else STEEL_RIM}" opacity="0">'
        f'<animate attributeName="opacity" values="0;0;1;1;0;0" keyTimes="0;.16;.22;.56;.6;1" dur="5s" repeatCount="indefinite"/>'
        f'<animate attributeName="height" values="5;13;8;12;5" dur="{0.6 + i * 0.08:.2f}s" repeatCount="indefinite"/></rect>'
        for i in range(7)
    )
    return (
        f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" rx="7" fill="#0B0C0E" stroke="#2A2C31" stroke-width="1.5"/>'
        f'<rect x="{cx - 18}" y="{y0}" width="36" height="10" rx="5" fill="#000" stroke="#3A3D42">'
        + pill("width", "36;108;108;36;36") + pill("x", f"{cx - 18};{cx - 54};{cx - 54};{cx - 18};{cx - 18}")
        + pill("height", "10;38;38;10;10") + "</rect>" + bars
    )


def g_life(cx, cy):
    """EDEN//0: creatures wandering a small world."""
    rnd = random.Random(3)
    out = [f'<circle cx="{cx}" cy="{cy}" r="46" fill="none" stroke="#1F2125" stroke-width="1.5" stroke-dasharray="2 5"/>']
    for i in range(12):
        ps = [(cx + d * math.cos(a), cy + d * math.sin(a)) for a, d in ((rnd.uniform(0, 6.3), rnd.uniform(0, 38)) for _ in range(4))]
        path = "M" + " L".join(f"{x:.0f} {y:.0f}" for x, y in ps + ps[:1])
        col, r = (HOT, 3.5) if i < 2 else (STEEL_RIM, 2.6) if i < 8 else ("#4A4E55", 2.2)
        out.append(f'<circle cx="{ps[0][0]:.0f}" cy="{ps[0][1]:.0f}" r="{r}" fill="{col}"><animateMotion dur="{rnd.uniform(7, 12):.1f}s" repeatCount="indefinite" path="{path}" calcMode="paced"/></circle>'
                   .replace(f'cx="{ps[0][0]:.0f}" cy="{ps[0][1]:.0f}"', 'cx="0" cy="0"'))
    return "".join(out)


def g_flow(cx, cy):
    """TraceFlow: requests moving between web, API and database."""
    nodes = {"WEB": (cx - 48, cy - 26), "API": (cx + 44, cy - 6), "DB": (cx - 22, cy + 34)}
    out = []
    for k, (a, b) in enumerate((("WEB", "API"), ("API", "DB"), ("DB", "WEB"))):
        (x1, y1), (x2, y2) = nodes[a], nodes[b]
        d = f"M{x1} {y1} L{x2} {y2}"
        out.append(f'<path d="{d}" stroke="#2A2C31" stroke-width="1.5" stroke-dasharray="3 4"/>')
        out += [
            f'<circle r="3" fill="{HOT if k == 0 else STEEL_RIM}"><animateMotion dur="1.8s" begin="{k * 0.3 + j * 0.9:.1f}s" repeatCount="indefinite" path="{d}"/></circle>'
            for j in range(2)
        ]
    for name, (x, y) in nodes.items():
        out.append(
            f'<rect x="{x - 20}" y="{y - 11}" width="40" height="22" rx="5" fill="#0B0C0E" stroke="#4A4E55" stroke-width="1.5"/>'
            + text(x, y + 4, name, 10, STEEL, "m", 700, "middle", 1)
        )
    return "".join(out)


def g_counter(cx, cy):
    """zerotokens: tokens per run falling to zero."""
    out = []
    for i, (v, size, col) in enumerate((("12,480", 28, STEEL), ("3,912", 28, STEEL), ("0", 38, HOT))):
        ops = ("1;1;0;0;0;0", "0;0;1;1;0;0", "0;0;0;0;1;1")[i]
        out.append(
            f'<text x="{cx}" y="{cy + 8}" class="m" font-size="{size}" font-weight="800" fill="{col}" text-anchor="middle" opacity="{1 if i == 0 else 0}">{v}'
            f'<animate attributeName="opacity" values="{ops}" keyTimes="0;.28;.33;.6;.66;1" dur="6s" repeatCount="indefinite" calcMode="discrete"/></text>'
        )
    out.append(text(cx, cy + 32, "TOKENS / RUN", 10, DIM, "m", 700, "middle", 2))
    return "".join(out)


def g_commands(cx, cy):
    """django-saas-toolkit: its three skills, run in turn."""
    out = []
    for i, c in enumerate(("/saas-review", "/project-memory", "/commit-prep")):
        y = cy - 22 + i * 24
        vals = ";".join("1" if j == i else "0" for j in range(3)) + (";1" if i == 0 else ";0")
        out.append(
            f'<rect x="{cx - 68}" y="{y - 15}" width="136" height="21" rx="5" fill="{RED}" fill-opacity=".14" opacity="{1 if i == 0 else 0}">'
            f'<animate attributeName="opacity" values="{vals}" keyTimes="0;.333;.666;1" dur="4.5s" repeatCount="indefinite" calcMode="discrete"/></rect>'
            + text(cx - 60, y, f'<tspan fill="{RED}">›</tspan> {c}', 12, STEEL, "m", 600)
        )
    return "".join(out)


def g_pool(cx, cy):
    """AI Pool Starter: one tool cycling through a pool of models."""
    ps = hexpts(cx, cy, 40)
    out = [f'<circle cx="{cx}" cy="{cy}" r="40" fill="none" stroke="#1F2125" stroke-width="1.5"/>']
    out += [f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#0B0C0E" stroke="#4A4E55" stroke-width="1.5"/>' for x, y in ps]
    out.append(
        f'<g><circle cx="{ps[0][0]:.1f}" cy="{ps[0][1]:.1f}" r="6" fill="{HOT}"/>'
        f'<circle cx="{ps[0][0]:.1f}" cy="{ps[0][1]:.1f}" r="11" fill="none" stroke="{HOT}" stroke-opacity=".45" stroke-width="1.5"/>'
        f'<animateTransform attributeName="transform" type="rotate" values="{";".join(f"{60 * i} {cx} {cy}" for i in range(6))}" '
        f'dur="6s" repeatCount="indefinite" calcMode="discrete"/></g>'
    )
    out.append(text(cx, cy + 4, "/models", 10.5, STEEL, "m", 700, "middle"))
    return "".join(out)


def oss_tile(p):
    W, H = 600, 140
    body = f"""
{frame(W, H, 14)}
<g class="full">
  {text(34, 56, p["name"], 27, TEXT, "s", 800, ls=-0.8)}
  {text(W - 22, 30, "↗", 14, DIM, "m", 700, "end")}
  {p["glyph"]}
  {text(36, 90, escape(p["desc"]), 16.5, BODY)}
  {text(36, 116, p["meta"], 12, DIM, "m", 600, ls=1.6, extra='xml:space="preserve"')}
</g>
<g class="compact">
  {text(34, 92, p["name"], fit(p["name"], 62, 470), TEXT, "s", 800, ls=-1.5)}
  {text(W - 30, 92, "↗", 44, HOT, "m", 700, "end")}
</g>
"""
    return svg(W, H, f'{p["name"]} — {p["desc"]}', body, narrow=300)


# ---------------------------------------------------------------- stack

ICONS = json.loads((Path(__file__).resolve().parent / "stack_icons.json").read_text())  # Simple Icons (CC0)
# the same six layers the hero's satellites carry; (icon slug or badge text, name, version)
STACK = [
    ("API", "backend", [
        ("python", "Python", ""), ("django", "Django", "5.2"), ("django", "DRF", ""), ("fastapi", "FastAPI", ""),
        ("celery", "Celery", "5.5"), ("@ARQ", "arq", ""), ("jsonwebtokens", "simplejwt", ""),
    ]),
    ("WEB", "frontend", [
        ("typescript", "TypeScript", ""), ("react", "React", "19"), ("vite", "Vite", ""), ("reactquery", "TanStack Query", ""),
        ("reactrouter", "React Router", ""), ("@RF", "React Flow", ""), ("@PX", "PixiJS", ""),
    ]),
    ("iOS", "mobile · native", [
        ("react", "React Native", "0.86"), ("expo", "Expo", "57"), ("expo", "Expo Router", ""), ("@ZS", "zustand", ""),
        ("swift", "Swift", "6"), ("apple", "SwiftUI · AppKit", ""),
    ]),
    ("AI", "models", [
        ("@GQ", "Groq", "gpt-oss-120b"), ("ollama", "Ollama", "qwen2.5"), ("openai", "OpenAI-compatible", ""),
        ("claude", "Claude Code", ""), ("modelcontextprotocol", "MCP · skills", ""),
    ]),
    ("DB", "data", [
        ("postgresql", "PostgreSQL", "16"), ("@VEC", "pgvector", "HNSW"), ("redis", "Redis", "7"), ("redis", "Redis Streams", ""),
        ("sqlite", "SQLite", ""), ("cloudflare", "Cloudflare D1", ""),
    ]),
    ("CI", "ship", [
        ("docker", "Docker Compose", ""), ("@AWS", "EC2", ""), ("@AWS", "S3 · CloudFront", ""), ("@AWS", "CloudWatch", ""),
        ("caddy", "Caddy", ""), ("githubactions", "Actions", ""), ("pytest", "pytest", ""),
    ]),
]
PRACTICE = ["Contract-first OpenAPI", "ADRs", "Evals · LLM-as-judge", "One CI gate per PR", "Semantic cache", "Monorepo"]


def text_width(s, size, mono=False):
    """Rough rendered width of s at size px; good enough to centre content inside a chip."""
    if mono:
        return len(s) * size * 0.6
    em = 0.0
    for ch in s:
        if ch in "iljtfr.,·:;|!' ()":
            em += 0.29
        elif ch in "mwMW":
            em += 0.84
        elif ch.isupper():
            em += 0.66
        elif ch.isdigit():
            em += 0.56
        else:
            em += 0.53
    return em * size * 1.1  # system UI fonts run a little wider than the table


def stack_block():
    """An architecture map rather than a badge wall: one row per layer, real versions, then practice."""
    W, H, T = 1200, 522, 14.0
    used = {sl for _, _, items in STACK for sl, _, _ in items if not sl.startswith("@")}
    defs = "".join(f'<symbol id="i-{sl}" viewBox="0 0 24 24"><path d="{ICONS[sl]}"/></symbol>' for sl in sorted(used))
    u = 11
    k = 0.866 * u
    Pm = lambda x, y, z: ((x - y) * k, (x + y) * 0.5 * u - z * u)

    def mini_cube(cx, cy, scale=1.0, hollow=False):
        f = lambda ps: pts([(cx + Pm(*q)[0] * scale, cy + (Pm(*q)[1] + u) * scale) for q in ps])
        if hollow:
            return (
                f'<g fill="none" stroke="{HOT}" stroke-width="1.4"><polygon points="{f([(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)])}"/>'
                f'<polygon points="{f([(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)])}"/><polygon points="{f([(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)])}"/></g>'
            )
        return (
            f'<g filter="url(#glow)"><polygon points="{f([(0, 1, 0), (1, 1, 0), (1, 1, 1), (0, 1, 1)])}" fill="{RED}"/>'
            f'<polygon points="{f([(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)])}" fill="#7A0810"/>'
            f'<polygon points="{f([(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)])}" fill="{HOT}"/></g>'
        )

    def lit(n):
        """A red wave runs through the map, row by row, once a cycle."""
        t = 0.5 + n * 0.2
        kt = f"0;{t / T:.4f};{(t + 0.2) / T:.4f};{(t + 1.0) / T:.4f};1"
        return (
            f'<animate attributeName="fill" values="{STEEL_RIM};{STEEL_RIM};{HOT};{STEEL_RIM};{STEEL_RIM}" keyTimes="{kt}" dur="{T}s" repeatCount="indefinite"/>',
            f'<animate attributeName="stroke" values="#24262A;#24262A;{RED};#24262A;#24262A" keyTimes="{kt}" dur="{T}s" repeatCount="indefinite"/>',
        )

    def mark(sl, x, y, size, fill_anim):
        if sl.startswith("@"):  # no brand icon available: a lettered square in the same footprint
            label = sl[1:]
            fs = size * (0.42 if len(label) <= 2 else 0.33)
            return (
                f'<rect x="{x + 0.75:.1f}" y="{y + 0.75:.1f}" width="{size - 1.5:.1f}" height="{size - 1.5:.1f}" rx="{size * 0.22:.1f}" '
                f'fill="none" stroke="{STEEL_RIM}" stroke-width="{max(1.2, size * 0.07):.1f}">'
                + fill_anim.replace('attributeName="fill"', 'attributeName="stroke"') + "</rect>"
                f'<text x="{x + size / 2:.1f}" y="{y + size / 2 + fs * 0.36:.1f}" class="m" font-size="{fs:.1f}" font-weight="800" '
                f'text-anchor="middle" fill="{STEEL_RIM}">{fill_anim}{label}</text>'
            )
        return f'<use href="#i-{sl}" x="{x:.1f}" y="{y:.1f}" width="{size}" height="{size}" fill="{STEEL_RIM}">{fill_anim}</use>'

    left, x0, right, gap = 44, 212, W - 40, 8
    full, compact = [], []
    n = 0
    for row, (layer, role, items) in enumerate(STACK):
        y = 34 + row * 68
        full.append(
            mini_cube(left + 9, y + 6)
            + text(left + 30, y + 22, layer, 16, HOT, "m", 800, ls=1)
            + text(left + 30, y + 40, role.upper(), 10, DIM, "m", 700, ls=1.4)
        )
        if row:
            full.append(f'<rect x="{left}" y="{y - 12}" width="{right - left}" height="1" fill="#141518"/>')
        span = right - x0
        natural = [18 + 9 + text_width(nm, 13.5) + (9 + text_width(v, 11, True) if v else 0) + 28 for _, nm, v in items]
        extra = (span - sum(natural) - gap * (len(items) - 1)) / len(items)
        assert extra >= 0, f"{layer} row overflows"
        x = x0
        for (sl, name, ver), nat in zip(items, natural):
            fill_anim, stroke_anim = lit(n)
            w = nat + extra
            cx0 = x + (w - (nat - 28)) / 2  # centred content: icon, name, version
            tx = cx0 + 18 + 9
            full.append(
                f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="40" rx="10" fill="#0B0C0E" stroke="#24262A" stroke-width="1.3">{stroke_anim}</rect>'
                + mark(sl, cx0, y + 11, 18, fill_anim)
                + text(f"{tx:.1f}", y + 25, escape(name), 13.5, TEXT, "s", 500)
                + (text(f"{tx + text_width(name, 13.5) + 9:.1f}", y + 25, escape(ver), 11, DIM, "m", 600) if ver else "")
            )
            x += w + gap
            n += 1
        yc = 30 + row * 80
        compact.append(mini_cube(left + 14, yc + 14, 1.5) + text(left + 50, yc + 50, layer, 34, HOT, "m", 800, ls=1))
        # icons only on a phone, so each mark appears once per row
        for j, sl in enumerate(dict.fromkeys(sl for sl, _, _ in items)):
            xc = 200 + j * 118
            compact.append(
                f'<rect x="{xc}" y="{yc}" width="70" height="70" rx="16" fill="#0B0C0E" stroke="#24262A" stroke-width="2"/>'
                + mark(sl, xc + 16, yc + 16, 38, "")
            )
    # practice: how the work is done, not only what it is built with
    y = 34 + 6 * 68 + 6
    full.append(
        f'<rect x="{left}" y="{y - 18}" width="{right - left}" height="1" fill="#1E2024"/>'
        + mini_cube(left + 9, y + 6, hollow=True)
        + text(left + 30, y + 22, "HOW", 16, HOT, "m", 800, ls=1)
        + text(left + 30, y + 40, "PRACTICE", 10, DIM, "m", 700, ls=1.4)
    )
    natural = [12 + 6 + text_width(nm, 13) + 30 for nm in PRACTICE]
    extra = (right - x0 - sum(natural) - gap * (len(PRACTICE) - 1)) / len(PRACTICE)
    x = x0
    for name, nat in zip(PRACTICE, natural):
        w = nat + extra
        cx0 = x + (w - (nat - 30)) / 2
        full.append(
            f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="40" rx="20" fill="none" stroke="#3A2024" stroke-width="1.3"/>'
            f'<circle cx="{cx0 + 3:.1f}" cy="{y + 20}" r="3" fill="{HOT}"/>'
            + text(f"{cx0 + 15:.1f}", y + 25, escape(name), 13, BODY, "s", 500)
        )
        x += w + gap
    assert x <= right + gap + 1, "practice row overflows"
    body = (
        f"<defs>{defs}</defs>{frame(W, H, 18)}"
        f'<g class="full">{"".join(full)}</g><g class="compact">{"".join(compact)}</g>'
    )
    title = "Stack: " + "; ".join(f"{layer} — {', '.join((nm + ' ' + v).strip() for _, nm, v in items)}" for layer, _, items in STACK)
    title += ". Practice: " + ", ".join(PRACTICE)
    return svg(W, H, title, body, narrow=560)


# ---------------------------------------------------------------- skyline


def skyline(cal, stats):
    W, H = 1200, 410
    weeks = cal["weeks"]
    counts = sorted(d["contributionCount"] for w in weeks for d in w["contributionDays"] if d["contributionCount"])
    q = lambda f: counts[min(len(counts) - 1, int(len(counts) * f))] if counts else 1
    t1, t2, t3 = q(0.5), q(0.85), q(0.96)
    peak = counts[-1] if counts else 1
    palette = [  # top, front, right
        ("#0E0F11", "#0A0B0C", "#08090A"),
        ("#2A2C30", "#1C1E21", "#151618"),
        ("#5A5F66", "#3E4248", "#2F3236"),
        ("#B4B9C0", "#80868E", "#5F646B"),
        (HOT, "#B00C14", "#7E0910"),
    ]
    x0, y0 = 120, 176
    u, v = (18.3, 3.2), (-8.0, 6.5)
    uu, vv = (u[0] * 0.85, u[1] * 0.85), (v[0] * 0.82, v[1] * 0.82)
    P = lambda w, d: (x0 + w * u[0] + d * v[0], y0 + w * u[1] + d * v[1])
    add = lambda a, b: (a[0] + b[0], a[1] + b[1])
    up = lambda a, h: (a[0], a[1] - h)
    cells = sorted(
        ((day["weekday"], wi, day) for wi, w in enumerate(weeks) for day in w["contributionDays"]),
        key=lambda c: (c[0], c[1]),
    )
    bars = []
    for d, wi, day in cells:
        c = day["contributionCount"]
        lvl = 0 if not c else 1 if c <= t1 else 2 if c <= t2 else 3 if c <= t3 else 4
        h = 2 if not c else 5 + (c / peak) ** 0.6 * 100
        top, front, right = palette[lvl]
        a = P(wi, d)
        b, dd = add(a, uu), add(a, vv)
        cc = add(b, vv)
        lid = pts([up(a, h), up(b, h), up(cc, h), up(dd, h)])
        glow = ' filter="url(#glow)"' if lvl == 4 else ""
        faces = (
            f'<polygon points="{pts([dd, cc, up(cc, h), up(dd, h)])}" fill="{front}"/>'
            f'<polygon points="{pts([b, cc, up(cc, h), up(b, h)])}" fill="{right}"/>'
            f'<polygon points="{lid}" fill="{top}"{glow}/>'
        )
        bars.append(f'<g class="in" {delay(0.2 + wi * 0.025 + d * 0.01)}>{faces}</g>' if c else faces)
    months, seen = [], set()
    for wi, w in enumerate(weeks):
        first = w["contributionDays"][0]["date"]
        if first[:7] not in seen and wi > 0 and int(first[8:]) <= 7:
            seen.add(first[:7])
            x, y = P(wi, 7.6)
            name = dt.date.fromisoformat(first).strftime("%b").upper()
            months.append(text(f"{x:.1f}", f"{y + 14:.1f}", name, 11, "#3E4248", "m", 700, ls=1.5))
    best = stats["best"]
    best_day = dt.date.fromisoformat(best["date"]).strftime("%b %-d")
    body = f"""
{frame(W, H, 18)}
<g class="full">
  {text(34, 74, f'{cal["totalContributions"]:,}', 44, TEXT, "s", 800, ls=-1.5)}
  {text(36, 102, f'contributions in the last year  ·  {stats["longest"]}-day longest streak  ·  best day {best["contributionCount"]} on {best_day}', 15, DIM, "s", 400, extra='xml:space="preserve"')}
</g>
<g class="compact">
  {text(34, 98, f'{cal["totalContributions"]:,}', 84, TEXT, "s", 800, ls=-3)}
  {text(36, 146, f'contributions · {stats["longest"]}-day streak', 36, DIM)}
</g>
{"".join(bars)}
<g class="full">{"".join(months)}</g>
"""
    return svg(W, H, f'{cal["totalContributions"]} contributions in the last year, longest streak {stats["longest"]} days', body, narrow=560)


# ---------------------------------------------------------------- buttons


def button(label, icon):
    W, H = 260, 56
    body = f"""
{frame(W, H, 12)}
{icon}
{text(70, 34, label, 13.5, STEEL, "m", 700, ls=3)}
{text(W - 24, 35, "↗", 16, HOT, "m", 700, "end")}
"""
    return svg(W, H, label, body)


ICON_IN = (
    f'<rect x="26" y="15" width="26" height="26" rx="5" fill="none" stroke="{STEEL}" stroke-width="1.8"/>'
    + text(39, 34, "in", 14, STEEL, "s", 800, "middle")
)
ICON_MAIL = (
    f'<rect x="24" y="17" width="30" height="22" rx="4" fill="none" stroke="{STEEL}" stroke-width="1.8"/>'
    f'<path d="M25 19 L39 30 L53 19" fill="none" stroke="{STEEL}" stroke-width="1.8" stroke-linejoin="round"/>'
)


# ---------------------------------------------------------------- main


def main():
    data = fetch()
    cal = data["contributionsCollection"]["contributionCalendar"]
    stats = calendar_stats(cal["weeks"])
    vb = data["voidbar"]
    vb_release = (vb.get("latestRelease") or {}).get("tagName", "")
    pf = proof()
    commits = lambda key: f'{pf[key]} COMMITS' if pf.get(key) else ""

    products = [
        dict(
            slug="skillforge", name="SkillForge", label=f"AI PRODUCT  ·  PRIVATE  ·  {commits('skillforge')}",
            tag="PRIVATE", short="AI career copilot",
            desc=["AI career copilot. A CV goes in, a", "local LLM scores it on six dimensions", "and matches it to real vacancies."],
            role="architecture · Django API · AI pipeline",
            stack=["Django", "pgvector", "Celery", "Ollama", "React", "Expo"],
            glyph=glyph_radar(486, 140, 64),
        ),
        dict(
            slug="fitgym", name="FITGYM", label=f"MULTI-TENANT SAAS  ·  DEMO ↗  ·  {commits('fitgym')}",
            tag="DEMO ↗", short="CRM for fitness clubs",
            desc=["CRM for fitness clubs: a tenant per", "club, memberships, schedule,", "QR check-in and a member app."],
            role="co-founder · backend · admin · mobile",
            stack=["Django", "PostgreSQL", "React", "React Native", "Docker"],
            glyph=glyph_qr(430, 84),
        ),
        dict(
            slug="leadforge", name="LeadForge", label=f"LEAD RESEARCH  ·  PRIVATE  ·  {commits('leadforge')}",
            tag="PRIVATE", short="Lead research CRM",
            desc=["Evidence-first lead research for", "local businesses on open map data.", "No scraping, no paid API keys."],
            role="author · collector · scoring · CRM",
            stack=["Python", "TypeScript", "Overture Maps", "Cloudflare D1"],
            glyph=glyph_funnel(430, 82),
        ),
        dict(
            slug="cognitrace", name="CogniTrace", label=f"ANALYST BOARD  ·  PRIVATE  ·  {commits('cognitrace')}",
            tag="PRIVATE", short="Evidence graph board",
            desc=["Self-hosted analyst board: entities,", "evidence-backed claims and live", "runs on a graph canvas."],
            role="author · FastAPI · realtime · graph UI",
            stack=["FastAPI", "Redis Streams", "React Flow", "WebSocket"],
            glyph=glyph_graph(488, 142),
        ),
    ]
    oss = [
        dict(slug="voidbar", name="VoidBar", desc="Your MacBook notch, finally useful.",
             meta=f'SWIFT 6 · MACOS   ★ {vb["stargazerCount"]}   {vb_release}', glyph=g_notch(492, 72)),
        dict(slug="eden", name="EDEN//0", desc="Artificial life you can play in the browser.",
             meta="TYPESCRIPT · SPIKING NEURAL NETS", glyph=g_life(498, 72)),
        dict(slug="traceflow", name="TraceFlow", desc="Architecture and live traffic, inside VS Code.",
             meta="VS CODE · OPEN VSX" + (f'   {pf["traceflow_downloads"]} DOWNLOADS' if pf.get("traceflow_downloads") else ""),
             glyph=g_flow(500, 70)),
        dict(slug="zerotokens", name="zerotokens", desc="Turns repeated LLM work into zero-token CI.",
             meta="CLAUDE SKILL · PYTHON", glyph=g_counter(500, 66)),
        dict(slug="django-saas-toolkit", name="django-saas-toolkit", desc="Review, memory and commits for Django SaaS.",
             meta="CLAUDE PLUGIN", glyph=g_commands(500, 72)),
        dict(slug="ai-pool", name="AI Pool Starter", desc="One tool, the whole model pool.",
             meta="WORKSHOP · KAI 2026", glyph=g_pool(500, 70)),
    ]

    OUT.mkdir(exist_ok=True)
    files = {
        "hero.svg": hero(),
        "skyline.svg": skyline(cal, stats),
        "label-work.svg": label("SELECTED WORK"),
        "label-oss.svg": label("OPEN SOURCE"),
        "label-activity.svg": label("ACTIVITY"),
        "label-stack.svg": label("STACK"),
        "stack.svg": stack_block(),
        "btn-linkedin.svg": button("LINKEDIN", ICON_IN),
        "btn-email.svg": button("EMAIL", ICON_MAIL),
    }
    for p in products:
        files[f"card-{p['slug']}.svg"] = product_card(p)
    for p in oss:
        files[f"oss-{p['slug']}.svg"] = oss_tile(p)
    # every animation removed: the base state is the finished cube with its satellites docked
    files["hero-static.svg"] = re.sub(r"<animate(?:Transform|Motion)?\b[^>]*/>", "", files["hero.svg"]).replace(' class="breathe"', "")
    for name, content in files.items():
        (OUT / name).write_text(content)
    print(f"wrote {len(files)} files to {OUT}")


if __name__ == "__main__":
    main()
