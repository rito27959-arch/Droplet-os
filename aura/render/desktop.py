#!/usr/bin/env python3
"""DROPLET AURA 0.2 — "Bureau" screen, iteration 2 (1440x900 pt @2x).

Benchmarked against macOS Tahoe 26 (HIG Materials, WWDC25 "Meet Liquid Glass"):
  - menu bar fully transparent; app name bold, menus regular 13 pt
  - Liquid Glass only on the navigation layer (sidebar, toolbar controls, Dock);
    the content area uses a standard (non-glass) material, no glass on glass
  - the sidebar is lit by what is BEHIND the window (behind-window vibrancy)
  - symbols: Phosphor (MIT) instead of hand-drawn glyphs
  - Droplet signature: every glass highlight comes from the eclipse (upper right)

  desktop.py <out.png>
"""
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

from core import (GOUTTE, S, TXT, TXT2, TXT3, WHITE, Canvas, hexc)
from glyphs_ui import glyph
from icons import doc_icon, folder_icon, icon
from wallpaper import render as wallpaper

W, H = 1440, 900
GOUTTE_REMPLIE = hexc("#ec002d")
SIDEBAR_TINT = hexc("#1c2233")
CONTENT_BG = hexc("#121621")


def menu_bar(c):
    y = 15.5
    c.image(glyph("eclipse", 18, (1, 1, 1)), 15, 6.5)
    x = 46
    x += c.text("Fichiers", x, y, "bold", 13, TXT, anchor="lm", shadow=0.45) + 20
    for m in ("Fichier", "Édition", "Présentation", "Aller", "Fenêtre", "Aide"):
        x += c.text(m, x, y, "regular", 13, TXT, anchor="lm", shadow=0.45) + 19
    clock = "mar. 17 nov.  14:13"
    xr = W - 14
    wdt = c.text(clock, xr, y, "regular", 13, TXT, anchor="rm", shadow=0.45)
    xr -= wdt + 16
    for name, sz, wt in (("controls", 15, "bold"), ("search", 15, "bold"), ("wifi", 16, "bold"), ("battery", 19, "regular")):
        xr -= sz
        c.image(glyph(name, sz, (1, 1, 1), weight=wt), xr, y - sz / 2)
        xr -= 15


def capsule(c, x, y, w, h, items=()):
    """Toolbar control group: Liquid Glass over the content, symbols as vibrant overlay."""
    c.glass(x, y, w, h, h / 2, tint=hexc("#262d3d"), tint_a=0.40, frost=4, bezel=9, lens=1.2, rim=0.85,
            lift=0.025, hairline=0.12, shadow=True)
    n = len(items)
    for i, (g, col) in enumerate(items):
        gx = x + w * (i + 0.5) / n - 9
        c.image(glyph(g, 18, col), gx, y + h / 2 - 9)


