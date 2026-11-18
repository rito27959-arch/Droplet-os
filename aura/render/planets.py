#!/usr/bin/env python3
"""Droplet — night wallpapers: the eclipse, then the eight planets of the solar system.

Each planet is a procedural sphere (3-D noise sampled on the surface, so no seams), lit from the
side by a sun hidden behind the upper left, with its atmosphere glowing on the rim, so it keeps
the eclipse's signature: a dark body outlined by light. Saturn has its rings (with the planet's
shadow on them), Uranus its faint vertical rings.

  planets.py OUTDIR [W H]  -> planete-<nom>.png + planches
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates

rng0 = np.random.default_rng(3)


def C(h):
    h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255


def mix(a, b, t):
    return a * (1 - t) + b * t


def ss(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


class Noise3:
    """trilinear value noise on a periodic 3-D grid, fBm."""
    def __init__(self, seed, g=32):
        self.g = g
        self.v = np.random.default_rng(seed).random((g, g, g)).astype(np.float32)

    def __call__(self, x, y, z, octaves=5, freq=2.0, lac=2.0, gain=0.5):
        out = np.zeros_like(x); amp = 1.0; tot = 0
        for o in range(octaves):
            out += amp * self.one(x * freq, y * freq, z * freq); tot += amp
            freq *= lac; amp *= gain
        return out / tot

    def one(self, x, y, z):
        g = self.g
        x = x + 100.0; y = y + 100.0; z = z + 100.0
        coords = np.stack([np.mod(z, g), np.mod(y, g), np.mod(x, g)])
        return map_coordinates(self.v, coords.reshape(3, -1), order=1, mode="grid-wrap").reshape(x.shape) * 2 - 1


# ------------------------------------------------------------------ sky
def night_sky(W, H, k, seed=5):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) / k
    t = np.clip(yy / 900, 0, 1)[..., None]
    sky = mix(C("#070914"), C("#151338"), t ** 1.4)
    # faint violet nebula low right + blue haze top left (the family colours)
    neb = np.exp(-(((xx - 1150) / 700) ** 2 + ((yy - 820) / 260) ** 2))[..., None]
    sky = mix(sky, C("#3a1458"), neb * .45)
    haze = np.exp(-(((xx - 120) / 600) ** 2 + ((yy - 60) / 360) ** 2))[..., None]
    sky = mix(sky, C("#14205a"), haze * .35)
    r = np.random.default_rng(seed)
    stars = np.zeros((H, W), np.float32)
    n = int(1400 * (W * H) / (1440 * 900 * k * k) * k * k)
    ys, xs = r.integers(0, H, n), r.integers(0, W, n)
    stars[ys, xs] = r.random(n) ** 3 * 1.4
    stars = gaussian_filter(stars, .55 * k) * 2.2
    sky = sky + np.clip(stars, 0, 1)[..., None] * C("#e8ecff")
    return np.clip(sky, 0, 1)


# ------------------------------------------------------------------ surfaces (n = surface normal, view space)
def surface(name, nx, ny, nz, N):
    # body-fixed coordinates: tilt the planet a little so features are not axis-aligned
    lat = ny                                   # -1 (north, top) .. 1
    if name == "mercure":
        h = N(nx, ny, nz, 6, 2.5)
        col = mix(C("#5d5751"), C("#a59d93"), ss(h * 1.6 + .5)[..., None])
        # craters: rings of brightness at random spots
        r = np.random.default_rng(1)
        for _ in range(70):
            c = r.normal(size=3); c /= np.linalg.norm(c)
            if c[2] < 0: c[2] = -c[2]
            rad = r.uniform(.03, .14)
            d = np.sqrt((nx - c[0]) ** 2 + (ny - c[1]) ** 2 + (nz - c[2]) ** 2)
            bowl = ss(1 - d / rad)
            rim = np.exp(-((d - rad) / (rad * .18)) ** 2)
            col = col * (1 - bowl[..., None] * .22) + rim[..., None] * .16
        return col, 0.0, None
    if name == "venus":
        sw = N(nx * 1.2, ny * 3.0, nz * 1.2, 5, 1.6)
        col = mix(C("#c9a66b"), C("#f3e2b6"), ss(sw * 1.4 + .55)[..., None])
        return col, .85, C("#ffd9a0")
    if name == "terre":
        h = N(nx, ny, nz, 7, 1.6) + N(nx * 6, ny * 6, nz * 6, 3, 2) * .12
        land = ss((h - .04) * 14)
        ocean = mix(C("#061d45"), C("#0f3f80"), ss(N(nx * 2, ny * 2, nz * 2, 3, 2) * 1.2 + .5)[..., None])
        ocean = mix(ocean, C("#1d6aa8"), ss((h + .02) * 30)[..., None] * (1 - land[..., None]) * .6)   # shallows
        veg = mix(C("#2f5a2a"), C("#a08458"), ss(N(nx * 3, ny * 3, nz * 3, 4, 2) * 1.8 + .35 + np.abs(lat) * .25 - .2)[..., None])
        col = mix(ocean, veg, land[..., None])
        ice = ss((np.abs(lat) - .84) * 16 + N(nx * 4, ny * 4, nz * 4, 2, 2) * 2)
        col = mix(col, C("#eef4fa"), ice[..., None])
        cl = N(nx * 1.6 + 5, ny * 3.0, nz * 1.6, 7, 2.6)
        cl = ss((cl - .02) * 4.5) * .9 + ss((N(nx * 5, ny * 9, nz * 5, 3, 2) - .1) * 3) * .25
        col = mix(col, C("#f6f8fb"), np.clip(cl, 0, 1)[..., None] * .9)
        return col, .7, C("#6fb6ff"), land * (1 - np.clip(cl, 0, 1)), "lights"
    if name == "mars":
        h = N(nx, ny, nz, 6, 2.2)
        col = mix(C("#7a3218"), C("#d47744"), ss(h * 1.8 + .55)[..., None])
        col = mix(col, C("#4a2416"), ss(-h * 3 - .2)[..., None] * .6)
        cap = ss((-lat - .86) * 18 + N(nx * 5, ny * 5, nz * 5, 2, 2) * 2)
        col = mix(col, C("#f2ece6"), cap[..., None])
        return col, .25, C("#ffb08a")
    if name == "jupiter":
        turb = N(nx * 2.2, ny * 1.2, nz * 2.2, 6, 2.6)
        b = lat * 13 + turb * 1.1
        fine = np.sin(lat * 47 + turb * 4) * .5 + .5
        bands = np.sin(b) * .5 + .5
        col = mix(C("#9b6b4a"), C("#f1e3c8"), ss(bands * 1.2 - .1)[..., None])
        col = mix(col, C("#c49a72"), fine[..., None] * .25)
        col = mix(col, C("#6e4a35"), ss((np.sin(lat * 6.5 + .9) - .75) * 4)[..., None] * .35)
        gx, gy = nx + .2, (ny - .36) * 2.1
        dd = np.sqrt((gx / .2) ** 2 + (gy / .2) ** 2)
        col = mix(col, C("#c25a35"), ss(1 - dd)[..., None] * .8)
        col = mix(col, C("#f2dcc0"), np.exp(-((dd - 1.05) / .12) ** 2)[..., None] * .5)
        return col, .5, C("#ffe0b8")
    if name == "saturne":
        turb = N(nx * 1.5, ny * 1.5, nz * 1.5, 4, 2.0) * .05
        b = lat * 11 + turb * 8
        col = mix(C("#c7a774"), C("#f0e0b8"), (np.sin(b) * .5 + .5)[..., None])
        return col, .45, C("#ffe7b0")
    if name == "uranus":
        col = mix(C("#8fd0dc"), C("#c4eef2"), ss(-lat * .8 + .4 + N(nx, ny, nz, 3, 1.5) * .3)[..., None])
        return col, .7, C("#b9f3ff")
    if name == "neptune":
        sw = N(nx * 1.2, ny * 4, nz * 1.2, 5, 1.8)
        col = mix(C("#1f3a9e"), C("#4a76e0"), ss(sw * 1.6 + .5 + np.sin(lat * 8) * .15)[..., None])
        gx, gy = nx - .15, (ny + .22) * 1.8
        col = mix(col, C("#14246a"), ss(1 - np.sqrt((gx / .13) ** 2 + (gy / .13) ** 2))[..., None] * .8)
        return col, .8, C("#7fa8ff")
    raise ValueError(name)


PLANETS = [("mercure", "Mercure", .55), ("venus", "Vénus", .92), ("terre", "Terre", 1.0), ("mars", "Mars", .7),
           ("jupiter", "Jupiter", 1.18), ("saturne", "Saturne", 1.0), ("uranus", "Uranus", .95), ("neptune", "Neptune", .95)]


def render_planet(name, W, H, k, cx=1152, cy=270, R=196, sky=None, light=(-0.85, -0.40, -0.06), back=0.0):
    """returns the frame (HxWx3). R in design points (scaled by the planet's display size)."""
    img = night_sky(W, H, k) if sky is None else sky.copy()
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32) / k
    # back: 0 = lit from the side ... 1 = the sun exactly behind (the eclipse: a silhouette in its corona)
    L = np.array(light, np.float32); L /= np.linalg.norm(L)
    L = (1 - back) * L + back * np.array([-.05, -.04, -1.0], np.float32); L /= np.linalg.norm(L)
    dx, dy = (xx - cx) / R, (yy - cy) / R
    r2 = dx * dx + dy * dy
    inside = np.clip((1 - np.sqrt(r2)) * R * k + .5, 0, 1)
    nz = np.sqrt(np.clip(1 - r2, 0, 1))
    nx, ny = dx, dy
    # body tilt (rotate about the view axis)
    tilt = {"saturne": -.42, "uranus": 1.35, "jupiter": .05, "terre": -.4}.get(name, .2)
    ct, st = np.cos(tilt), np.sin(tilt)
    bx, by = nx * ct - ny * st, nx * st + ny * ct
    N = Noise3({"mercure": 1, "venus": 2, "terre": 3, "mars": 4, "jupiter": 5, "saturne": 6, "uranus": 7, "neptune": 8}[name])
    res = surface(name, bx, by, nz, N)
    col, atm, atmc = res[:3]
    ndl = nx * L[0] + ny * L[1] + nz * L[2]
    diffuse = np.clip(ndl, 0, 1)
    term = ss((ndl + .08) / .35)                         # soft terminator
    lit = col * (diffuse * .95 + .03)[..., None] * term[..., None] + col * .012
    # limb darkening on gas giants / atmosphere scattering on the lit limb
    if atm:
        fres = (1 - nz) ** 2.2
        lit = lit + atmc * (fres * atm * np.clip(ndl + .35, 0, 1) * .55)[..., None]
    if len(res) > 3:  # Earth: city lights on the night side
        land = res[3]
        city = np.clip(N(bx * 30, by * 30, nz * 30, 2, 1) * 3 - 1.4, 0, 1) * land * (1 - ss((ndl + .1) / .2))
        lit = lit + C("#ffb35a") * (city * .9 * (1 - back) ** 2)[..., None]
    planet = lit
    # rim light: the sun behind the body outlines it (the eclipse signature)
    edge = np.sqrt(r2)
    behind = np.clip(-(dx * L[0] + dy * L[1]) / (np.sqrt(r2) + 1e-6) * -1, 0, 1)   # toward the light
    halo_c = atmc if atmc is not None else C("#ffffff")
    rim = np.exp(-((edge - 1) * R / 3.0) ** 2) * (.35 + .65 * behind)
    glow = np.exp(-np.clip(edge - 1, 0, None) * R / (14 + 30 * atm)) * (edge > 1) * (.15 + .85 * behind) * (.35 + atm)
    # rings behind the planet (Saturn, Uranus): drawn in two halves around the globe
    ring_front = None
    if name in ("saturne", "uranus"):
        ring_back, ring_front, rshadow = rings(name, xx, yy, cx, cy, R, tilt, L, nz, inside, dx, dy)
        planet = planet * (1 - rshadow[..., None] * .75)
    img = img + halo_c * (glow * .55 * (1 - back))[..., None]
    # corona of the hidden sun (the Droplet eclipse), strongest when the sun is right behind
    if back > 0:
        out_ = np.clip(edge - 1, 0, None) * R
        cor = (np.exp(-out_ / 6) * 1.3 + np.exp(-out_ / 24) * .75 + np.exp(-out_ / 110) * .45) * (edge > 1)
        ang = np.arctan2(dy, dx)
        cor = cor * (1 + .25 * np.sin(ang * 7 + 1) * np.exp(-out_ / 40))
        corc = mix(C("#b04dff"), C("#ff5fa0"), np.exp(-out_ / 14)[..., None])
        corc = mix(corc, C("#fff0f6"), np.exp(-out_ / 3)[..., None])
        img = img + corc * (cor * back ** 1.5)[..., None]
        if ring_front is not None:
            ring_back[..., 3] *= (1 - back) ** 2; ring_front[..., 3] *= (1 - back) ** 2
    if ring_front is not None:   # far half of the rings, then the globe hides what is behind it
        img = mix(img, ring_back[..., :3], ring_back[..., 3:4])
    img = mix(img, planet, inside[..., None])
    img = img + halo_c * (rim * inside * .0 + rim * .9 * (1 - inside * .6))[..., None]
    if ring_front is not None:
        img = mix(img, ring_front[..., :3], ring_front[..., 3:4])
    return np.clip(img, 0, 1)


