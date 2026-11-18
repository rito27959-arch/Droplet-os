#!/usr/bin/env python3
"""DROPLET AURA 0.2 — Bureau v2, built on macOS Tahoe metrics (HIG research).

Menu bar 24 pt, transparent; 13 pt text with HIG tracking; window radius 26 pt with
concentric floating sidebar (radius 18) that shows the desktop behind the window
(behind-window blending); toolbar items grouped in glass capsules; 64 pt icon grid,
12 pt labels; Dock in clear frosted glass with 52 pt layered icons.
"""
import sys

import numpy as np
from PIL import Image

from core import S, TXT, WHITE, Canvas, hexc
from icons import doc_icon
from icons2 import icon
from ph import ph
from wallpaper import render as wallpaper

W, H = 1440, 900
LABEL = hexc("#f5f5f7"); LABEL2 = hexc("#a1a1a6"); LABEL3 = hexc("#86868b")
GOUTTE = hexc("#ff375f"); GOUTTE_REMPLIE = hexc("#ec002d")
WIN_BG = hexc("#16181f")


def menu_bar(c):
    cy = 12
    c.image(ph("circle-half", 15, (1, 1, 1), "fill"), 14, cy - 7.5)       # placeholder replaced below
    x = 40
    x += c.text("Fichiers", x, cy, "bold", 13, LABEL, anchor="lm", shadow=0.35) + 22
    for m in ("Fichier", "Édition", "Présentation", "Aller", "Fenêtre", "Aide"):
        x += c.text(m, x, cy, "regular", 13, LABEL, anchor="lm", shadow=0.35) + 22
    xr = W - 14
    xr -= c.text("mar. 17 nov. 14:13", xr, cy, "regular", 13, LABEL, anchor="rm", shadow=0.35) + 18
    for name, sz, wt in (("sliders-horizontal", 15, "bold"), ("magnifying-glass", 14, "bold"),
                         ("wifi-high", 16, "bold"), ("battery-high", 19, "regular")):
        xr -= sz
        c.image(ph(name, sz, (1, 1, 1), wt), xr, cy - sz / 2)
        xr -= 15


def eclipse_mark(c, x, y, size):
    """Droplet OS mark: the eclipse as a crescent of light (thick upper-left, hairline lower-right)."""
    from PIL import ImageDraw
    N = int(size * S * 4)
    im = Image.new("L", (N, N), 0)
    d = ImageDraw.Draw(im)
    R = N / 2 - 1
    d.ellipse([N / 2 - R, N / 2 - R, N / 2 + R, N / 2 + R], fill=255)
    r2, off = R * 0.80, R * 0.13
    d.ellipse([N / 2 - r2 + off, N / 2 - r2 + off, N / 2 + r2 + off, N / 2 + r2 + off], fill=0)
    a = np.asarray(im.resize((int(size * S), int(size * S)), Image.LANCZOS), np.float32) / 255
    c.over(np.ones(a.shape + (3,), np.float32), a, int(x * S), int(y * S))


def capsule(c, x, y, w, h, items=(), wall=None):
    c.glass(x, y, w, h, h / 2, tint=hexc("#2a2d36"), tint_a=0.42, frost=8, bezel=11, lens=1.2,
            rim=0.85, lift=0.03, shadow=True)
    n = len(items)
    for i, (g, col, wt) in enumerate(items):
        gx = x + w * (i + 0.5) / n
        c.image(ph(g, 16, col, wt), gx - 8, y + h / 2 - 8)


