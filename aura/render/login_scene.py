#!/usr/bin/env python3
"""Droplet 0.2 — login screen prototype, harmonised with the desktop (same wallpaper, same glass).

Night: the current body of the night cycle (here Saturn). Day: the garden.
  login_scene.py OUTDIR
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

from core import Canvas, S, hexc
from glassgl import GlassGL
from ph import ph
import planets

W, H = 1440, 900
HERE = Path(__file__).resolve().parent


def wallpaper(mode):
    if mode == "jour":
        im = Image.open(HERE.parent / "wallpapers" / "jardin-jour.jpg").convert("RGB").resize((W * S, H * S), Image.LANCZOS)
        return np.asarray(im, np.float32) / 255
    return planets.render_planet("saturne", W * S, H * S, S, R=150)


def render(mode, out):
    c = Canvas(W, H, 0)
    c.px = wallpaper(mode)
    gl = GlassGL(W * S, H * S, scale=S)
    mat = GlassGL.REGULAR_LIGHT if mode == "jour" else GlassGL.REGULAR_DARK
    white = hexc("#ffffff")

    def ink(x, y, w, h):
        """adaptive label colour (Liquid Glass rule): dark on bright backgrounds, white on dark ones."""
        reg = c.px[int(y * S):int((y + h) * S), int(x * S):int((x + w) * S)]
        lum = float((reg @ np.array([.2126, .7152, .0722], np.float32)).mean())
        return (hexc("#1d1d1f"), 0.0) if lum > .5 else (white, .3)

    def glass(x, y, w, h, r, **o):
        m = dict(mat); m.update(o); c.px = gl.apply(c.px, (x, y, w, h), r, **m)

    # a soft veil at the top and bottom so white type reads on any wallpaper
    yy = np.linspace(0, 1, H * S)[:, None, None]
    veil = np.clip(1 - yy / .32, 0, 1) ** 2 * .22 + np.clip((yy - .7) / .3, 0, 1) ** 2 * .30
    c.px = c.px * (1 - veil)

    # status (top right): keyboard layout, network, power
    c.text("FR", W - 92, 22, "semibold", 12, white, anchor="mm", shadow=.3)
    c.image(ph("wifi-high", 16, (1, 1, 1), "bold"), W - 70, 14)
    c.image(ph("battery-high", 22, (1, 1, 1), "fill"), W - 44, 11)

    # date + time (Inter Display: the optical size for large type)
    c.text("Mardi 17 novembre", W / 2, 112, "semibold", 22, white, anchor="mm", shadow=.35, alpha=.92)
    c.text("19:42", W / 2, 196, "display-semibold", 118, white, anchor="mm", tracking=-2.5, shadow=.25, alpha=.94)

    # user
    cx, ay = W / 2, 588
    glass(cx - 40, ay - 40, 80, 80, 40, bevel=18, refraction=8, frost=2)
    av = Image.open(HERE.parent / "icons" / "assistant.png").convert("RGBA").resize((int(66 * S),) * 2, Image.LANCZOS)
    m = np.zeros((int(66 * S),) * 2, np.float32)
    yy2, xx2 = np.mgrid[0:m.shape[0], 0:m.shape[1]]
    rr = m.shape[0] / 2
    m = np.clip(rr - np.hypot(xx2 - rr + .5, yy2 - rr + .5), 0, 1)
    a = np.asarray(av, np.float32); a[..., 3] *= m
    c.image(Image.fromarray(a.astype(np.uint8), "RGBA"), cx - 33, ay - 33)
    col, sh = ink(cx - 60, ay + 50, 120, 24)
    c.text("Droplet", cx, ay + 62, "semibold", 15, col, anchor="mm", shadow=sh)

    # password capsule
    fw, fh, fy = 236, 36, ay + 86
    # a text field is a "regular" surface: enough frost and tint to keep its text legible
    glass(cx - fw / 2, fy, fw, fh, fh / 2, bevel=14, refraction=7, frost=14,
          tintAmount=mat["tintAmount"] + (.30 if mode == "jour" else .12))
    col, _ = ink(cx - fw / 2 + 10, fy + 8, fw - 50, fh - 16)
    c.text("Saisissez le mot de passe", cx - fw / 2 + 16, fy + fh / 2, "regular", 13,
           col, anchor="lm", alpha=.62)
    c.solid(cx + fw / 2 - 31, fy + 6, 24, 24, 12, hexc("#ec002d"), a=.95)
    c.image(ph("arrow-right", 13, (1, 1, 1), "bold"), cx + fw / 2 - 25.5, fy + 11.5)
    c.text("Verrouillage des majuscules désactivé", cx, fy + fh + 22, "regular", 11, white, anchor="mm", alpha=0)

    # power actions: glass circles with labels (bottom centre)
    by = H - 92
    for i, (sym, lab) in enumerate([("moon", "Suspendre"), ("arrow-clockwise", "Redémarrer"), ("power", "Éteindre")]):
        x = cx + (i - 1) * 104
        glass(x - 22, by - 22, 44, 44, 22, bevel=14, refraction=7, frost=8,
              tintAmount=mat["tintAmount"] + (.22 if mode == "jour" else .05))
        col, sh = ink(x - 18, by - 18, 36, 36)
        c.image(ph(sym, 18, tuple(col), "bold" if sym != "moon" else "fill"), x - 9, by - 9)
        col, sh = ink(x - 40, by + 32, 80, 16)
        c.text(lab, x, by + 40, "medium", 12, col, anchor="mm", shadow=sh, alpha=.9)

    c.save(out)


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    for mode in ("nuit", "jour"):
        render(mode, out / f"connexion-{mode}.png")
        print(out / f"connexion-{mode}.png")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/login")
