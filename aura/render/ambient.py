#!/usr/bin/env python3
"""Droplet — the day garden, alive: clouds drift and billow, birds fly, flap and glide.

After the transition has drawn the scene, the shell keeps it moving with these rules:
  * clouds: each one drifts with the wind, faster when lower/larger (parallax), and its shape
    evolves slowly (3-D noise with time as the third axis); light and self-shadow follow the sun;
    a cloud leaving one side comes back on the other after a while
  * birds: a small flock crosses the sky on gentle curves; wings beat (about 3 Hz), then they glide
    for a moment, each bird a little out of phase with its neighbours
  ambient.py OUTDIR [W H SECONDS]
"""
import math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter

import daynight as dn
import clouds as CL
from planets import Noise3

C, mix, ss = dn.C, dn.mix, dn.ss

CLOUDS = [  # x, y, half-width, half-height, wind speed (pt/s), seed
    (300, 190, 190, 62, 7.5, 0), (700, 120, 120, 38, 4.0, 1), (880, 335, 150, 46, 9.5, 2),
    (1380, 175, 120, 36, 5.5, 3), (90, 360, 110, 30, 11.0, 4),
]


class Ambient:
    def __init__(self, W, H):
        self.sc = dn.Scene(W, H)
        sc = self.sc
        self.W, self.H, self.k = W, H, sc.k
        # static background = the finished day scene without clouds and birds
        keep = sc.layers[:sc.anim_from] + sc.layers[sc.anim_to:]
        sc.layers, sc.pens = keep, []
        self.bg = sc.frame(1.0)
        self.noise = Noise3(17, g=24)
        self.sun = sc.sun
        r = np.random.default_rng(5)
        self.towers = [[(r.uniform(-.6, .6), r.uniform(.32, .5), r.uniform(.1, .7)) for _ in range(5)] for _ in CLOUDS]

    # ------------------------------------------------------------ clouds
    def cloud(self, out, i, t):
        cx0, cy, rw, rh, v = CL.CLOUDS[i]
        k = self.k
        span = 1440 + 2 * rw + 200
        cx = (cx0 + v * t + rw + 100) % span - rw - 100            # wraps around off-screen
        x0, x1 = int(max(0, (cx - rw * 1.25) * k)), int(min(self.W, (cx + rw * 1.25) * k))
        y0, y1 = int(max(0, (cy - rh * 2.2) * k)), int(min(self.H, (cy + rh * 1.2) * k))
        if x1 <= x0 or y1 <= y0:
            return out
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32) / k
        dens, col = CL.cloud(xx, yy, k, i, t, cx)
        out[y0:y1, x0:x1] = mix(out[y0:y1, x0:x1], col, dens[..., None])
        return out

    # flocks: (altitude, distance 0 near..1 far, speed pt/s, members, start offset s, rest s)
    FLOCKS = [(232, .25, 58, 5, 0.0, 6.0), (150, .7, 36, 3, 9.0, 10.0)]
    MEMBERS = [(0, 0, 12, 0.0), (30, 15, 10, .31), (56, -5, 8.5, .62), (82, 20, 9, .17), (-28, 23, 7.5, .85)]

    def birds(self, out, t):
        """Each flock enters beyond the left edge and leaves beyond the right edge (never pops on
        screen), then rests off-screen. Far birds are smaller, paler and bluer (aerial perspective)."""
        k, S4 = self.k, 4
        sc = S4 / 2 * k
        for alt, dist, speed, n, t0, rest in self.FLOCKS:
            span = 1440 + 2 * 180                       # from x = -180 to x = 1620 (leader)
            flight = span / speed
            tt = (t - t0) % (flight + rest)
            if tt > flight:
                continue                                 # resting, out of sight
            layer = Image.new("L", (self.W * S4 // 2, self.H * S4 // 2), 0)
            d = ImageDraw.Draw(layer)
            scale = 1.0 - .45 * dist
            lead_x = -180 + tt * speed
            base_y = alt + 22 * math.sin(tt * .25) - tt * 1.2      # slow climb with gentle swell
            members = self.MEMBERS[:n]
            for j, (ox, oy, sz, ph) in enumerate(members):
                sz *= scale
                x = lead_x - ox * 1.1 * scale
                y = base_y + oy * scale + 4 * scale * math.sin(tt * 1.1 + j)
                cyc = (tt * .22 + ph) % 1
                flap = 1.0 if cyc < .65 else ss((.8 - cyc) / .15)
                wing = math.sin(2 * math.pi * 3.0 * tt + ph * 6.28) * flap + (1 - flap) * .25
                bank = math.sin(tt * .5 + j) * .08
                pts = []
                for side in (-1, 1):
                    tip = (x + side * sz, y - sz * .62 * wing + side * sz * bank)
                    mid = (x + side * sz * .5, y - sz * .38 * wing - sz * .12)
                    pts.append([tip, mid, (x, y + sz * .08)])
                line = pts[0] + pts[1][::-1]
                d.line([(px * sc, py * sc) for px, py in line], fill=255,
                       width=max(1, int((1.7 - .6 * dist) * sc)), joint="curve")
            ink = np.asarray(layer.resize((self.W, self.H), Image.LANCZOS), np.float32) / 255
            # colour: a silhouette seen through air -> mixed with the sky behind it
            yy = int(np.clip(base_y * k, 0, self.H - 1)); xx = int(np.clip(lead_x * k, 0, self.W - 1))
            sky = self.bg[yy, xx]
            col = mix(C("#27324a"), sky, .25 + .45 * dist)
            out = mix(out, col, ink[..., None] * (.92 - .25 * dist))
        return out

    def frame(self, t):
        out = self.bg.copy()
        for i in range(len(CL.CLOUDS)):
            out = self.cloud(out, i, t)
        return np.clip(self.birds(out, t), 0, 1)


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    W, H, secs = (int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (1280, 800, 16)
    am = Ambient(W, H)
    fps = 24
    fr = out / "ambient"; fr.mkdir(exist_ok=True)
    for i in range(int(secs * fps)):
        p = fr / f"{i:04d}.png"
        if not p.exists():
            Image.fromarray((am.frame(i / fps) * 255 + .5).astype(np.uint8)).save(p)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(fr / "%04d.png"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    str(out / "jardin-vivant.mp4")], check=True)
    print(out / "jardin-vivant.mp4")


if __name__ == "__main__":
    main()