def rings(name, xx, yy, cx, cy, R, tilt, L, nz, inside, dx, dy):
    # ring plane: an ellipse (inclined disc) rotated by the body tilt
    incl = .28 if name == "saturne" else .22
    ct, st = np.cos(tilt), np.sin(tilt)
    u = ((xx - cx) * ct + (yy - cy) * st) / R          # along the ring's major axis
    v = (-(xx - cx) * st + (yy - cy) * ct) / R
    rr = np.sqrt(u ** 2 + (v / incl) ** 2)              # radius in the ring plane (planet radii)
    if name == "saturne":
        prof = (ss((rr - 1.24) * 40) * (1 - ss((rr - 2.27) * 40)))
        r_ = np.random.default_rng(9)
        ripple = np.interp(rr, np.linspace(1.2, 2.3, 400), gaussian_filter(r_.random(400), 1.2))
        dens = (.45 + .55 * ripple) * prof
        dens *= 1 - np.exp(-((rr - 1.95) / .03) ** 2) * .92                # Cassini division
        dens *= np.where(rr < 1.53, .35, 1.0)                               # faint C ring
        dens *= 1 - np.exp(-((rr - 2.2) / .008) ** 2) * .7                  # Encke gap
        col = mix(C("#8d7558"), C("#f2e4c4"), ss((rr - 1.3) * 1.4)[..., None])
        alpha = np.clip(dens * .95, 0, 1)
    else:
        prof = sum(np.exp(-((rr - r0) / .012) ** 2) for r0 in (1.6, 1.68, 1.75, 1.95))
        col = np.broadcast_to(C("#cfe9f0"), xx.shape + (3,))
        alpha = np.clip(prof * .35, 0, 1)
    # light on the rings (lit from the same side) + the planet's shadow across them
    lit = .9
    shadow_side = (dx * L[0] + dy * L[1]) < 0
    perp = np.abs(dx * L[1] - dy * L[0])
    pshadow = (perp < 1.0) & shadow_side & (rr > 1) & (v < 0)          # only the far half is behind the globe
    col = col * lit * np.where(pshadow, .18, 1.0)[..., None]
    front = v > 0                                                        # near half passes in front of the globe
    back = np.dstack([col, alpha * ~front])
    fr = np.dstack([col, alpha * front])
    # ring shadow on the globe: a band displaced toward the light
    band = np.sqrt((u - L[0] * .3) ** 2 + ((v - L[1] * .3) / incl) ** 2)
    rshadow = (ss((band - 1.24) * 30) * (1 - ss((band - 2.27) * 30))) * inside * .45 * (v < 0)
    return back, fr, rshadow


