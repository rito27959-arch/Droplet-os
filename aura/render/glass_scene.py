#!/usr/bin/env python3
"""Droplet 0.2 — Liquid Glass prototype: the desktop in night and day appearance.

Glass = desktop/effects/liquidglass/liquidglass.frag (the compositor shader), run through
glassgl.py. Content (text, icons, symbols) is drawn on top, as the shell draws it.
  glass_scene.py OUTDIR
"""
import sys
from pathlib import Path
import numpy as np
from PIL import Image

from core import Canvas, S, hexc
from glassgl import GlassGL
from ph import ph

W, H = 1440, 900
import os
KIT = os.environ.get("DROPLET_GLASS", "kit") == "kit"
HERE = Path(__file__).resolve().parent
ICONS = HERE.parent / "icons"

MODES = {
    "nuit": dict(wall="eclipse-lumineux.jpg", glass=GlassGL.REGULAR_DARK, label=hexc("#f5f5f7"),
                 label2=hexc("#a1a1a6"), accent=hexc("#ff375f"), filled=hexc("#ec002d"), sep=(1, 1, 1, .14),
                 platter=(1, 1, 1, .08), bar=hexc("#ffffff")),
    "jour": dict(wall="jardin-jour.jpg", glass=GlassGL.REGULAR_LIGHT, label=hexc("#1d1d1f"),
                 label2=hexc("#5e5e63"), accent=hexc("#ff2d55"), filled=hexc("#ec002d"), sep=(0, 0, 0, .12),
                 platter=(0, 0, 0, .05), bar=hexc("#ffffff")),
}


def icon(name, size_pt):
    return Image.open(ICONS / f"{name}.png").convert("RGBA").resize((int(size_pt * S),) * 2, Image.LANCZOS)


