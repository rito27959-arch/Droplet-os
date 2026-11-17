"""Liquid rendering for DROPLET BOOT (v2).

Everything liquid (wordmark, progress bar, password beads) is a signed distance
field shaded as CLEAR WATER lit by the eclipse:
  - Fresnel rim reflecting a sky gradient
  - REFLECTION and inverted REFRACTION of the eclipse ring itself (each curved
    stroke behaves like a lens and shows a tiny ring)                   [item 1]
  - key light + ring lobe follow the corona light angle every frame   [item 2]
  - a darker band inside the rim (thickness), cyan caustic, sharp glints
"""
import math

import numpy as np
from scipy.ndimage import gaussian_filter

from glyphs import wordmark_sdf

def c(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)
SOFT, CYAN, WHITE, ICE = c("#80A9FF"), c("#9BE7FF"), c("#F5F7FC"), c("#C9DBFF")

# direction from the text towards the eclipse (screen y is down): up and toward the viewer
E = np.array([0.0, -0.74, 0.67], np.float32); E /= np.linalg.norm(E)
EX = np.array([1.0, 0.0, 0.0], np.float32)
EY = np.cross(E, EX); EY /= np.linalg.norm(EY)
RING_RAD, RING_W = 0.23, 0.035


def smooth(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x):
    return 1 - (1 - np.clip(x, 0, 1)) ** 3
def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def eclipse_env(d, light_angle):
    """Radiance of the eclipse seen in direction d (H, W, 3)."""
    dot = np.clip(d @ E, -1, 1)
    rho = np.arccos(dot)
    psi = np.arctan2(d @ EY, d @ EX)
    lobe = 0.15 + 0.85 * ((1 + np.cos(psi - light_angle)) / 2) ** 3
    ring = np.exp(-((rho - RING_RAD) / RING_W) ** 2) * lobe
    glow = np.exp(-np.clip(rho - RING_RAD, 0, None) / 0.12) * (rho > RING_RAD) * 0.18 * lobe
    return WHITE[None, None] * (ring * 0.9)[..., None] + SOFT[None, None] * (ring * 0.35 + glow)[..., None]


