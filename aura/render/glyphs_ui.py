"""UI symbols for DROPLET AURA.

Phosphor Icons 2.1 (MIT, https://phosphoricons.com) rendered from SVG with cairosvg,
recoloured; plus the Droplet OS eclipse mark (original).
glyph(name, size_pt, color, weight) -> RGBA PIL image at 2x.
"""
import io
import re
from functools import lru_cache
from pathlib import Path

import cairosvg
import numpy as np
from PIL import Image, ImageDraw

from core import S

PHOSPHOR = Path("/home/claude/vendor/node_modules/@phosphor-icons/core/assets")

NAMES = {
    "recents": "clock", "apps": "squares-four", "desktop": "desktop", "doc": "file-text",
    "download": "download-simple", "disk": "hard-drive", "network": "globe-simple",
    "wifi": "wifi-high", "battery": "battery-high", "search": "magnifying-glass",
    "controls": "sliders-horizontal", "back": "caret-left", "forward": "caret-right",
    "grid": "squares-four", "list": "list-bullets", "share": "export", "tag": "tag",
    "minimize": "minus", "expand": "arrows-out-simple", "close": "x", "more": "dots-three",
    "folder": "folder-simple", "cloud": "cloud", "airdrop": "broadcast", "home": "house",
    "music": "music-notes-simple", "image": "image", "sparkle": "sparkle",
}


@lru_cache(maxsize=256)
def _render(name, px, weight):
    if name == "eclipse":
        return _eclipse(px)
    file = PHOSPHOR / weight / (NAMES.get(name, name) + ("" if weight == "regular" else f"-{weight}") + ".svg")
    svg = file.read_text()
    svg = re.sub(r'fill="currentColor"', 'fill="#ffffff"', svg)
    if "<svg fill=" not in svg and " fill=" not in svg.split(">", 1)[0]:
        svg = svg.replace("<svg ", "<svg fill=\"#ffffff\" ", 1)
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=px * 4, output_height=px * 4)
    im = Image.open(io.BytesIO(png)).convert("RGBA").resize((px, px), Image.LANCZOS)
    return np.asarray(im, np.float32)[..., 3] / 255


def _eclipse(px):
    """Droplet OS mark: the eclipse as a luminous annulus, thick toward the light
    (upper right), hairline on the far side. Outer disc offset minus inner disc."""
    N = px * 8
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    c, R = N / 2, N * 0.29
    off = R * 0.10
    outer = np.hypot(xx - (c + off * 0.5), yy - (c - off * 0.87)) < R * 1.16
    inner = np.hypot(xx - c, yy - c) < R
    m = (outer & ~inner).astype(np.float32) * 255
    return np.asarray(Image.fromarray(m.astype(np.uint8)).resize((px, px), Image.LANCZOS), np.float32) / 255


def glyph(name, size_pt=16, color=(1, 1, 1), weight="regular", alpha=1.0, stroke=None):
    px = int(round(size_pt * S))
    a = _render(name, px, weight) * alpha
    rgba = np.dstack([np.broadcast_to(np.asarray(color, np.float32), a.shape + (3,)), a])
    return Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA")