class Scene:
    def __init__(self, mode):
        self.m = MODES[mode]
        bg = Image.open(HERE.parent / "wallpapers" / self.m["wall"]).convert("RGB").resize((W * S, H * S), Image.LANCZOS)
        self.c = Canvas(W, H, 0)
        self.c.px = np.asarray(bg, np.float32) / 255
        self.gl = GlassGL(W * S, H * S, scale=S)

    def glass(self, x, y, w, h, r, **over):
        if KIT:   # macOS 27 kit material, chosen by size (same rule as the compositor)
            m = GlassGL.material(self.m["glass"] is GlassGL.REGULAR_DARK, w, h)
        else:
            m = dict(self.m["glass"]); m.update(over)
        self.c.px = self.gl.apply(self.c.px, (x, y, w, h), r, **m)

    def text(self, s, x, y, weight="regular", size=13, color=None, **kw):
        return self.c.text(s, x, y, weight, size, self.m["label"] if color is None else color, **kw)

    def sym(self, name, x, y, size, color=None, weight="regular"):
        self.c.image(ph(name, size, tuple(self.m["label"] if color is None else color), weight), x, y)

    def line(self, x, y, w):
        r, g, b, a = self.m["sep"]
        self.c.solid(x, y, w, .5, .25, np.array([r, g, b], np.float32), a=a)

    # ---------------------------------------------------------------- pieces
    def eclipse_mark(self):
        # the Droplet mark: a disc of light eclipsed by an offset disc (same geometry as eclipse.svg)
        n = int(16 * S) * 4
        yy, xx = (np.mgrid[0:n, 0:n] + .5) / n * 64
        a = np.clip((30 - np.hypot(xx - 32, yy - 32)) * n / 64, 0, 1) * np.clip((np.hypot(xx - 35.4, yy - 35.4) - 24.6) * n / 64, 0, 1)
        img = Image.fromarray((np.dstack([np.ones((n, n, 3)), a]) * 255).astype(np.uint8), "RGBA")
        self.c.image(img.resize((n // 4, n // 4), Image.LANCZOS), 23, 4)

    def widget(self):
        x, y, w, h = 22, 46, 344, 164
        self.glass(x, y, w, h, 24, frost=4, tintAmount=self.m["glass"]["tintAmount"] * .8)
        lab, lab2, acc = self.m["label"], self.m["label2"], self.m["accent"]
        self.text("MARDI", x + 18, y + 24, "bold", 11, acc, anchor="lm", tracking=.4)
        self.text("17", x + 16, y + 62, "display-light", 48, lab, anchor="lm")
        self.text("novembre 2026", x + 18, y + 98, "regular", 12, lab2, anchor="lm")
        gx, gy, cw = x + 152, y + 22, 25
        for i, dname in enumerate("LMMJVSD"):
            self.text(dname, gx + i * cw + cw / 2, gy, "bold", 9, lab2, anchor="mm")
        first = 6  # 1 Nov 2026 is a Sunday
        for dnum in range(1, 31):
            k = first + dnum - 1
            cx, cy = gx + (k % 7) * cw + cw / 2, gy + 20 + (k // 7) * 21
            if dnum == 17:
                self.c.solid(cx - 10, cy - 10, 20, 20, 10, self.m["filled"])
                self.text("17", cx, cy, "bold", 10, hexc("#ffffff"), anchor="mm")
            else:
                self.text(str(dnum), cx, cy, "medium", 10, lab2 if k % 7 > 4 else lab, anchor="mm")

    def droplet_menu(self):
        x, y, w = 9, 27, 276
        items = ["À propos de cet ordinateur", None, "Réglages du système…", ("Rechercher une app…", "Super Espace"), None,
                 "Suspendre l'activité", "Redémarrer…", "Éteindre…", None, "Fermer la session…"]
        h = 10 + sum(11 if i is None else 24 for i in items)
        self.glass(x, y, w, h, 13, bevel=10, refraction=7, frost=18, tintAmount=self.m['glass']['tintAmount'] + .18,
                   shadowAlpha=.38, shadowBlur=34, shadowY=14)
        cy = y + 5
        for i, it in enumerate(items):
            if it is None:
                self.line(x + 14, cy + 5.5, w - 28); cy += 11; continue
            label, short = it if isinstance(it, tuple) else (it, None)
            if i == 2:   # hovered row
                self.c.solid(x + 5, cy, w - 10, 24, 7, self.m["filled"])
                col = hexc("#ffffff")
            else:
                col = self.m["label"]
            self.text(label, x + 16, cy + 12, "regular", 13, col, anchor="lm")
            if short:
                self.text(short, x + w - 16, cy + 12, "regular", 13, self.m["label2"], anchor="rm")
            cy += 24

    def control_center(self):
        x0, y0, cw = W - 8 - 324, 30, 324
        lab, lab2, fill = self.m["label"], self.m["label2"], self.m["filled"]
        tile = dict(bevel=12, refraction=9, frost=12, shadowAlpha=.22, shadowBlur=22, shadowY=8)

        def round_btn(cx, cy, name, on):
            if on:
                self.c.solid(cx - 15, cy - 15, 30, 30, 15, fill)
            else:
                r, g, b, a = self.m["platter"]
                self.c.solid(cx - 15, cy - 15, 30, 30, 15, np.array([r, g, b], np.float32), a=a * 1.6)
            self.c.image(ph(name, 15, (1, 1, 1) if on else tuple(lab), "fill" if name in ("moon", "sun", "moon-stars") else "bold"), cx - 7.5, cy - 7.5)

        # connectivity
        self.glass(x0, y0, 157, 140, 26, **tile)
        for i, (sym, t, s, on) in enumerate([("wifi-high", "Wi-Fi", "Maison", True), ("bluetooth", "Bluetooth", "Activé", True),
                                             ("broadcast", "AirDrop", "Indisponible", False)][:2]):
            yy = y0 + 34 + i * 46
            round_btn(x0 + 28, yy, sym, on)
            self.text(t, x0 + 52, yy - 7, "semibold", 13, lab, anchor="lm")
            self.text(s, x0 + 52, yy + 9, "regular", 11, lab2, anchor="lm")
        # focus + appearance
        for i, (sym, t, s, on) in enumerate([("moon", "Concentration", "Désactivée", False),
                                             ("sun" if self.m is MODES["jour"] else "moon-stars", "Apparence", "Claire" if self.m is MODES["jour"] else "Sombre", True)]):
            xx, yy = x0 + 167, y0 + i * 75
            self.glass(xx, yy, 157, 65, 26, **tile)
            round_btn(xx + 28, yy + 32.5, sym, on)
            self.text(t, xx + 52, yy + 25.5, "semibold", 13, lab, anchor="lm")
            self.text(s, xx + 52, yy + 41.5, "regular", 11, lab2, anchor="lm")
        # sliders
        for i, (t, sym, v) in enumerate([("Écran", "sun", .72), ("Son", "speaker-high", .45)]):
            yy = y0 + 150 + i * 78
            self.glass(x0, yy, cw, 68, 26, **tile)
            self.text(t, x0 + 16, yy + 18, "semibold", 13, lab, anchor="lm")
            tx, ty, tw = x0 + 14, yy + 34, cw - 28
            r, g, b, a = self.m["platter"]
            self.c.solid(tx, ty, tw, 22, 11, np.array([r, g, b], np.float32), a=a * 2)
            self.c.solid(tx, ty, max(22, tw * v), 22, 11, hexc("#ffffff"), a=.96)
            self.c.image(ph(sym, 13, (0.45, 0.45, 0.48), "fill"), tx + 6, ty + 4.5)

    def dock(self):
        names = ["fichiers", "navigateur", "terminal", "editeur", "photos", "musique", "reglages", "capture"]
        isz, pad, gap, sep = 52, 7, 6, 15
        w = len(names) * isz + (len(names) - 1) * gap + sep + gap + isz + 2 * pad
        h = isz + 2 * pad
        x, y = (W - w) / 2, H - h - 8
        self.glass(x, y, w, h, 26, tintAmount=self.m["glass"]["tintAmount"] * .55, frost=3, refraction=13, bevel=18)
        ix = x + pad
        for n in names:
            self.c.shadow(ix + 4, y + pad + 4, isz - 8, isz - 8, 11, blur=3, dy=1.5, k=0.30)
            self.c.image(icon(n, isz), ix, y + pad)
            if n in ("fichiers", "terminal", "editeur"):
                self.c.solid(ix + isz / 2 - 1.75, y + h - 4.5, 3.5, 3.5, 1.75, self.m["label"], a=.8)
            ix += isz + gap
        r, g, b, a = self.m["sep"]
        self.c.solid(ix + sep / 2 - gap / 2 - .5, y + 14, 1, h - 28, .5, np.array([r, g, b], np.float32), a=a * 1.6)
        ix += sep
        self.c.image(icon("corbeille", isz), ix, y + pad)

    def render(self, path):
        self.widget()
        self.droplet_menu()
        self.control_center()
        self.dock()
        self.menubar_final()
        self.c.save(path)

    def menubar_final(self):
        white = self.m["bar"]
        self.c.solid(14, 2, 34, 20, 7, np.array([1, 1, 1], np.float32), a=.24)
        self.eclipse_mark()
        x = 62
        x += self.text("Fichiers", x, 12, "bold", 13, white, anchor="lm", shadow=.3) + 20
        for t in ("Fichier", "Édition", "Présentation", "Aller", "Fenêtre", "Aide"):
            x += self.text(t, x, 12, "medium", 13, white, anchor="lm", shadow=.3) + 19
        rx = W - 16
        rx -= self.text("mar. 17 nov.  19:20", rx, 12, "medium", 13, white, anchor="rm", shadow=.3) + 14
        self.c.solid(rx - 30, 2, 30, 20, 7, np.array([1, 1, 1], np.float32), a=.24)   # Control Centre is open
        for name, sz, wt in (("toggle-right", 17, "fill"), ("magnifying-glass", 15, "bold"), ("wifi-high", 16, "bold")):
            self.c.image(ph(name, sz, (1, 1, 1), wt), rx - 15 - sz / 2, 12 - sz / 2)
            rx -= 30


def main(out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    for mode in MODES:
        Scene(mode).render(out / f"verre-{mode}.png")
        print(out / f"verre-{mode}.png")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/glass")
