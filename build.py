"""Bangun aset SVG untuk README profil GitHub (versi terang dan gelap).

Jalankan: python build.py   (butuh: pip install fonttools brotli)

Semua teks memakai font yang disematkan langsung ke SVG (dipangkas ke huruf yang dipakai),
jadi tampilannya sama di semua browser tanpa memuat font dari luar.
"""

from __future__ import annotations

import base64
import io
import pathlib
from html import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "assets"
FONTS = ROOT / "fonts"

# ---------- Tinta dan tema (sama dengan Jam Bareng: flyer gig risograf) ----------

INK = {"blue": "#5b78ff", "pink": "#ff4fb0", "yellow": "#ffe14a", "red": "#ff5a2b", "print": "#121316"}

THEMES = {
    "dark": {
        "bg": "#121316",
        "surface": "#1a1b1f",
        "text": "#f3f1ec",
        "dim": "#a9abb4",
        "muted": "#80828c",
        "line": "rgba(243,241,236,0.12)",
        "dots": "rgba(243,241,236,0.16)",
    },
    "light": {
        "bg": "#f3f1ec",
        "surface": "#fbfaf6",
        "text": "#121316",
        "dim": "#45474f",
        "muted": "#6b6d76",
        "line": "rgba(18,19,22,0.14)",
        "dots": "rgba(18,19,22,0.14)",
    },
}

# ---------- Font: instance statis per bobot, diukur dan dipangkas ----------

FACES = {
    # nama: (berkas, bobot)
    "display": ("big-shoulders-display-latin-wght-normal.woff2", 900),
    "body": ("archivo-latin-wght-normal.woff2", 500),
    "bodybold": ("archivo-latin-wght-normal.woff2", 600),
}

_static: dict[str, TTFont] = {}


def static_font(face: str) -> TTFont:
    if face not in _static:
        file, weight = FACES[face]
        font = TTFont(FONTS / file)
        _static[face] = instancer.instantiateVariableFont(font, {"wght": weight})
    return _static[face]


def measure(text: str, face: str, size: float, tracking: float = 0) -> float:
    """Lebar teks dalam px menurut metrik font."""
    font = static_font(face)
    cmap = font.getBestCmap()
    hmtx = font["hmtx"]
    upm = font["head"].unitsPerEm
    width = sum(hmtx[cmap.get(ord(ch), cmap[ord("?")])][0] for ch in text)
    return width * size / upm + tracking * max(0, len(text) - 1)


def font_face_css(face: str, chars: set[str]) -> str:
    buf = io.BytesIO()
    static_font(face).save(buf)
    buf.seek(0)
    font = TTFont(buf)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    opts.name_IDs = []
    opts.notdef_outline = True
    sub = subset.Subsetter(opts)
    sub.populate(unicodes={ord(c) for c in chars | {" "}})
    sub.subset(font)
    out = io.BytesIO()
    font.flavor = "woff2"
    font.save(out)
    data = base64.b64encode(out.getvalue()).decode()
    return f"@font-face{{font-family:'{face}';src:url(data:font/woff2;base64,{data}) format('woff2');}}"


class Svg:
    """Penyusun SVG kecil yang mencatat huruf per font untuk dipangkas."""

    def __init__(self, w: int, h: int, title: str):
        self.w, self.h, self.title = w, h, title
        self.parts: list[str] = []
        self.defs: list[str] = []
        self.css: list[str] = []
        self.chars: dict[str, set[str]] = {f: set() for f in FACES}

    def add(self, s: str) -> None:
        self.parts.append(s)

    def text(self, x: float, y: float, s: str, face: str, size: float, fill: str, extra: str = "") -> None:
        self.chars[face] |= set(s)
        self.add(
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{face}" font-size="{size}" fill="{fill}" {extra}>{escape(s)}</text>'
        )

    def render(self) -> str:
        faces = "".join(font_face_css(f, c) for f, c in self.chars.items() if c)
        reduce = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
        style = f"<style>{faces}{''.join(self.css)}{reduce}</style>"
        defs = f"<defs>{''.join(self.defs)}</defs>" if self.defs else ""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.title)}">'
            f"<title>{escape(self.title)}</title>{style}{defs}{''.join(self.parts)}</svg>"
        )


# ---------- Banner ----------

