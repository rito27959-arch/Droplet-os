"""Droplet — the garden's cumulus clouds, shared by the transition (drawn at t = 0), the live
ambient animation and the sprites the shell animates.

cloud(X, Y, k, i, t, cx=None) -> (density HxW, colour HxWx3) on any pixel grid given in design
points (X, Y). t is time in seconds (the shape billows slowly), cx overrides the drift position.
"""
import math
import numpy as np
from scipy.ndimage import gaussian_filter
from planets import Noise3

SUN = (1152.0, 270.0)
# x, y, half-width, half-height, wind speed (pt/s)
CLOUDS = [(300, 190, 190, 62, 7.5), (700, 120, 120, 38, 4.0), (880, 335, 150, 46, 9.5),
          (1380, 175, 120, 36, 5.5), (90, 360, 110, 30, 11.0)]
_noise = Noise3(17, g=24)
_r = np.random.default_rng(5)
TOWERS = [[(_r.uniform(-.6, .6), _r.uniform(.32, .5), _r.uniform(.1, .7)) for _ in range(5)] for _ in CLOUDS]


def _C(h):
    h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255


def _shift(a, dy, dx):
    o = np.zeros_like(a); h, w = a.shape
    if abs(dy) >= h or abs(dx) >= w:
        return o
    ys, yd = (slice(dy, h), slice(0, h - dy)) if dy >= 0 else (slice(0, h + dy), slice(-dy, h))
    xs, xd = (slice(dx, w), slice(0, w - dx)) if dx >= 0 else (slice(0, w + dx), slice(-dx, w))
    o[ys, xs] = a[yd, xd]
    return o


def cloud(X, Y, k, i, t=0.0, cx=None):
    cx0, cy, rw, rh, _ = CLOUDS[i]
    cx = cx0 if cx is None else cx
    env = 1 - ((X - cx) / rw) ** 2 - ((Y - cy) / (rh * .7)) ** 2 * np.where(Y > cy, 3.0, 1.0)
    for j, (dx, br, dy) in enumerate(TOWERS[i]):
        br = br * (1 + .08 * math.sin(t * .35 + j * 1.7 + i))      # towers swell and settle
        bx, by = cx + dx * rw, cy - dy * rh
        env = np.maximum(env, np.where(Y < cy + rh * .35,
                                       1 - ((X - bx) / (br * rw)) ** 2 - ((Y - by) / (br * rw * .78)) ** 2, -1))
    n = _noise((X - cx) / 60, (Y - cy) / 60, np.full_like(X, t * .06 + i * 3.1), 4, 1.0)
    dens = np.clip((env * 1.4 + n * 0.9) * 1.8, 0, 1)
    dens = gaussian_filter(dens, 1.6 * k)
    sx, sy = SUN
    step_y, step_x = -5 * k, 6 * k * np.sign(sx - cx)
    depth = sum(_shift(dens, int(round(-q * step_y)), int(round(-q * step_x))) for q in range(1, 9))
    light = np.exp(-depth * .32) * .85 + .15
    col = _C("#9fb2cb")[None, None] * (1 - light[..., None]) + _C("#ffffff") * light[..., None]
    dsun = np.hypot(X - sx, Y - sy)
    g = (np.exp(-(dsun / 500) ** 2) * light)[..., None] * .5
    col = col * (1 - g) + _C("#fff6e6") * g
    return dens * .97, col