def window(c, wall):
    x, y, w, h, r = 84, 72, 980, 418, 26
    c.shadow(x, y, w, h, r, blur=50, dy=30, k=0.60)
    c.solid(x - 0.5, y - 0.5, w + 1, h + 1, r + 0.5, hexc("#000000"), a=0.55)
    c.solid(x, y, w, h, r, WIN_BG, a=1.0)
    c.solid(x + 0.5, y + 0.5, w - 1, h - 1, r - 0.5, WHITE, a=0.0, border=(WHITE, 0.13))
    # floating sidebar — concentric (26 - 8 = 18), shows the desktop behind the window
    sx, sy, sw, sh = x + 8, y + 8, 226, h - 16
    c.glass(sx, sy, sw, sh, 18, tint=hexc("#3b3f4c"), tint_a=0.30, frost=26, bezel=12, lens=0.9,
            rim=0.8, lift=0.055, shadow=False, source=wall)

    def section(label, yy):
        c.text(label, sx + 16, yy, "semibold", 11, LABEL3, anchor="lm")

    def row(g, label, yy, selected=False, dot=None):
        if selected:
            c.solid(sx + 8, yy - 13, sw - 16, 26, 8, WHITE, a=0.11)
        if dot is not None:
            c.solid(sx + 20.5, yy - 4.5, 9, 9, 4.5, dot)
        else:
            c.image(ph(g, 16, GOUTTE, "regular"), sx + 17, yy - 8)
        c.text(label, sx + 42, yy, "regular", 13, LABEL, anchor="lm")

    yy = sy + 26
    section("Favoris", yy); yy += 24
    for g, lab, sel in (("clock", "Récents", False), ("squares-four", "Applications", False),
                        ("desktop", "Bureau", False), ("file-text", "Documents", True),
                        ("arrow-circle-down", "Téléchargements", False)):
        row(g, lab, yy, sel); yy += 28
    yy += 12; section("Emplacements", yy); yy += 24
    for g, lab in (("hard-drives", "Droplet HD"), ("globe-simple", "Réseau")):
        row(g, lab, yy); yy += 28
    yy += 12; section("Étiquettes", yy); yy += 24
    for col, lab in ((GOUTTE, "Important"), (hexc("#ff9f0a"), "En cours"), (hexc("#30d158"), "Terminé")):
        row(None, lab, yy, dot=col); yy += 28

    # toolbar (glass capsules over the content), height 36, concentric with the window corner
    cx0 = sx + sw + 14
    fade_h = 64
    X0, X1 = int((sx + sw + 4) * S), int((x + w - 1) * S)
    Y0, Y1 = int((y + 1) * S), int((y + 1 + fade_h) * S)
    ramp = np.linspace(1, 0, Y1 - Y0, dtype=np.float32)[:, None] ** 1.6
    reg = c.px[Y0:Y1, X0:X1]
    reg[:] = reg * (1 - ramp[..., None] * 0.55) + hexc("#0b0c10") * ramp[..., None] * 0.55
    ty, th = y + 13, 36
    capsule(c, cx0, ty, 76, th, (("caret-left", LABEL, "bold"), ("caret-right", LABEL3, "bold")))
    c.text("Documents", cx0 + 90, ty + th / 2, "display-semibold", 15, LABEL, anchor="lm")
    xr = x + w - 13
    xr -= 108; capsule(c, xr, ty, 108, th, (("minus", LABEL2, "bold"), ("arrows-out-simple", LABEL2, "bold"), ("x", LABEL2, "bold")))
    xr -= 8 + 168; capsule(c, xr, ty, 168, th)
    c.image(ph("magnifying-glass", 15, LABEL2, "bold"), xr + 13, ty + th / 2 - 7.5)
    c.text("Rechercher", xr + 35, ty + th / 2, "regular", 13, LABEL3, anchor="lm")
    xr -= 8 + 40; capsule(c, xr, ty, 40, th, (("export", LABEL2, "bold"),))
    xr -= 8 + 40; capsule(c, xr, ty, 40, th, (("tag-simple", LABEL2, "bold"),))
    xr -= 8 + 76; capsule(c, xr, ty, 76, th, (("squares-four", LABEL, "fill"), ("list-bullets", LABEL3, "bold")))

    # icon view: 64 pt icons, 12 pt labels, Finder-like grid
    thumb = Image.fromarray((wall[int(0.05 * wall.shape[0]):int(0.6 * wall.shape[0]),
                                 int(0.55 * wall.shape[1]):int(1.0 * wall.shape[1])] * 255).astype(np.uint8))
    items = [("folder", "Projets"), ("folder", "Photos"), ("folder", "Musique"), ("folder", "Factures"),
             ("folder", "Clients"), ("pdf", "Droplet OS 0.2.pdf"), ("sheet", "Budget 2026.ods"),
             ("text", "Notes de version.md"), ("image", "Éclipse.png"), ("pdf", "Contrat.pdf")]
    cell_w, cell_h = 128, 116
    cols = 5
    gx0 = cx0 + 2 + ((x + w - 14 - cx0) - cols * cell_w) / 2
    gy0 = y + 80
    folder_img = folder_v2(int(64 * S))
    for i, (kind, label) in enumerate(items):
        col, rw = i % cols, i // cols
        ix, iy = gx0 + col * cell_w, gy0 + rw * cell_h
        sel = label == "Droplet OS 0.2.pdf"
        if sel:
            c.solid(ix + 64 - 38, iy - 5, 76, 74, 10, WHITE, a=0.10)
        ic = folder_img if kind == "folder" else doc_icon(int(64 * S), kind, thumb if kind == "image" else None)
        c.image(ic, ix + 64 - 32, iy)
        if sel:
            tw = c.text_width(label, "regular", 12)
            c.solid(ix + 64 - tw / 2 - 6, iy + 72, tw + 12, 18, 5, GOUTTE_REMPLIE)
            c.text(label, ix + 64, iy + 81, "regular", 12, WHITE, anchor="mm")
        else:
            c.text(label, ix + 64, iy + 81, "regular", 12, LABEL, anchor="mm")


