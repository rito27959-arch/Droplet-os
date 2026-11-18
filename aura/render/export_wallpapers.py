#!/usr/bin/env python3
"""Exports everything the shell's live wallpaper needs (share/droplet/wallpapers/):

  jour/fond.jpg                 the garden without clouds (clouds and birds are animated live)
  jour/nuage-<i>-<a|b|c>.png    cloud sprites, three moments of each cloud's slow billowing
  jour/nuages.json              where each sprite sits (design points) and its wind speed
  transition/nuit-jour.mp4      eclipse -> garden (the artist draws it), and jour-nuit.mp4 (reverse)
  nuit/<corps>.jpg              eclipse and the eight planets, lit
  nuit/<planete>-entree.mp4     from the eclipse to the lit planet (played backwards to leave it)

  export_wallpapers.py OUTDIR [W H]
"""
import json, multiprocessing as mp, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image

import ambient, clouds as CL, daynight as dn, planets as P

FPS = 24


def save(img, path, q=92):
    Image.fromarray((np.clip(img, 0, 1) * 255 + .5).astype(np.uint8)).save(path, quality=q)


def encode(frames_dir, out, reverse=False):
    vf = ["-vf", "reverse"] if reverse else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{frames_dir}/%04d.png", *vf,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(out)], check=True)


def ease(t):
    return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2


# ---------------------------------------------------------------- night
def _planet_frame(args):
    name, R0, R, i, n_morph, n_rev, W, H, d = args
    k = W / 1440
    if i < n_morph:
        t = ease(i / (n_morph - 1)); r = R0 + (R - R0) * t; back = 1.0
    else:
        r = R; back = 1 - ease((i - n_morph) / (n_rev - 1))
    img = P.render_planet(name, W, H, k, R=r, back=back)
    save(img, f"{d}/{i:04d}.png")


def night(out, W, H):
    nd = out / "nuit"; nd.mkdir(parents=True, exist_ok=True)
    k = W / 1440
    save(P.render_planet("terre", W, H, k, R=196, back=1.0), nd / "eclipse.jpg")
    jobs = []
    for name, _, sc in P.PLANETS:
        R = 196 * sc if name != "saturne" else 150
        save(P.render_planet(name, W, H, k, R=R), nd / f"{name}.jpg")
        fr = out / "_frames" / name; fr.mkdir(parents=True, exist_ok=True)
        n_morph, n_rev = int(FPS * .7), int(FPS * 1.4)
        jobs += [(name, 196, R, i, n_morph, n_rev, W, H, str(fr)) for i in range(n_morph + n_rev)
                 if not (fr / f"{i:04d}.png").exists()]
    with mp.Pool(2) as pool:
        pool.map(_planet_frame, jobs, chunksize=2)
    for name, _, _ in P.PLANETS:
        encode(out / "_frames" / name, nd / f"{name}-entree.mp4")
        encode(out / "_frames" / name, nd / f"{name}-sortie.mp4", reverse=True)
    print("nuit ok")


# ---------------------------------------------------------------- day
def day(out, W, H):
    jd = out / "jour"; jd.mkdir(parents=True, exist_ok=True)
    am = ambient.Ambient(W, H)
    k = am.k
    save(am.bg, jd / "fond.jpg", 94)
    meta = []
    for i, (cx, cy, rw, rh, v) in enumerate(CL.CLOUDS):
        x0, x1 = cx - rw * 1.3, cx + rw * 1.3
        y0, y1 = cy - rh * 2.4, cy + rh * 1.3
        gw, gh = int((x1 - x0) * k), int((y1 - y0) * k)
        yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32) / k
        xx += x0; yy += y0
        for tag, t in (("a", 0.0), ("b", 25.0), ("c", 50.0)):
            dens, col = CL.cloud(xx, yy, k, i, t, cx)
            rgba = np.dstack([col, dens])
            Image.fromarray((np.clip(rgba, 0, 1) * 255 + .5).astype(np.uint8), "RGBA").save(jd / f"nuage-{i}-{tag}.png")
        meta.append(dict(x=x0, y=y0, width=x1 - x0, height=y1 - y0, speed=v, centre=cx, halfWidth=rw))
    (jd / "nuages.json").write_text(json.dumps(dict(design=[1440, 900], clouds=meta), indent=1))
    print("jour ok")


def _trans_frame(args):
    i, p, d = args
    img = _SC.frame(p)
    save(img, f"{d}/{i:04d}.png")


_SC = None


def transition(out, W, H):
    global _SC
    td = out / "transition"; td.mkdir(parents=True, exist_ok=True)
    fr = out / "_frames" / "transition"; fr.mkdir(parents=True, exist_ok=True)
    _SC = dn.Scene(W, H)
    n = int(FPS * 3.6)
    jobs = [(i, ease(i / (n - 1)), str(fr)) for i in range(n) if not (fr / f"{i:04d}.png").exists()]
    with mp.get_context("fork").Pool(2) as pool:
        pool.map(_trans_frame, jobs, chunksize=2)
    encode(fr, td / "nuit-jour.mp4")
    encode(fr, td / "jour-nuit.mp4", reverse=True)
    print("transition ok")


# ---------------------------------------------------------------- bird sprites
def birds(out, poses=12):
    """jour/oiseau-<near|far>-<i>.png: one gull silhouette per wing pose (i = 0 wings down ..
    poses-1 wings up), drawn like ambient.py. The shell moves these small images instead of
    repainting a canvas: animating the flock costs a few textured quads."""
    from PIL import ImageDraw
    jd = out / "jour"; jd.mkdir(parents=True, exist_ok=True)
    S4, sz = 8, 12.0                         # design size 12 pt, sprites 2x (24 px half-span)
    W, H = int(2 * sz + 6), int(2 * sz + 6)  # in points; sprite pixel = 2 x point
    for tag, col, width in (("near", (39, 50, 74, 225), 1.7), ("far", (70, 88, 120, 175), 1.25)):
        for i in range(poses):
            wing = -1 + 2 * i / (poses - 1)
            img = Image.new("RGBA", (W * 2 * S4, H * 2 * S4), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            x, y = W / 2, H / 2
            def quad(p0, c, p1, n=14):   # quadratic Bezier, as the QML canvas drew it
                return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0],
                         (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1]) for t in np.linspace(0, 1, n)]
            body = (x, y + sz * .08)
            left = quad((x - sz, y - sz * .62 * wing), (x - sz * .5, y - sz * .38 * wing - sz * .12), body)
            right = quad(body, (x + sz * .5, y - sz * .38 * wing - sz * .12), (x + sz, y - sz * .62 * wing))
            line = left + right[1:]
            k = 2 * S4
            d.line([(px * k, py * k) for px, py in line], fill=col, width=int(width * k), joint="curve")
            img.resize((W * 2, H * 2), Image.LANCZOS).save(jd / f"oiseau-{tag}-{i}.png")
    print("oiseaux ok", W, H)


if __name__ == "__main__":
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    W, H = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (1920, 1200)
    what = sys.argv[4].split(",") if len(sys.argv) > 4 else ["day", "night", "transition"]
    if "day" in what: day(out, W, H)
    if "night" in what: night(out, W, H)
    if "transition" in what: transition(out, W, H)
    if "birds" in what or len(sys.argv) <= 4: birds(out)
