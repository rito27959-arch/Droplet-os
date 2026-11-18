"""Phosphor icons (MIT) as UI glyphs — optically balanced, consistent weights (SF Symbols role)."""
import io
import re

import cairosvg
import numpy as np
from PIL import Image

from core import S

ROOT = "/home/claude/aura-deps/ph/package/assets"


def ph(name, size_pt=16, color=(1, 1, 1), weight="regular", alpha=1.0):
    path = f"{ROOT}/{weight}/{name}{'' if weight == 'regular' else '-' + weight}.svg"
    svg = open(path).read()
    px = int(round(size_pt * S))
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=px * 4, output_height=px * 4)
    a = np.asarray(Image.open(io.BytesIO(png)).convert("RGBA").resize((px, px), Image.LANCZOS), np.float32)[..., 3] / 255
    rgba = np.dstack([np.broadcast_to(np.asarray(color, np.float32), a.shape + (3,)), a * alpha])
    return Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA")
