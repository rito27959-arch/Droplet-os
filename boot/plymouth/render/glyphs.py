"""DROPLET custom logotype — geometric monoline letterforms built from analytic
signed-distance primitives (capsules and arcs), so every stroke is a perfect
liquid tube. Original design, no font involved.

Design rules
  - monoline, round terminals (surface tension), stroke = 0.14 cap height
  - the O is a perfect circle: it echoes the eclipse above it
  - bowls of D / R / P are true semicircles joined to straight stems
  - the E's middle arm is shorter (optical balance); the R's leg starts at the bowl
"""
import numpy as np

STROKE = 0.17      # stroke width / cap height (thick enough to read as liquid)
TRACK = 0.34       # letter spacing / cap height


def seg(x, y, ax, ay, bx, by):
    px, py, vx, vy = x - ax, y - ay, bx - ax, by - ay
    h = np.clip((px * vx + py * vy) / (vx * vx + vy * vy), 0, 1)
    return np.hypot(px - vx * h, py - vy * h)


def arc(x, y, cx, cy, r, a0, a1):
    """Distance to a circular arc from angle a0 to a1 (radians, y down)."""
    dx, dy = x - cx, y - cy
    ang = np.arctan2(dy, dx)
    mid, half = (a0 + a1) / 2, (a1 - a0) / 2
    inside = np.abs(np.angle(np.exp(1j * (ang - mid)))) <= half
    d_ring = np.abs(np.hypot(dx, dy) - r)
    e0 = np.hypot(x - (cx + r * np.cos(a0)), y - (cy + r * np.sin(a0)))
    e1 = np.hypot(x - (cx + r * np.cos(a1)), y - (cy + r * np.sin(a1)))
    return np.where(inside, d_ring, np.minimum(e0, e1))


def bowl(x, y, x0, top, bot, width):
    """Stem-attached bowl: horizontal lines then a semicircle (D/P/R)."""
    r = (bot - top) / 2
    cx = x0 + width - r
    return np.minimum.reduce([
        seg(x, y, x0, top, cx, top),
        seg(x, y, x0, bot, cx, bot),
        arc(x, y, cx, top + r, r, -np.pi / 2, np.pi / 2),
    ])


# each glyph: (advance width in cap units, function(x, y) -> centreline distance)
# coordinates in cap units: y = 0 top, y = 1 baseline; s = half stroke (inset)
def glyphs():
    s = STROKE / 2
    t, b = s, 1 - s
    G = {}
    G["D"] = (0.80, lambda x, y: np.minimum(seg(x, y, s, t, s, b), bowl(x, y, s, t, b, 0.80 - 2 * s)))
    G["R"] = (0.70, lambda x, y: np.minimum.reduce([
        seg(x, y, s, t, s, b), bowl(x, y, s, t, 0.54, 0.70 - 2 * s),
        seg(x, y, 0.36, 0.54, 0.70 - s, b)]))
    G["O"] = (1.00, lambda x, y: np.abs(np.hypot(x - 0.5, y - 0.5) - (0.5 - s)))
    G["P"] = (0.66, lambda x, y: np.minimum(seg(x, y, s, t, s, b), bowl(x, y, s, t, 0.56, 0.66 - 2 * s)))
    G["L"] = (0.56, lambda x, y: np.minimum(seg(x, y, s, t, s, b), seg(x, y, s, b, 0.56 - s, b)))
    G["E"] = (0.60, lambda x, y: np.minimum.reduce([
        seg(x, y, s, t, s, b), seg(x, y, s, t, 0.60 - s, t),
        seg(x, y, s, 0.5, 0.50 - s, 0.5), seg(x, y, s, b, 0.60 - s, b)]))
    G["T"] = (0.70, lambda x, y: np.minimum(seg(x, y, s, t, 0.70 - s, t), seg(x, y, 0.35, t, 0.35, b)))
    G["S"] = (0.62, lambda x, y: np.minimum.reduce([
        arc(x, y, 0.31, 0.27, 0.27 - s * 0.2, np.pi * 0.15, np.pi * 1.95),
        arc(x, y, 0.31, 0.73, 0.27 - s * 0.2, -np.pi * 0.85, np.pi * 0.95)]))
    return G


def wordmark_sdf(text, cap_px, ss=2, pad_cap=0.6):
    """Signed distance field (pixels at ss resolution, > 0 outside)."""
    G = glyphs()
    cap = cap_px * ss
    adv = [G[ch][0] for ch in text]
    total = sum(adv) + TRACK * (len(text) - 1)
    pad = pad_cap * cap
    W, H = int(total * cap + 2 * pad), int(cap + 2 * pad)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    X, Y = (xx - pad) / cap, (yy - pad) / cap
    d = np.full((H, W), 1e3, np.float32)
    x0 = 0.0
    for ch, a in zip(text, adv):
        d = np.minimum(d, G[ch][1](X - x0, Y))
        x0 += a + TRACK
    return (d - STROKE / 2) * cap        # to pixels, minus half stroke
