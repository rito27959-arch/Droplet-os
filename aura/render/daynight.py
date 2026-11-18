#!/usr/bin/env python3
"""Droplet — dynamic wallpaper: night (eclipse) <-> day (garden drawn progressively).

Every element is a layer (RGBA) plus a *reveal map* (the moment 0..1 each pixel appears) and an
optional lifetime (for the luminous pen line that traces each ridge, then fades). At progress p:
    alpha = smoothstep((p - map) / feather) * (1 - smoothstep((p - map - life) / feather))
The shell runs the same layers + maps through one small GPU shader, so this prototype is
exactly the real transition. Played backwards it is the day -> night transition.

  daynight.py OUTDIR [W H]   -> frames, mp4 (night -> day -> night), key stills
"""
import subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, zoom

HERE = Path(__file__).resolve().parent
rng = np.random.default_rng(11)


def ss(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def ease(t):
    return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2


def C(h):
    h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255


def mix(a, b, t):
    return a * (1 - t) + b * t


def shift(a, dx):
    """horizontal shift without wrap-around (clouds enter from outside the screen)."""
    out = np.zeros_like(a)
    if dx > 0: out[:, dx:] = a[:, :-dx]
    elif dx < 0: out[:, :dx] = a[:, -dx:]
    else: out[:] = a
    return out


def fbm1(n, octaves, seed, base=6):
    """1-D fractal noise in -1..1 sampled on n points."""
    r = np.random.default_rng(seed); out = np.zeros(n); amp, tot = 1.0, 0
    for o in range(octaves):
        k = base * 2 ** o
        pts = r.uniform(-1, 1, k + 3)
        out += amp * zoom(pts, (n + 2 * n / k) / (k + 3), order=3)[:n]
        tot += amp; amp *= 0.5
    return out / tot


def fbm2(H, W, scale, octaves, seed):
    r = np.random.default_rng(seed); out = np.zeros((H, W), np.float32); amp, tot = 1.0, 0
    for o in range(octaves):
        gh, gw = max(3, int(H / scale * 2 ** o)), max(3, int(W / scale * 2 ** o))
        g = r.uniform(-1, 1, (gh, gw)).astype(np.float32)
        out += amp * zoom(g, (H / gh, W / gw), order=3)[:H, :W]
        tot += amp; amp *= 0.5
    return out / tot


class Scene:
    def __init__(self, W, H):
        global rng
        rng = np.random.default_rng(11)   # every Scene is the same garden (fond.jpg == end of the film)
        self.W, self.H, self.k = W, H, W / 1440
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        self.X, self.Y = xx / self.k, yy / self.k            # design units 1440 x 900
        self.x1 = self.X[0]
        self.layers = []
        # night = the eclipse of the night cycle (a silhouette in the corona of the hidden sun)
        import planets
        self.night = planets.render_planet("terre", W, H, self.k, R=196, back=1.0)
        self.sun = (1152.0, 270.0)
        self.build()

    def add(self, rgb, a, rev, fe=0.05, life=None):
        if np.ndim(rgb) == 1: rgb = np.broadcast_to(rgb, (self.H, self.W, 3))
        if np.ndim(rev) == 0: rev = np.full((self.H, self.W), rev, np.float32)
        self.layers.append((np.asarray(rgb, np.float32), np.asarray(a, np.float32)[..., None], rev.astype(np.float32), fe, life))

    def disc(self, cx, cy, r, soft=1.0):
        return np.clip((r - np.hypot(self.X - cx, self.Y - cy)) * self.k / soft + .5, 0, 1)

    # ------------------------------------------------------------------ the day
    def build(self):
        X, Y, H, W, k, x1 = self.X, self.Y, self.H, self.W, self.k, self.x1
        sx, sy = self.sun
        dsun = np.hypot(X - sx, Y - sy)

        # sky: deep zenith -> pale horizon haze, warm forward scattering around the sun
        t = np.clip(Y / 600, 0, 1)[..., None]
        sky = mix(C("#2f74d0"), C("#a9d2f5"), t ** 0.85)
        sky = mix(sky, C("#cfe5f7"), np.clip((Y - 380) / 260, 0, 1)[..., None] ** 1.5)
        scat = (np.exp(-(dsun / 520) ** 2) * .55 + np.exp(-(dsun / 200) ** 2) * .35)[..., None]
        sky = mix(sky, C("#fff6e3"), np.clip(scat, 0, 1))
        self.sky = sky
        haze = C("#cfe3f2")
        # light floods the sky from the sun outward
        self.add(sky, np.ones((H, W)), 0.12 + 0.22 * np.clip(dsun / 1450, 0, 1) ** 0.8, fe=0.08)

        # high cirrus veils
        cir = np.clip(fbm2(H, W, 220 * k, 4, 3) * 1.6 + .1, 0, 1) * np.clip((420 - Y) / 300, 0, 1)
        cir = gaussian_filter(cir, (1 * k, 9 * k)) * .28
        self.add(C("#ffffff"), cir, 0.34 + X / 1440 * .12, fe=0.10)

        # clouds: volumetric cumulus (fbm in an envelope), lit from the sun, flat-ish base
        self.pens = []
        order = [0, 2, 3, 1, 4]
        self.anim_from = len(self.layers)          # clouds + birds: animated live afterwards (ambient.py)
        import clouds as CL
        for i in range(len(CL.CLOUDS)):
            dens, col = CL.cloud(X, Y, k, i, 0.0)
            self.draw_cloud(col, dens, start=.40 + order[i] * .055)

        # birds are not drawn here: they fly in live afterwards (ambient), never popping on screen
        self.anim_to = len(self.layers)

        # hills: 5 ridges, aerial perspective (far = hazier, bluer, flatter)
        specs = [  # base y, amplitude, colour near ridge, colour low, haze, start
            (520, 26, "#a7c7d9", "#9dbfcf", .55, .30, 31),
            (575, 34, "#9fcfb0", "#86b997", .38, .36, 32),
            (640, 44, "#86c48f", "#5fa56e", .22, .42, 33),
            (712, 46, "#69b874", "#3f8e52", .10, .48, 34),
            (790, 40, "#4ea95e", "#2d7a40", .0, .54, 35),
        ]
        self.ridge = []
        for base, amp, ctop, cbot, hz, t0, seed in specs:
            yr = base + amp * fbm1(len(x1), 5, seed, base=3)
            self.ridge.append(yr)
            r2 = yr[None, :]
            inside = np.clip((Y - r2) * k + .5, 0, 1)
            depth = np.clip((Y - r2) / 150, 0, 1)[..., None]
            col = mix(C(ctop), C(cbot), depth ** .8)
            # soft relief: large rolling forms lit from the upper right, strongest just below the ridge
            form = gaussian_filter(fbm2(H, W, 260 * k, 3, seed + 50), 6 * k)
            sl = gaussian_filter(np.gradient(yr), 30 * k)[None, :] / k
            near = np.exp(-np.clip(Y - r2, 0, None) / 90)
            col = col * (1 + (np.clip(-sl * 3, -.6, .6) * near + form * .5)[..., None] * .14)
            col = mix(col, C("#fff4d8"), np.exp(-((Y - r2) / 5) ** 2)[..., None] * .16)   # rim light on the ridge
            col = mix(col, haze, hz)
            col = np.clip(col, 0, 1)
            along = x1[None, :] / 1440
            # luminous pen traces the ridge left -> right, then fades
            pen = np.exp(-((Y - r2) * k / 1.0) ** 2) * (1 - hz * .5)
            self.add(C("#ffffff"), pen, t0 + .14 * along, fe=0.02, life=0.18)
            # watercolour wash: fills from the ridge downwards, following the pen
            self.add(col, inside, t0 + .03 + .14 * along + np.clip((Y - r2) / 700, 0, 1) * .10, fe=0.05)

        # trees: soft canopies + cypresses, scaled by distance, with contact shadows
        for li, (layer, n, scale, t0) in enumerate([(2, 7, .55, .56), (3, 6, .85, .60), (4, 3, 1.25, .66)]):
            yr = self.ridge[layer]
            xs = np.sort(rng.uniform(40, 1400, n))
            hz = specs[layer][4]
            for j, tx in enumerate(xs):
                by = float(np.interp(tx, x1, yr)) + 6 * scale + rng.uniform(2, 10) * scale
                s = scale * rng.uniform(.8, 1.2)
                start = t0 + j * .018 + tx / 1440 * .05
                kind = rng.random()
                # contact shadow on the grass (away from the sun)
                sh = np.clip(1 - ((X - tx + 14 * s) / (26 * s)) ** 2 - ((Y - by) / (4 * s)) ** 2, 0, 1) * .35
                self.add(C("#1d4d2a"), gaussian_filter(sh, 1.5 * k), start, fe=0.04)
                trunk_h = (16 if kind < .3 else 26) * s
                trunk = np.clip((2.2 * s - np.abs(X - tx)) * k + .5, 0, 1) * (Y <= by) * (Y >= by - trunk_h)
                self.add(mix(C("#5b4030"), haze, hz), trunk, start + (by - Y) / max(trunk_h, 1) * .03, fe=0.025)
                if kind < .3:  # cypress
                    cy, rx, ry = by - trunk_h * .3 - 36 * s, 9 * s, 38 * s
                    can = np.clip((1 - ((X - tx) / rx) ** 2 - ((Y - cy) / ry) ** 2) * 8 * s, 0, 1)
                else:          # round canopy made of soft lumps
                    cy, cr = by - trunk_h - 16 * s, 22 * s
                    can = np.zeros_like(X)
                    for dx, dy, rr in [(0, 0, 1), (-.6, .25, .7), (.6, .2, .72), (-.25, -.5, .66), (.32, -.45, .62)]:
                        can = np.maximum(can, self.disc(tx + dx * cr, cy + dy * cr, rr * cr, soft=1.3))
                    rx = ry = cr
                    can = np.clip(can * (1 + fbm2(H, W, 7 * k, 1, int(tx)) * .25), 0, 1)
                light = np.clip(((X - tx) / (rx * 2) - (Y - cy) / (ry * 2)) + .45, 0, 1)[..., None]
                col = mix(C("#25633a"), C("#7cc47a"), light ** 1.2)
                col = mix(col, haze, hz)
                d = np.hypot((X - tx) / (rx + 1e-3), (Y - (cy + ry * .5)) / (ry + 1e-3))
                self.add(col, can, start + .035 + np.clip(d, 0, 2) * .03, fe=0.03)

        # meadow flowers on the near hill: bloom in a wave from left to right; front ones in bokeh
        yr = self.ridge[4]
        fl = np.zeros((H, W), np.float32); flc = np.zeros((H, W, 3), np.float32); fr = np.ones((H, W), np.float32)
        pal = [C(c) for c in ("#ff5f8a", "#ff375f", "#ffffff", "#ffd60a", "#ffb3c7", "#c89bff", "#ffffff")]
        for _ in range(520):
            x = rng.uniform(-10, 1450)
            ridge = float(np.interp(x, x1, yr))
            u = rng.random() ** 1.6
            y = ridge + 10 + u * (900 - ridge)
            r = .9 + 3.4 * u
            m = self.disc(x, y, r, soft=1 + 2.5 * u ** 3)
            c = pal[rng.integers(len(pal))] * (.9 + .1 * rng.random())
            sel = m > fl
            flc[sel] = c; fr[sel] = .74 + x / 1440 * .12 + rng.uniform(0, .05)
            fl = np.maximum(fl, m)
        self.add(flc, fl * .95, fr, fe=0.03)
        # foreground grass, slightly out of focus
        blades = np.zeros((H, W), np.float32)
        for _ in range(900):
            x = rng.uniform(0, 1440); h = rng.uniform(14, 46); lean = rng.uniform(-8, 8)
            y0 = rng.uniform(870, 905)
            tt = np.clip((y0 - Y) / h, 0, 1)
            cx = x + lean * tt ** 2
            w = 1.6 * (1 - tt)
            blades = np.maximum(blades, np.clip((w - np.abs(X - cx)) * k + .5, 0, 1) * (Y <= y0) * (Y >= y0 - h))
        blades = gaussian_filter(blades, 1.2 * k)
        self.add(C("#1f6a33"), blades * .9, .80 + X / 1440 * .08, fe=0.04)


    # ------------------------------------------------------------------ the artist's hand
    def stroke_map(self, pts, width=1.3):
        """distance of every pixel to a polyline (design units) and the arc-length position (0..1)
        of the nearest point: the pen reveals the line in that order."""
        from scipy.spatial import cKDTree
        seg = np.diff(pts, axis=0)
        L = np.concatenate([[0], np.cumsum(np.hypot(seg[:, 0], seg[:, 1]))])
        # resample densely
        n = max(2, int(L[-1] * 2))
        u = np.linspace(0, L[-1], n)
        P = np.stack([np.interp(u, L, pts[:, 0]), np.interp(u, L, pts[:, 1])], 1)
        x0, y0 = P.min(0) - 8; x1, y1 = P.max(0) + 8
        sel = (self.X >= x0) & (self.X <= x1) & (self.Y >= y0) & (self.Y <= y1)
        q = np.stack([self.X[sel], self.Y[sel]], 1)
        d, idx = cKDTree(P).query(q)
        dist = np.full(self.X.shape, 1e9, np.float32); sarc = np.zeros(self.X.shape, np.float32)
        dist[sel] = d; sarc[sel] = u[idx] / max(L[-1], 1e-6)
        ink = np.clip((width / 2 - dist) * self.k + .5, 0, 1)
        return ink, sarc, P

    def draw_cloud(self, col, dens, start):
        from skimage.measure import find_contours
        # 1. outline sketched with a graphite pen (two passes, the second slightly off)
        cs = find_contours(dens, .32)
        if not cs:
            return
        c = max(cs, key=len)[:, ::-1] / self.k                       # (x, y) design units
        c = c[::2]
        jit = np.random.default_rng(int(c[0, 0])).normal(0, .6, c.shape)
        span = .085
        for pass_, (off, a, w) in enumerate(((0, .85, 1.4), (1, .45, .9))):
            pts = c + jit * off * 1.6
            ink, sarc, P = self.stroke_map(pts, w)
            t0 = start + pass_ * .02
            self.add(C("#56688a"), ink * a, t0 + span * sarc, fe=.008, life=.20)
            if pass_ == 0:
                self.pens.append((P, t0, span))
        # 2. quick hatching on the shaded side
        ang = .6
        u = self.X * np.cos(ang) + self.Y * np.sin(ang)
        hatch = np.clip(1 - np.abs(np.mod(u, 7) - 3.5) * self.k / .7, 0, 1)
        shade = np.clip((.96 - col.mean(-1)) / .12, 0, 1)
        hm = hatch * (dens > .45) * shade * .6
        vx = (self.X - self.X[dens > .3].min()) / max(1, np.ptp(self.X[dens > .3]))
        self.add(C("#6b7ea0"), hm, start + span + .01 + vx * .05, fe=.01, life=.12)
        # 3. watercolour wash: the cloud fills in from its lit side (upper right)
        sel = dens > .05
        proj = (self.X - self.Y) if True else 0
        pr = (proj - proj[sel].min()) / max(1, np.ptp(proj[sel]))
        self.add(col, dens, start + span + .05 + (1 - pr) * .06, fe=.04)

    def draw_birds(self):
        r = np.random.default_rng(4)
        for j, (bx, by, sz) in enumerate([(520, 240, 9), (548, 252, 7), (570, 236, 6), (1010, 160, 7)]):
            # two arcs: the gull "v"
            t = np.linspace(0, 1, 30)
            left = np.stack([bx - sz + sz * t, by - sz * .55 * np.sin(np.pi * (1 - t) * .9) + sz * .25 * t], 1)
            right = np.stack([bx + sz * t, by - sz * .55 * np.sin(np.pi * t * .9) + sz * .25 * (1 - t)], 1)
            pts = np.concatenate([left, right[1:]])
            ink, sarc, P = self.stroke_map(pts, 1.5)
            t0 = .70 + j * .025
            self.add(C("#33415c"), ink * .9, t0 + .03 * sarc, fe=.006)
            self.pens.append((P, t0, .03))

    # ------------------------------------------------------------------ frame
    def frame(self, p, drift=0.0):
        """p = 0 night (eclipse) ... 1 day (garden)."""
        X, Y, k = self.X, self.Y, self.k
        out = self.night.copy()
        sx, sy = self.sun
        dsun = np.hypot(X - sx, Y - sy)
        for rgb, a, rev, fe, life in self.layers:
            v = ss((p - rev) / fe)
            if life is not None:
                v = v * (1 - ss((p - rev - life) / fe))
            out = mix(out, rgb, v[..., None] * a)
        # the sun, behind the moon: white-hot core and layered bloom (brighter while it emerges)
        sp = ss((p - .04) / .10)
        core = self.disc(sx, sy, 46, soft=1.2)
        burst = 1 + 1.6 * (1 - ss((p - .14) / .16))
        bloom = (np.exp(-(dsun / 70) ** 2) * .9 + np.exp(-(dsun / 160) ** 2) * .45 * burst) * sp
        sun = mix(C("#fff1c4"), C("#fffef8"), core[..., None])
        # where the moon was, light pours in (no dark "hole" once the moon has moved)
        inner = self.disc(sx, sy, 200, soft=18) * sp * (1 - ss((p - .15) / .08))
        glowc = mix(C("#ffd2b8"), C("#fff6e4"), np.exp(-(dsun / 120) ** 2)[..., None])
        out = mix(out, glowc, inner[..., None] * .96)
        out = mix(out, sun, np.clip(np.maximum(core * sp, bloom), 0, 1)[..., None])
        # the moon slides off the sun, up and to the right, and leaves the sky
        mv = ss((p - .05) / .30)
        mx, my = sx + 620 * mv, sy - 560 * mv
        moon = self.disc(mx, my, 196)
        # diamond ring: the first point of sunlight on the moon's trailing edge
        ang = np.arctan2(sy - my, sx - mx) if mv > 0 else np.pi * .75
        dx_, dy_ = mx + 196 * np.cos(ang), my + 196 * np.sin(ang)
        dd = np.hypot(X - dx_, Y - dy_)
        ring = ss(p / .06) * (1 - ss((p - .16) / .08))
        spark = np.clip(np.exp(-(dd / 10) ** 2) * 1.4 + np.exp(-(dd / 46) ** 2) * .55, 0, 1) * ring
        out = mix(out, C("#05070c"), moon[..., None])
        out = mix(out, C("#fffaf0"), spark[..., None])
        # the pen tip: a small bright point where the artist is drawing
        for P, t0, span in self.pens:
            if t0 <= p <= t0 + span:
                q = (p - t0) / span
                px_, py_ = P[min(len(P) - 1, int(q * (len(P) - 1)))]
                d = np.hypot(X - px_, Y - py_)
                tip = np.clip(np.exp(-(d / 2.2) ** 2) * 1.2 + np.exp(-(d / 9) ** 2) * .35, 0, 1)
                out = mix(out, C("#ffffff"), tip[..., None])
        return np.clip(out, 0, 1)


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    W, H = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1440, 900)
    sc = Scene(W, H)
    fps, secs = 30, 3.4
    n = int(fps * secs)
    seq = [0.0] * fps + [ease(i / (n - 1)) for i in range(n)] + [1.0] * int(fps * 1.5)
    seq += [1 - ease(i / (n - 1)) for i in range(n)] + [0.0] * fps
    fdir = out / "frames"; fdir.mkdir(exist_ok=True)
    for i, p in enumerate(seq):
        if (fdir / f"{i:04d}.png").exists():
            continue   # resumable
        Image.fromarray((sc.frame(p, drift=i * .3) * 255 + .5).astype(np.uint8)).save(fdir / f"{i:04d}.png")
    for name, p in [("1-nuit", 0.0), ("2-anneau", 0.12), ("3-aube", 0.3), ("4-dessin", 0.5), ("5-jardin", 0.7), ("6-jour", 1.0)]:
        Image.fromarray((sc.frame(p) * 255 + .5).astype(np.uint8)).save(out / f"cle-{name}.png")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(fdir / "%04d.png"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    str(out / "transition-nuit-jour.mp4")], check=True)
    print(out / "transition-nuit-jour.mp4", len(seq))


if __name__ == "__main__":
    main()
