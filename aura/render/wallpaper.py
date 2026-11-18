"""DROPLET AURA default wallpaper: "Éclipse" — the boot mark at planetary scale.

Night (scene-nuit), a vast dark sphere, its corona dispersed white -> goutte rose ->
violet -> deep blue, a sparse star field, film grain. One glow per screen (family rule):
the corona is that glow.

  wallpaper.py <out.png> [W_pt H_pt]
"""
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

from core import NUIT, S, WHITE, hexc

ROSE = hexc("#ff2d55"); ROSE_SOFT = hexc("#ff6a88"); VIOLET = hexc("#7b4dff"); DEEP = hexc("#1b2a8f")
SPHERE = hexc("#070a12")


def render(w_pt=1440, h_pt=900, seed=11, lumineux=False):
    W, H = int(w_pt * S), int(h_pt * S)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    k = H / 1800
    # sky: night with a barely perceptible vertical lift
    img = np.zeros((H, W, 3), np.float32) + NUIT
    img += (hexc("#0a0d18") - NUIT) * (1 - yy / H)[..., None] * 0.5

    cx, cy, R = (W * 0.79, H * 0.53, H * 0.37) if not lumineux else (W * 0.80, H * 0.30, H * 0.22)
    dx, dy = xx - cx, yy - cy
    r = np.hypot(dx, dy)
    th = np.arctan2(dy, dx)
    la = np.deg2rad(-118)                                   # brightest point: upper left, clear of windows
    lobe = ((1 + np.cos(th - la)) / 2)
    lobe_sharp = lobe ** 5
    out = np.clip(r - R, 0, None)
    outside = r > R

    def ring(off, width): return np.exp(-((r - (R + off * k)) / (width * k)) ** 2)
    # prismatic corona, dispersion stronger where the light is strongest
    PEACH = hexc("#ffd2c4")
    corona = (WHITE * (ring(0, 1.8) * (0.22 + 0.78 * lobe_sharp))[..., None] * 1.15
              + PEACH * (ring(2.5, 3.5) * (0.1 + 0.9 * lobe ** 4))[..., None] * 0.55
              + ROSE_SOFT * (ring(5, 7) * (0.2 + 0.8 * lobe ** 3))[..., None] * 0.9
              + ROSE * (ring(14, 16) * (0.15 + 0.85 * lobe ** 2.5))[..., None] * 0.75
              + VIOLET * (ring(34, 34) * (0.2 + 0.8 * lobe ** 2))[..., None] * 0.30)
    # atmosphere: broad glows, rose near the rim, violet then deep blue far out
    atmo = (ROSE * (np.exp(-out / (60 * k)) * (0.10 + 0.90 * lobe ** 2.5))[..., None] * 0.42
            + VIOLET * (np.exp(-out / (200 * k)) * (0.12 + 0.88 * lobe ** 2.5))[..., None] * 0.14
            + DEEP * (np.exp(-out / (520 * k)) * (0.15 + 0.85 * lobe ** 2))[..., None] * 0.13)
    if lumineux:
        # broad luminous field: the corona lights the whole sky, so glass has light to bend
        far = (ROSE * (np.exp(-out / (300 * k)) * (0.25 + 0.75 * lobe))[..., None] * 0.24
               + VIOLET * (np.exp(-out / (800 * k)) * (0.3 + 0.7 * lobe))[..., None] * 0.17
               + DEEP * (np.exp(-out / (2000 * k)))[..., None] * 0.24)
        # a low aurora band across the bottom, where the Dock sits
        band = np.exp(-((yy / H - 0.98) / 0.22) ** 2) * (0.6 + 0.4 * np.sin(xx / W * 3.1 + 0.6))
        far += (ROSE * 0.6 + VIOLET * 0.4) * (band * 0.17)[..., None]
        atmo = atmo + far
    img += (corona + atmo) * outside[..., None]
    # streamers: faint radial filaments in the corona (structure, not noise)
    rng = np.random.default_rng(seed)
    fil = np.zeros_like(r)
    for _ in range(46):
        a0 = rng.uniform(-np.pi, np.pi); wdt = rng.uniform(0.006, 0.02); ln = rng.uniform(60, 260) * k
        da = np.angle(np.exp(1j * (th - a0)))
        fil += np.exp(-(da / wdt) ** 2) * np.exp(-out / ln) * rng.uniform(0.3, 1.0)
    img += (ROSE_SOFT * 0.5 + WHITE * 0.5) * (fil * (0.1 + 0.9 * lobe ** 2) * 0.055 * outside)[..., None]

    # the sphere: dark glass, faint earthshine on the lit limb, subtle inner gradient
    inside = np.clip((R - r) / (1.2 * S), 0, 1)
    limb = np.exp(-(R - r) / (26 * k)) * lobe ** 2 * 0.06
    # faint volume: the sphere is lit very slightly from behind on the lit side
    facing = np.clip((dx * np.cos(la) + dy * np.sin(la)) / R, -1, 1)
    body = SPHERE + (hexc("#161325") - SPHERE) * (np.clip(facing, 0, 1) ** 3)[..., None] * 0.9
    body = body + (ROSE * 0.6 + WHITE * 0.4) * limb[..., None]
    img = img * (1 - inside[..., None]) + body * inside[..., None]

    # stars: sparse, varied, never on the sphere, fewer inside the glow
    n = int(240 * (W * H) / (2880 * 1800))
    sx, sy = rng.uniform(0, W, n), rng.uniform(0, H, n)
    mag = rng.power(9, n) ** 3
    star = np.zeros((H, W), np.float32)
    ix, iy = sx.astype(int), sy.astype(int)
    np.add.at(star, (iy, ix), mag)
    star = gaussian_filter(star, 0.6 * S) * 8
    glow_mask = np.clip(1 - (np.exp(-out / (300 * k)) * lobe), 0, 1) * outside
    tint = np.stack([np.ones_like(star), np.ones_like(star) * 0.97, np.ones_like(star) * 1.05], -1)
    img += (star * glow_mask)[..., None] * tint * 0.9

    # vignette + grain
    v = ((xx / W - 0.5) ** 2 + (yy / H - 0.5) ** 2)
    img *= (1 - 0.35 * v)[..., None]
    img += rng.normal(0, 0.006, img.shape).astype(np.float32)
    return np.clip(img, 0, 1)


if __name__ == "__main__":
    out = sys.argv[1]
    w, h = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1440, 900)
    img = render(w, h)
    Image.fromarray((img * 255 + 0.5).astype(np.uint8)).save(out)
    print(out, img.shape)
