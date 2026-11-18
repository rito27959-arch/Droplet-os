"""DROPLET AURA — offline UI renderer core (design validation, 0.2).

Renders screens at 2x with a physically-inspired Liquid Glass material:
  - lensing: the glass bezel bends the background (displacement from a
    convex height profile), centre stays clear
  - chromatic dispersion at the rim (R/G/B displaced differently)
  - light frosting (small blur) + adaptive tint for legibility
  - specular rim lit from the top-left, faint counter-rim bottom-right
  - soft contact shadow
All coordinates are given in 1x points and multiplied by S.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter, map_coordinates

S = 2  # render scale (2x / Retina)

def hexc(h, a=None):
    h = h.lstrip("#")
    v = np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)
    return v

# Droplet Design tokens (family system)
NUIT = hexc("#05070c"); NUIT_ELEVE = hexc("#0a0e17"); VERRE = hexc("#10151f"); VERRE_HAUT = hexc("#1a2130")
TXT = hexc("#f7f9fc"); TXT2 = hexc("#a5b0c1"); TXT3 = hexc("#7d889b")
GOUTTE = hexc("#ff2d55"); BLEU = hexc("#0a84ff"); INDIGO = hexc("#5e5ce6"); VIOLET = hexc("#bf5af2")
ORANGE = hexc("#ff9f0a"); VERT = hexc("#30d158"); CYAN = hexc("#64d2ff"); GRAPHITE = hexc("#98989d")
WHITE = np.ones(3, np.float32)

FONT_DIR = "/usr/share/fonts/opentype/inter/"
FONTS = {
    "regular": "Inter-Regular.otf", "medium": "Inter-Medium.otf", "semibold": "Inter-SemiBold.otf",
    "bold": "Inter-Bold.otf", "display-semibold": "InterDisplay-SemiBold.otf", "display-bold": "InterDisplay-Bold.otf",
    "display-medium": "InterDisplay-Medium.otf", "display-light": "InterDisplay-Light.otf",
}
_font_cache = {}


def font(weight, size_pt):
    key = (weight, size_pt)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(FONT_DIR + FONTS[weight], int(round(size_pt * S)))
    return _font_cache[key]


# Apple HIG, macOS tracking values (points) — applied to Inter, our open SF substitute
HIG_TRACKING = {6: .24, 7: .23, 8: .21, 9: .17, 10: .12, 11: .06, 12: 0.0, 13: -.08, 14: -.15, 15: -.23,
                16: -.31, 17: -.43, 18: -.44, 19: -.45, 20: -.45, 21: -.36, 22: -.26, 23: -.10, 24: .07}


def hig_tracking(size):
    k = int(round(size))
    return HIG_TRACKING.get(k, 0.07 if k > 24 else 0.24)


def smooth(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- signed distances
def sdf_rbox(H, W, x, y, w, h, r):
    """Rounded box, all in pixels. Negative inside. Returns (d, gx, gy) outward normal."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = x + w / 2, y + h / 2
    px, py = xx - cx, yy - cy
    qx, qy = np.abs(px) - (w / 2 - r), np.abs(py) - (h / 2 - r)
    ox, oy = np.maximum(qx, 0), np.maximum(qy, 0)
    out = np.hypot(ox, oy)
    d = out + np.minimum(np.maximum(qx, qy), 0) - r
    # outward normal
    inside_corner = out > 1e-3
    nx = np.where(inside_corner, ox / np.maximum(out, 1e-6), (qx >= qy).astype(np.float32))
    ny = np.where(inside_corner, oy / np.maximum(out, 1e-6), (qy > qx).astype(np.float32))
    return d, nx * np.sign(px + 1e-6), ny * np.sign(py + 1e-6)


def squircle_mask(size, n=5.0, ss=4):
    """Continuous-corner app-icon shape (superellipse)."""
    N = size * ss
    img = Image.new("L", (N, N), 0)
    t = np.linspace(0, 2 * np.pi, 720)
    x = np.sign(np.cos(t)) * np.abs(np.cos(t)) ** (2 / n)
    y = np.sign(np.sin(t)) * np.abs(np.sin(t)) ** (2 / n)
    pts = list(zip((x + 1) / 2 * (N - 1), (y + 1) / 2 * (N - 1)))
    ImageDraw.Draw(img).polygon(pts, fill=255)
    return np.asarray(img.resize((size, size), Image.LANCZOS), np.float32) / 255