def main():
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    W, H = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1440, 900)
    k = W / 1440
    sky = night_sky(W, H, k)
    tiles = []
    for name, label, scale in PLANETS:
        R = 196 * scale if name != "saturne" else 150
        img = render_planet(name, W, H, k, R=R, sky=sky)
        Image.fromarray((img * 255 + .5).astype(np.uint8)).save(out / f"planete-{name}.png")
        tiles.append(Image.fromarray((img * 255 + .5).astype(np.uint8)).resize((480, 300), Image.LANCZOS))
        print(name)
    sheet = Image.new("RGB", (480 * 4, 300 * 2))
    for i, t in enumerate(tiles):
        sheet.paste(t, ((i % 4) * 480, (i // 4) * 300))
    sheet.save(out / "planche-planetes.jpg", quality=92)





# ------------------------------------------------------------------ the night cycle (prototype video)
def cycle_frames(fps=24):
    """eclipse -> Mercure -> ... -> Neptune -> eclipse. Each body is reached through the eclipse."""
    seq = [("eclipse", 196, 1.0)] * int(fps * 1.0)
    bodies = [(n, 196 * sc if n != "saturne" else 150) for n, _, sc in PLANETS]
    prev_R = 196
    def ease(t): return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2
    for name, R in bodies + [("eclipse", 196)]:
        for i in range(int(fps * .7)):                       # silhouette changes size
            t = ease(i / (fps * .7 - 1))
            seq.append((name, prev_R + (R - prev_R) * t, 1.0))
        if name == "eclipse":
            seq += [(name, R, 1.0)] * fps
            break
        for i in range(int(fps * 1.3)):                      # the sun slides aside: the planet appears
            seq.append((name, R, 1 - ease(i / (fps * 1.3 - 1))))
        seq += [(name, R, 0.0)] * int(fps * 1.6)
        for i in range(int(fps * 1.2)):                      # back into eclipse
            seq.append((name, R, ease(i / (fps * 1.2 - 1))))
        prev_R = R
    return seq


def _render_one(args):
    i, (name, R, back), W, H, out = args
    k = W / 1440
    sky = _SKY.get((W, H))
    if sky is None:
        sky = _SKY[(W, H)] = night_sky(W, H, k)
    img = render_planet("terre" if name == "eclipse" else name, W, H, k, R=R, sky=sky, back=back)
    Image.fromarray((img * 255 + .5).astype(np.uint8)).save(f"{out}/{i:04d}.png")


_SKY = {}


def video(out, W=960, H=600, fps=20, procs=2):
    import multiprocessing as mp, subprocess
    out = Path(out); fr = out / "cycle"; fr.mkdir(parents=True, exist_ok=True)
    seq = cycle_frames(fps)
    jobs = [(i, s, W, H, str(fr)) for i, s in enumerate(seq) if not (fr / f"{i:04d}.png").exists()]
    with mp.Pool(procs) as pool:
        pool.map(_render_one, jobs, chunksize=4)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(fr / "%04d.png"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
                    str(out / "cycle-planetes.mp4")], check=True)
    return len(seq)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "video":
        print(video(sys.argv[2]))
    else:
        main()