def window(c, wall):
    x, y, w, h, r = 120, 78, 920, 604, 26
    c.shadow2(x, y, w, h, r, k=1.15)
    # content layer: standard material (not glass) — lets a hint of the desktop through
    c.glass(x, y, w, h, r, tint=CONTENT_BG, tint_a=0.93, frost=40, bezel=10, lens=0.3, rim=0.35,
            lift=0.0, hairline=0.10, shadow=False)
    # sidebar: Liquid Glass lit by what is BEHIND the window (behind-window vibrancy)
    sx, sy, sw, sh = x + 8, y + 8, 220, h - 16
    behind = gaussian_filter(wall, sigma=(40 * S, 40 * S, 0))
    c.glass(sx, sy, sw, sh, r - 8, tint=SIDEBAR_TINT, tint_a=0.62, frost=2, bezel=14, lens=1.0, rim=0.75,
            lift=0.035, hairline=0.12, shadow=True, source=np.clip(behind * 1.6, 0, 1))

    # window controls (Droplet: one capsule of three symbols, top of the sidebar)
    cy = sy + 22
    c.solid(sx + 12, cy - 12, 84, 24, 12, WHITE, a=0.07)
    for i, g in enumerate(("close", "minimize", "expand")):
        c.image(glyph(g, 13, TXT2, weight="bold"), sx + 18 + i * 27, cy - 6.5)

    def section(label, yy):
        c.text(label, sx + 18, yy, "semibold", 11, TXT3, anchor="lm")

    def item(g, label, yy, selected=False, dot=None):
        if selected:
            c.solid(sx + 8, yy - 14, sw - 16, 28, 9, WHITE, a=0.11)
        if dot is not None:
            c.solid(sx + 23, yy - 4.5, 9, 9, 4.5, dot)
        else:
            c.image(glyph(g, 17, tuple(GOUTTE)), sx + 18, yy - 8.5)
        c.text(label, sx + 44, yy, "regular", 13, TXT, anchor="lm")

    yy = sy + 62
    section("Favoris", yy); yy += 24
    for g, lab, sel in (("recents", "Récents", False), ("apps", "Applications", False), ("desktop", "Bureau", False),
                        ("doc", "Documents", True), ("download", "Téléchargements", False)):
        item(g, lab, yy, sel); yy += 28
    yy += 14; section("Emplacements", yy); yy += 24
    for g, lab in (("disk", "Droplet HD"), ("network", "Réseau")):
        item(g, lab, yy); yy += 28
    yy += 14; section("Étiquettes", yy); yy += 24
    for col, lab in ((GOUTTE, "Important"), (hexc("#ff9f0a"), "En cours"), (hexc("#30d158"), "Terminé")):
        item(None, lab, yy, dot=col); yy += 28

    # toolbar: floating glass groups over the content
    cx0 = sx + sw + 14
    ty, th = y + 14, 36
    capsule(c, cx0, ty, 76, th, (("back", TXT), ("forward", TXT3)))
    c.text("Documents", cx0 + 92, ty + th / 2, "bold", 15, TXT, anchor="lm")
    xr = x + w - 14
    xr -= 190; capsule(c, xr, ty, 190, th)
    c.image(glyph("search", 16, TXT2), xr + 13, ty + th / 2 - 8)
    c.text("Rechercher", xr + 36, ty + th / 2, "regular", 13, TXT3, anchor="lm")
    xr -= 10 + 76; capsule(c, xr, ty, 76, th, (("share", TXT), ("tag", TXT)))
    xr -= 10 + 76; capsule(c, xr, ty, 76, th, (("grid", TXT), ("list", TXT3)))

    # file grid (content layer)
    thumb = Image.fromarray((wall[int(0.05 * wall.shape[0]):int(0.95 * wall.shape[0]),
                                 int(0.50 * wall.shape[1]):int(1.0 * wall.shape[1])] * 255).astype(np.uint8))
    items = [("folder", "Projets"), ("folder", "Photos"), ("folder", "Musique"), ("folder", "Factures"),
             ("folder", "Archives"), ("pdf", "Droplet OS 0.2.pdf"), ("sheet", "Budget 2026.ods"),
             ("text", "Notes de version.md"), ("image", "Éclipse.png")]
    cols, cell_w, cell_h = 5, 132, 128
    gx0 = cx0 + 2
    gy0 = y + 80
    for i, (kind, label) in enumerate(items):
        col, row = i % cols, i // cols
        ix = gx0 + col * cell_w
        iy = gy0 + row * cell_h
        selected = label == "Droplet OS 0.2.pdf"
        if selected:
            c.solid(ix + 27, iy - 3, 78, 78, 12, WHITE, a=0.08)
        ic = folder_icon(int(68 * S)) if kind == "folder" else doc_icon(int(68 * S), kind, thumb if kind == "image" else None)
        c.image(ic, ix + 32, iy + 2)
        tw = c.text_width(label, "regular", 12)
        if selected:
            pw = tw + 14
            c.solid(ix + 66 - pw / 2, iy + 81, pw, 19, 6, GOUTTE_REMPLIE)
            c.text(label, ix + 66, iy + 90.5, "medium", 12, WHITE, anchor="mm")
        else:
            c.text(label, ix + 66, iy + 90.5, "regular", 12, TXT, anchor="mm")
    c.text("9 éléments, 214 Go disponibles", cx0 + (x + w - cx0) / 2, y + h - 18, "regular", 11, TXT3, anchor="mm")


def dock(c):
    names = ["fichiers", "navigateur", "store", "photos", "musique", "calendrier", "assistant", "terminal", "reglages"]
    isz, pad, gap, sep = 54, 8, 6, 14
    w = len(names) * isz + (len(names) - 1) * gap + sep + gap + isz + 2 * pad
    h = isz + 2 * pad
    x, y = (W - w) / 2, H - h - 8
    c.glass(x, y, w, h, 24, tint=hexc("#3a4258"), tint_a=0.20, frost=6, bezel=18, lens=1.6, rim=0.8,
            lift=0.07, hairline=0.13, shadow=True)
    ix = x + pad
    running = {"fichiers", "navigateur", "terminal"}
    for n in names:
        c.image(icon(n, int(isz * S)), ix, y + pad)
        if n in running:
            c.solid(ix + isz / 2 - 2, y + h - 5, 4, 4, 2, WHITE, a=0.75)
        ix += isz + gap
    c.solid(ix + sep / 2 - gap / 2 - 0.5, y + 14, 1, h - 28, 0.5, WHITE, a=0.20)
    ix += sep
    c.image(icon("corbeille", int(isz * S)), ix, y + pad)


def main(out):
    wall = wallpaper(W, H)
    c = Canvas(W, H, 0)
    c.px = wall.copy()
    window(c, wall)
    dock(c)
    menu_bar(c)
    c.save(out)
    Image.open(out).resize((W, H), Image.LANCZOS).save(out.replace(".png", "-1x.png"))
    print(out)


if __name__ == "__main__":
    main(sys.argv[1])