# ---------------------------------------------------------------- compositing
class Canvas:
    def __init__(self, w_pt, h_pt, bg):
        self.W, self.H = int(w_pt * S), int(h_pt * S)
        self.px = np.zeros((self.H, self.W, 3), np.float32) + bg

    def over(self, rgb, a, x=0, y=0):
        """Composite straight-alpha layer (rgb HxWx3, a HxW) at pixel x, y."""
        h, w = a.shape
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.W, x + w), min(self.H, y + h)
        if x1 <= x0 or y1 <= y0: return
        sa = a[y0 - y:y1 - y, x0 - x:x1 - x, None]
        reg = self.px[y0:y1, x0:x1]
        reg[:] = reg * (1 - sa) + rgb[y0 - y:y1 - y, x0 - x:x1 - x] * sa

    def image(self, img, x_pt, y_pt, opacity=1.0):
        a = np.asarray(img, np.float32) / 255
        self.over(a[..., :3], a[..., 3] * opacity, int(round(x_pt * S)), int(round(y_pt * S)))

    def shadow2(self, x, y, w, h, r, k=1.0):
        """macOS-like window shadow: wide ambient + tight contact."""
        self.shadow(x, y, w, h, r, blur=60, dy=30, k=0.50 * k)
        self.shadow(x, y, w, h, r, blur=6, dy=2, k=0.35 * k)

    def shadow(self, x, y, w, h, r, blur=28, dy=14, k=0.38):
        pad = int(blur * S * 3)
        X, Y, Wp, Hp = int(x * S) - pad, int(y * S) - pad, int(w * S) + 2 * pad, int(h * S) + 2 * pad
        d, _, _ = sdf_rbox(Hp, Wp, pad, pad + dy * S, w * S, h * S, r * S)
        a = gaussian_filter((d < 0).astype(np.float32), blur * S / 2) * k
        self.over(np.zeros((Hp, Wp, 3), np.float32), a, X, Y)

    @staticmethod
    def auto_tracking(size):
        """Tracking in points, after Apple's SF tracking table, adapted to Inter
        (Inter is wider than SF Text: a little tighter at every size)."""
        table = [(11, 0.02), (12, -0.02), (13, -0.10), (14, -0.16), (15, -0.22), (17, -0.38),
                 (20, -0.45), (24, -0.55), (34, -0.85), (60, -1.6)]
        for sz, tr in table:
            if size <= sz:
                return tr
        return -0.028 * size

    def text(self, s, x_pt, y_pt, weight="regular", size=13, color=TXT, alpha=1.0, anchor="ls",
             tracking=None, shadow=0.0):
        """Text with HIG tracking (points), kerning preserved (glyph x from prefix advances)."""
        f = font(weight, size)
        tr = (hig_tracking(size) if tracking is None else tracking) * S
        adv = [f.getlength(s[:i]) for i in range(len(s) + 1)]
        total = adv[-1] + tr * (len(s) - 1)
        x0 = x_pt * S - (total / 2 if anchor[0] == "m" else total if anchor[0] == "r" else 0)
        asc, desc = f.getmetrics()
        pad = int(size * S)
        Wl, Hl = int(total) + 2 * pad, asc + desc + 2 * pad
        layer = Image.new("L", (Wl, Hl), 0)
        d = ImageDraw.Draw(layer)
        for i, ch in enumerate(s):
            d.text((pad + adv[i] + tr * i, pad + asc), ch, font=f, fill=255, anchor="ls")
        a = np.asarray(layer, np.float32) / 255
        cap = -f.getbbox("H", anchor="ls")[1]                 # cap height in px
        yb = {"s": y_pt * S, "m": y_pt * S + cap / 2, "t": y_pt * S + asc}[anchor[1]]
        X, Y = int(round(x0 - pad)), int(round(yb - asc - pad))
        if shadow > 0:
            sh = gaussian_filter(a, 2.5 * S) * shadow
            self.over(np.zeros(a.shape + (3,), np.float32), sh, X, Y + int(S))
        self.over(np.broadcast_to(np.asarray(color, np.float32), a.shape + (3,)).copy(), a * alpha, X, Y)
        return total / S

    def text_width(self, s, weight="regular", size=13, tracking=None):
        tr = hig_tracking(size) if tracking is None else tracking
        return font(weight, size).getlength(s) / S + tr * (len(s) - 1)

    # ------------------------------------------------------------ Liquid Glass
    LIGHT = (0.50, -0.87)          # global light: the eclipse, upper right

    def glass(self, x, y, w, h, r, tint=VERRE, tint_a=0.30, frost=5, bezel=None, lens=1.0,
              dispersion=1.0, rim=0.75, lift=0.035, shadow=True, source=None, hairline=0.10,
              ambient=None):
        """Liquid Glass panel (x, y, w, h, r in points)."""
        if shadow:
            self.shadow(x, y, w, h, r, blur=24, dy=10, k=0.30)
        m = 6
        X0, Y0 = max(0, int((x - m) * S)), max(0, int((y - m) * S))
        X1, Y1 = min(self.W, int((x + w + m) * S)), min(self.H, int((y + h + m) * S))
        Hh, Ww = Y1 - Y0, X1 - X0
        d, nx, ny = sdf_rbox(Hh, Ww, x * S - X0, y * S - Y0, w * S, h * S, r * S)
        cover = np.clip(0.5 - d, 0, 1)
        inside = np.clip(-d, 0, None)
        bz = (bezel if bezel is not None else min(18, min(w, h) * 0.35)) * S
        # convex bezel height profile -> refraction displacement (pixels)
        t = np.clip(inside / bz, 0, 1)
        slope = (1 - t) / np.sqrt(np.maximum(1 - (1 - t) ** 2, 0.02))       # d(height)/d(dist) of a circle
        slope = np.clip(slope, 0, 6) * (t < 1)
        disp = slope * bz * 0.22 * lens                                       # bends light inward
        src = self.px if source is None else source
        mg = int(frost * S * 3 + bz * 0.5 + 4)
        BX0, BY0 = max(0, X0 - mg), max(0, Y0 - mg)
        BX1, BY1 = min(self.W, X1 + mg), min(self.H, Y1 + mg)
        sub = src[BY0:BY1, BX0:BX1]
        blurred = np.stack([gaussian_filter(sub[..., c], frost * S) for c in range(3)], -1) if frost > 0 else sub
        yy, xx = np.mgrid[Y0 - BY0:Y1 - BY0, X0 - BX0:X1 - BX0].astype(np.float32)
        out = np.zeros((Hh, Ww, 3), np.float32)
        for c, k in enumerate((1.0 + 0.10 * dispersion, 1.0, 1.0 - 0.10 * dispersion)):
            sy = yy + ny * disp * k
            sx = xx + nx * disp * k
            out[..., c] = map_coordinates(blurred[..., c], [sy, sx], order=1, mode="nearest")
        # adaptive tint + glass lift
        out = out * (1 - tint_a) + tint * tint_a + lift
        # specular rim, light from top-left
        L = np.array(self.LIGHT, np.float32); L = L / np.linalg.norm(L)
        facing = np.clip(nx * L[0] + ny * L[1], 0, 1)
        counter = np.clip(-(nx * L[0] + ny * L[1]), 0, 1)
        edge = np.exp(-inside / (0.9 * S))
        soft = np.exp(-inside / (7 * S))
        spec = edge * (0.18 + 0.82 * facing ** 1.5) * rim + edge * counter ** 2 * rim * 0.35 + soft * facing * 0.05
        out = out + spec[..., None] * (1 - out) * 0.9
        # hairline: the glass edge always reads, even on black
        out = out + (np.exp(-inside / (0.6 * S)) * hairline)[..., None] * (1 - out)
        # ambient spill: colourful light nearby tints the surface (HIG: large sidebars)
        if ambient is not None:
            col, amt = ambient
            spill = np.clip(1 - (yy - Y0) / max(Hh, 1), 0, 1) ** 2 * amt
            out = out + (np.asarray(col) - out) * spill[..., None]
        reg = self.px[Y0:Y1, X0:X1]
        reg[:] = reg * (1 - cover[..., None]) + np.clip(out, 0, 1) * cover[..., None]

    def solid(self, x, y, w, h, r, color, a=1.0, border=None):
        X0, Y0 = max(0, int((x - 2) * S)), max(0, int((y - 2) * S))
        X1, Y1 = min(self.W, int((x + w + 2) * S)), min(self.H, int((y + h + 2) * S))
        d, _, _ = sdf_rbox(Y1 - Y0, X1 - X0, x * S - X0, y * S - Y0, w * S, h * S, r * S)
        cover = np.clip(0.5 - d, 0, 1) * a
        reg = self.px[Y0:Y1, X0:X1]
        reg[:] = reg * (1 - cover[..., None]) + np.asarray(color) * cover[..., None]
        if border is not None:
            col, ba = border
            ring = np.clip(1 - np.abs(d + 0.5 * S) / (0.5 * S), 0, 1) * ba
            reg[:] = reg * (1 - ring[..., None]) + np.asarray(col) * ring[..., None]

    def save(self, path, dither=True):
        img = self.px
        if dither:
            rng = np.random.default_rng(0)
            img = img + (rng.random(img.shape, np.float32) - rng.random(img.shape, np.float32)) / 255
        Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)