def hero(theme: str) -> str:
    t = THEMES[theme]
    W, H = 1280, 480
    s = Svg(W, H, "Moh Johan Farhan. Belajar ngoding dengan bikin hal yang bisa dimainin.")
    s.defs.append(
        f'<pattern id="dots" width="12" height="12" patternUnits="userSpaceOnUse">'
        f'<circle cx="3" cy="3" r="2" fill="{t["dots"]}"/><circle cx="9" cy="9" r="2" fill="{t["dots"]}"/></pattern>'
    )
    # Lapisan tinta meleset bergeser pelan, seperti cetakan risograf yang tidak pernah persis sama.
    s.css.append(
        "@keyframes driftA{0%{transform:translate(-6px,4px)}100%{transform:translate(-3px,6px)}}"
        "@keyframes driftB{0%{transform:translate(6px,-3px)}100%{transform:translate(4px,-6px)}}"
        ".inkA{animation:driftA 4.5s ease-in-out infinite alternate}"
        ".inkB{animation:driftB 5.5s ease-in-out infinite alternate}"
        "@keyframes eq{0%{transform:scaleY(.25)}100%{transform:scaleY(1)}}"
        ".bar{transform-box:fill-box;transform-origin:bottom;animation:eq ease-in-out infinite alternate}"
    )
    s.add(f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>')
    # Halftone di sudut kanan atas.
    s.add(f'<polygon points="{W},0 {W - 360},0 {W},360" fill="url(#dots)"/>')

    x = 72
    s.text(x, 92, "cvarSSS", "bodybold", 22, t["muted"])
    name_size = 150
    for i, line in enumerate(["MOH JOHAN", "FARHAN"]):
        y = 226 + i * 128
        s.chars["display"] |= set(line)
        common = f'x="{x}" y="{y}" font-family="display" font-size="{name_size}" letter-spacing="-1"'
        s.add(f'<text class="inkA" {common} fill="{INK["blue"]}">{line}</text>')
        s.add(f'<text class="inkB" {common} fill="{INK["pink"]}">{line}</text>')
        s.add(f'<text {common} fill="{t["text"]}">{line}</text>')
    s.text(x, 420, "Belajar ngoding dengan bikin hal yang bisa dimainin.", "body", 26, t["dim"])

    # Stiker "lagi dikerjain".
    sw, sh = 340, 268
    s.add(f'<g transform="translate(866 104) rotate(4)">')
    s.add(f'<rect x="10" y="10" width="{sw}" height="{sh}" fill="{INK["pink"]}"/>')
    s.add(f'<rect width="{sw}" height="{sh}" fill="{INK["yellow"]}"/>')
    s.text(28, 46, "Lagi dikerjain", "bodybold", 18, INK["print"])
    title_size = 72
    while measure("JAM BARENG", "display", title_size) > sw - 56:
        title_size -= 2
    s.text(28, 112, "JAM BARENG", "display", title_size, INK["print"])
    s.text(28, 142, "Game musik pakai gerakan tangan", "body", 17, INK["print"])
    colors = [INK["blue"], INK["pink"], INK["print"], INK["blue"], INK["pink"], INK["print"], INK["blue"], INK["pink"]]
    heights = [52, 74, 40, 66, 58, 80, 46, 62]
    durs = [0.9, 1.3, 0.7, 1.1, 0.8, 1.4, 1.0, 1.2]
    for i, (c, hgt, d) in enumerate(zip(colors, heights, durs)):
        bx = 28 + i * 36
        s.add(
            f'<rect class="bar" style="animation-duration:{d}s;animation-delay:-{i * 0.17:.2f}s" '
            f'x="{bx}" y="{238 - hgt}" width="26" height="{hgt}" fill="{c}"/>'
        )
    s.add(f'<rect x="28" y="238" width="{sw - 56}" height="3" fill="{INK["print"]}"/>')
    s.text(28, 260, "jam-bareng.pages.dev", "bodybold", 15, INK["print"])
    s.add("</g>")
    return s.render()


# ---------- Kartu proyek ----------

def glyph(kind: str, x: float, y: float, c: str, line: str) -> str:
    """Ikon kecil buatan sendiri, 56 x 56."""
    if kind == "jam":
        hs = [28, 48, 20, 40]
        return "".join(f'<rect x="{x + i * 14}" y="{y + 56 - h}" width="10" height="{h}" fill="{c}"/>' for i, h in enumerate(hs))
    if kind == "pulse":
        pts = [(0, 32), (14, 32), (20, 18), (28, 48), (36, 8), (42, 32), (56, 32)]
        p = " ".join(f"{x + a},{y + b}" for a, b in pts)
        return f'<polyline points="{p}" fill="none" stroke="{c}" stroke-width="5" stroke-linejoin="miter" stroke-linecap="square"/>'
    if kind == "ttt":
        g = "".join(
            f'<rect x="{x + 18 + i * 19}" y="{y}" width="3" height="56" fill="{line}"/>'
            f'<rect x="{x}" y="{y + 18 + i * 19}" width="56" height="3" fill="{line}"/>'
            for i in range(2)
        )
        g += f'<path d="M{x + 3} {y + 3}l12 12M{x + 15} {y + 3}l-12 12" stroke="{c}" stroke-width="4"/>'
        g += f'<circle cx="{x + 28}" cy="{y + 28}" r="6" fill="none" stroke="{c}" stroke-width="4"/>'
        g += f'<path d="M{x + 41} {y + 41}l12 12M{x + 53} {y + 41}l-12 12" stroke="{c}" stroke-width="4"/>'
        return g
    if kind == "type":
        g = f'<rect x="{x + 2}" y="{y + 6}" width="52" height="44" fill="none" stroke="{line}" stroke-width="3"/>'
        g += "".join(f'<rect x="{x + 10}" y="{y + 16 + i * 10}" width="{w}" height="4" fill="{c}"/>' for i, w in enumerate([30, 22]))
        g += f'<rect x="{x + 10 + 26}" y="{y + 34}" width="8" height="10" fill="{c}"/>'
        return g
    return ""


PROJECTS = [
    {
        "slug": "jam-bareng",
        "name": "JAM BARENG",
        "lines": ["Game musik berdua di depan satu webcam,", "dimainkan dengan gerakan tangan."],
        "tech": "TypeScript · MediaPipe · Web Audio",
        "status": "Live",
        "accent": INK["pink"],
        "glyph": "jam",
        "url": "https://jam-bareng.pages.dev",
    },
    {
        "slug": "ancu-kesehatan",
        "name": "ANCU KESEHATAN",
        "lines": ["Cek BMI dari berat dan tinggi badan,", "lengkap dengan saran sehat yang mudah dipahami."],
        "tech": "Python · Streamlit",
        "status": "Repo",
        "accent": INK["blue"],
        "glyph": "pulse",
        "url": "https://github.com/cvarSSS/ancu-kesehatan",
    },
    {
        "slug": "tictactoe",
        "name": "TICTACTOE UNBEATABLE",
        "lines": ["Tic-tac-toe melawan komputer yang memakai", "minimax. Paling bagus kamu cuma bisa seri."],
        "tech": "Python · minimax",
        "status": "Repo",
        "accent": INK["yellow"],
        "glyph": "ttt",
        "url": "https://github.com/cvarSSS/TicTacToe-Unbeatable",
    },
    {
        "slug": "apocalypse",
        "name": "APOCALYPSE",
        "lines": ["Lirik lagu muncul huruf demi huruf", "di terminal, mengikuti tempo lagunya."],
        "tech": "Python · threading",
        "status": "Repo",
        "accent": INK["red"],
        "glyph": "type",
        "url": "https://github.com/cvarSSS/Apocalypse",
    },
]


def card(p: dict, theme: str) -> str:
    t = THEMES[theme]
    W, H = 600, 248
    s = Svg(W, H, f"{p['name'].title()}: {' '.join(p['lines'])}")
    s.add(f'<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" fill="{t["surface"]}" stroke="{t["line"]}"/>')
    s.add(f'<rect width="10" height="{H}" fill="{p["accent"]}"/>')
    # Kuning terlalu pucat di atas kertas terang; pakai tinta cetak untuk ikonnya.
    glyph_color = INK["print"] if (theme == "light" and p["accent"] == INK["yellow"]) else p["accent"]
    s.add(glyph(p["glyph"], W - 56 - 36, 34, glyph_color, t["muted"]))

    x = 44
    max_name = W - x - 56 - 36 - 24
    size = 56
    while measure(p["name"], "display", size) > max_name:
        size -= 2
    s.text(x, 92, p["name"], "display", size, t["text"])
    for i, line in enumerate(p["lines"]):
        assert measure(line, "body", 20) < W - x - 32, f"terlalu panjang: {line}"
        s.text(x, 134 + i * 28, line, "body", 20, t["dim"])

    s.add(f'<rect x="{x}" y="196" width="{W - x - 32}" height="1" fill="{t["line"]}"/>')
    s.text(x, 226, p["tech"], "bodybold", 15, t["muted"])
    label = p["status"]
    lw = measure(label, "bodybold", 14) + 24
    lx = W - 32 - lw
    if label == "Live":
        s.add(f'<rect x="{lx:.1f}" y="208" width="{lw:.1f}" height="26" fill="{p["accent"]}"/>')
        s.text(lx + 12, 226, label, "bodybold", 14, INK["print"])
    else:
        s.add(f'<rect x="{lx + 0.5:.1f}" y="208.5" width="{lw - 1:.1f}" height="25" fill="none" stroke="{t["line"]}"/>')
        s.text(lx + 12, 226, label, "bodybold", 14, t["muted"])
    return s.render()


def main() -> None:
    OUT.mkdir(exist_ok=True)
    for theme in THEMES:
        (OUT / f"hero-{theme}.svg").write_text(hero(theme), encoding="utf-8")
        for p in PROJECTS:
            (OUT / f"card-{p['slug']}-{theme}.svg").write_text(card(p, theme), encoding="utf-8")
    for f in sorted(OUT.glob("*.svg")):
        print(f"{f.name:34} {f.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