def folder_v2(px):
    """Folder in the layered-glass style of the app icons, Droplet accent tint."""
    from icons2 import Icon, rr
    import numpy as np
    from PIL import Image
    ic = Icon(px // 1, "#000000", "#000000")
    ic.px[:] = 0
    back = ic.mask(lambda d, u: (d.rounded_rectangle([6 * u, 16 * u, 42 * u, 32 * u], radius=6 * u, fill=255),
                                 d.rounded_rectangle([6 * u, 22 * u, 94 * u, 86 * u], radius=9 * u, fill=255)))
    front = ic.mask(rr((6, 32, 94, 86), 9))
    ic.layer(back, "#2f7df0", 1.0, depth=0.0)
    ic.layer(front, "#5aa8ff", 0.92)
    alpha = np.clip(back + front, 0, 1)
    rgba = np.dstack([np.clip(ic.px, 0, 1), alpha])
    return Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").resize((px, px), Image.LANCZOS)


def widget_glass(c, x, y, w, h):
    # clear-ish glass: rich background behind (the corona), light dimming for legibility
    c.glass(x, y, w, h, 24, tint=hexc("#0d0f16"), tint_a=0.34, frost=14, bezel=20, lens=1.5,
            dispersion=1.4, rim=0.95, lift=0.04, shadow=True)


def widgets(c):
    x, w = 1104, 300
    # Weather
    y, h = 56, 150
    widget_glass(c, x, y, w, h)
    c.text("Douala", x + 18, y + 28, "semibold", 13, LABEL, anchor="lm")
    c.image(ph("navigation-arrow", 11, LABEL, "fill"), x + 18 + c.text_width("Douala", "semibold", 13) + 5, y + 22.5)
    c.text("27°", x + 16, y + 74, "display-light", 46, LABEL, anchor="lm")
    c.image(ph("cloud-sun", 30, (1, 1, 1), "fill"), x + w - 48, y + 15)
    c.text("Nuageux", x + 18, y + 112, "medium", 12, LABEL, anchor="lm")
    c.text("Max. 31°  Min. 24°", x + 18, y + 130, "regular", 12, LABEL2, anchor="lm")
    # Calendar
    y, h = 222, 196
    widget_glass(c, x, y, w, h)
    c.text("MARDI", x + 18, y + 26, "semibold", 11, GOUTTE, anchor="lm")
    c.text("17 novembre", x + 18, y + 50, "display-semibold", 20, LABEL, anchor="lm")
    ev = [(GOUTTE, "Revue design Aura", "15:00 – 16:00"), (hexc("#64d2ff"), "Appel avec Karim", "18:30 – 19:00"),
          (hexc("#ffd60a"), "Sport", "20:00 – 21:00")]
    ey = y + 78
    for col, title, when in ev:
        c.solid(x + 18, ey, 3, 32, 1.5, col)
        c.text(title, x + 30, ey + 10, "semibold", 12.5 if False else 12, LABEL, anchor="lm")
        c.text(when, x + 30, ey + 25, "regular", 11, LABEL2, anchor="lm")
        ey += 38


def dock(c):
    names = ["fichiers", "navigateur", "store", "photos", "musique", "calendrier", "assistant", "terminal", "reglages"]
    isz, pad, gap = 52, 7, 5
    sep = 14
    w = len(names) * isz + (len(names) - 1) * gap + sep + gap + isz + 2 * pad
    h = isz + 2 * pad
    x, y = (W - w) / 2, H - h - 7
    c.glass(x, y, w, h, 22, tint=hexc("#62646b"), tint_a=0.20, frost=4, bezel=16, lens=1.6,
            rim=1.0, lift=0.10, shadow=True)
    ix = x + pad
    for n in names:
        c.shadow(ix + 3, y + pad + 3, isz - 6, isz - 6, 11, blur=3, dy=1.5, k=0.35)
        c.image(icon(n, int(isz * S)), ix, y + pad)
        if n in ("fichiers", "navigateur", "terminal"):
            c.solid(ix + isz / 2 - 1.75, y + h - 4.2, 3.5, 3.5, 1.75, WHITE, a=0.85)
        ix += isz + gap
    c.solid(ix + sep / 2 - gap / 2 - 0.5, y + 14, 1, h - 28, 0.5, WHITE, a=0.20)
    ix += sep
    c.shadow(ix + 3, y + pad + 3, isz - 6, isz - 6, 11, blur=3, dy=1.5, k=0.35)
    c.image(icon("corbeille", int(isz * S)), ix, y + pad)


def main(out):
    wall = wallpaper(W, H, lumineux=True)
    c = Canvas(W, H, 0)
    c.px = wall.copy()
    window(c, wall)
    widgets(c)
    dock(c)
    # menu bar: mark + items
    eclipse_mark(c, 14, 4.5, 15)
    menu_bar_items(c)
    c.save(out)
    Image.open(out).resize((W, H), Image.LANCZOS).save(out.replace(".png", "-1x.png"))
    print(out)


def menu_bar_items(c):
    cy = 12
    x = 40
    x += c.text("Fichiers", x, cy, "bold", 13, LABEL, anchor="lm", shadow=0.35) + 22
    for m in ("Fichier", "Édition", "Présentation", "Aller", "Fenêtre", "Aide"):
        x += c.text(m, x, cy, "regular", 13, LABEL, anchor="lm", shadow=0.35) + 22
    xr = W - 14
    xr -= c.text("mar. 17 nov. 14:13", xr, cy, "regular", 13, LABEL, anchor="rm", shadow=0.35) + 18
    for name, sz, wt in (("sliders-horizontal", 15, "bold"), ("magnifying-glass", 14, "bold"),
                         ("wifi-high", 16, "bold"), ("battery-high", 19, "regular")):
        xr -= sz
        c.image(ph(name, sz, (1, 1, 1), wt), xr, cy - sz / 2)
        xr -= 18


if __name__ == "__main__":
    main(sys.argv[1])