def shade(S, ss, thick, light_angle, presence=1.0):
    """Clear-water material for a signed distance field S (pixels at ss, >0 outside).
    Returns premultiplied RGBA at 1x where alpha = light absorbed from behind."""
    cover = np.clip(0.5 - S / ss, 0, 1)
    H, W = S.shape
    if cover.max() <= 0:
        return np.zeros((H // ss, W // ss, 4), np.float32)
    thick = max(thick, 1.0)
    p = np.clip(-S / thick, 0, 1)
    h = np.sqrt(1 - (1 - p) ** 2) * thick
    hy, hx = np.gradient(gaussian_filter(h * 1.7, 0.8 * ss))
    n = np.dstack([-hx, -hy, np.ones_like(h) * 0.9]).astype(np.float32)
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    V = np.array([0, 0, 1], np.float32)
    ndv = np.clip(n[..., 2], 0, 1)

    # key light sits on the bright side of the corona and moves with it
    L = E + 0.30 * (math.cos(light_angle) * EX + math.sin(light_angle) * EY)
    L /= np.linalg.norm(L)
    def blinn(Ld, e):
        Hh = (Ld + V) / np.linalg.norm(Ld + V)
        return np.clip(n @ Hh, 0, 1) ** e
    fill = np.array([-0.6, -0.5, 0.6], np.float32); fill /= np.linalg.norm(fill)
    spec = blinn(L, 240) * 2.4 + blinn(L, 50) * 0.45 + blinn(fill, 140) * 0.35

    fres = (1 - ndv) ** 1.7
    up = smooth(-n[..., 1] * 1.8 + 0.25)
    sky = SOFT[None, None] * (0.50 * (1 - up[..., None])) + WHITE[None, None] * (0.85 * up[..., None])
    # reflection of the eclipse, and its inverted image through the water lens
    r = 2 * ndv[..., None] * n - V
    refl = eclipse_env(r, light_angle)
    # through the water lens the ring is seen inverted around the eclipse direction
    k = 1.25
    d = E[None, None] - k * (n[..., 0:1] * EX[None, None] + n[..., 1:2] * EY[None, None])
    d /= np.linalg.norm(d, axis=2, keepdims=True)
    refr = eclipse_env(d, light_angle)
    band = np.exp(-((p - 0.30) / 0.14) ** 2)
    caust = smooth(n[..., 1] * 2.2) * np.exp(-p / 0.45)
    light = (sky * (fres * 1.0)[..., None]
             + refl * (fres * 1.1)[..., None]
             + refr * ((1 - fres) * p * 0.85)[..., None]
             + CYAN[None, None] * (caust * 0.70)[..., None]
             + WHITE[None, None] * np.clip(spec, 0, 1.3)[..., None]
             + ICE[None, None] * 0.03)
    absorb = cover * np.clip(0.10 + band * 0.42, 0, 1)
    pm = np.dstack([np.clip(light, 0, 1.4) * cover[..., None], absorb]) * presence
    Hs, Ws = H // ss * ss, W // ss * ss
    return pm[:Hs, :Ws].reshape(Hs // ss, ss, Ws // ss, ss, 4).mean(axis=(1, 3)).astype(np.float32)


class LiquidWordmark:
    """Custom logotype; condenses from beads (intro) and evaporates into rising beads (outro)."""

    def __init__(self, text="DROPLET", cap_px=50, ss=2, seed=7):
        self.ss = ss
        self.sdf = wordmark_sdf(text, cap_px, ss)
        self.H, self.W = self.sdf.shape
        self.thick = float(-self.sdf.min())
        rng = np.random.default_rng(seed)
        core = np.argwhere(-self.sdf > self.thick * 0.5)
        rng.shuffle(core)
        spacing = self.thick * 1.9
        beads = []
        for y, x in core:
            if all((y - by) ** 2 + (x - bx) ** 2 > spacing ** 2 for by, bx in beads):
                beads.append((y, x))
        self.beads = np.array(beads, np.float32)
        xn = self.beads[:, 1] / self.W
        self.t0 = 0.05 + xn * 0.45 + rng.uniform(0, 0.10, len(beads))
        self.rmax = self.thick * rng.uniform(1.2, 1.6, len(beads))
        self.rise = rng.uniform(0.6, 1.4, len(beads))
        self.yy, self.xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)

    @property
    def size(self):
        return self.W // self.ss, self.H // self.ss

    def _beads(self, t, out=False):
        F = np.full_like(self.sdf, 1e3)
        k = self.thick * 1.2
        for (by, bx), t0, rm, rs in zip(self.beads, self.t0, self.rmax, self.rise):
            if out:   # evaporation: beads shrink and drift upward
                g = 1 - float(ease_out((t - 0.25 - t0 * 0.6) / 0.5))
                by = by - rs * self.thick * 3.0 * float(smooth((t - 0.2 - t0 * 0.6) / 0.7))
            else:
                g = float(ease_out((t - t0) / 0.45))
            if g <= 0.02:
                continue
            d = np.sqrt((self.xx - bx) ** 2 + ((self.yy - by) * (1 + 0.25 * (1 - g))) ** 2) - rm * g
            F = smin(F, d, k)
        return F

    def shape(self, t, out=False):
        xn = self.xx / self.W
        if out:
            m = 1 - smooth((t - xn * 0.35) / 0.3)          # letters break into beads
            return self._beads(t, True) * (1 - m) + self.sdf * m
        m = smooth((t - 0.40 - xn * 0.45) / 0.35)
        S = self._beads(t) * (1 - m) + self.sdf * m
        rip = 0.9 * self.ss * np.sin(xn * 38 - t * 9) * np.exp(-np.clip(t - 1.0 - xn * 0.5, 0, None) * 2.6) * m
        return S + rip

    def render(self, t, light_angle, out=False):
        return shade(self.shape(t, out), self.ss, self.thick, light_angle)


class LiquidBar:
    """Progress bar as a thread of water with a rounded meniscus at its head."""

    def __init__(self, width_px, height_px, ss=2):
        self.ss = ss
        pad = int(height_px * 2 * ss)
        self.W, self.H = int(width_px * ss) + 2 * pad, int(height_px * ss) + 2 * pad
        self.pad, self.r = pad, height_px * ss / 2
        self.len = width_px * ss
        self.yy, self.xx = np.mgrid[0:self.H, 0:self.W].astype(np.float32)

    def render(self, progress, t, light_angle):
        L = max(progress, 0.0) * self.len
        if L < 1:
            return np.zeros((self.H // self.ss, self.W // self.ss, 4), np.float32)
        x0, y0 = self.pad, self.H / 2
        x1 = x0 + L
        px = np.clip(self.xx, x0, x1)
        capsule = np.hypot(self.xx - px, self.yy - y0) - self.r
        # meniscus: the leading edge bulges slightly and breathes
        hr = self.r * (1.28 + 0.06 * math.sin(t * 7))
        head = np.hypot(self.xx - (x1 - hr * 0.35), self.yy - y0) - hr
        S = smin(capsule, head, self.r * 1.4)
        return shade(S, self.ss, self.r, light_angle)


def bead_row(count, slots, size_px, ss=2):
    """Password bullets: identical water beads, the newest one still settling."""
    gap = size_px * 1.9
    W = int((slots * gap + size_px * 2) * ss); H = int(size_px * 3 * ss)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    S = np.full((H, W), 1e3, np.float32)
    r = size_px / 2 * ss
    for i in range(count):
        cx = (size_px + i * gap) * ss
        S = np.minimum(S, np.hypot(xx - cx, (yy - H / 2) * (1.08 if i == count - 1 else 1)) - r)
    return S, r
