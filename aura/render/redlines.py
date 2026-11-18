#!/usr/bin/env python3
"""Redline (measurement) sheet for the Bureau screen — the spec engineers implement from.
Draws dimension callouts over a dimmed render. All values in points (1x)."""
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"
CYAN = (0, 214, 255)
PINK = (255, 55, 95)
S = 2


def main(src, out):
    base = Image.open(src).convert("RGB")
    W, H = base.size
    dim = Image.new("RGB", base.size, (0, 0, 0))
    img = Image.blend(base, dim, 0.45)
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 11 * S)

    def P(v): return v * S

    def tag(x, y, text, col=CYAN):
        tw = d.textlength(text, font=f)
        d.rounded_rectangle([P(x) - 4, P(y) - 13, P(x) + tw + 8, P(y) + 13], radius=8, fill=(10, 12, 18), outline=col, width=2)
        d.text((P(x) + 2, P(y)), text, font=f, fill=col, anchor="lm")

    def vdim(x, y0, y1, text, side=1):
        d.line([P(x), P(y0), P(x), P(y1)], fill=CYAN, width=2)
        for yy in (y0, y1): d.line([P(x) - 6, P(yy), P(x) + 6, P(yy)], fill=CYAN, width=2)
        tw = d.textlength(text, font=f) / S
        tag(x + 6 if side > 0 else x - tw - 18, (y0 + y1) / 2 if y1 - y0 > 20 else y0 - 16, text)

    def hdim(x0, x1, y, text):
        d.line([P(x0), P(y), P(x1), P(y)], fill=CYAN, width=2)
        for xx in (x0, x1): d.line([P(xx), P(y) - 6, P(xx), P(y) + 6], fill=CYAN, width=2)
        tag((x0 + x1) / 2 - 14, y - 14, text)

    def box(x, y, w, h, col=PINK):
        d.rounded_rectangle([P(x), P(y), P(x + w), P(y + h)], radius=4, outline=col, width=2)

    # menu bar
    vdim(560, 0, 24, "Barre de menus 24")
    tag(40, 40, "Nom de l'app : Inter Bold 13 · −0,08", PINK)
    tag(250, 40, "Menus : Inter 13 · −0,08 · pas 22", PINK)
    tag(1150, 40, "Pictos 14–19 · pas 18 · horloge 13", PINK)
    # window
    x, y, w, h = 84, 72, 980, 418
    tag(x + 4, y + h + 22, "Fenêtre : rayon 26 · liseré ext. noir 55 % · liseré int. blanc 13 % · ombre 50 pt / 30 pt")
    hdim(x, x + 8, y + 200, "8")
    tag(x + 4, y + h + 48, "Barre latérale : verre · rayon 18 (26 − 8) · largeur 226", PINK)
    box(x + 8 + 8, y + 8 + 26 + 24 + 28 * 3 - 13, 210, 26)
    tag(x + 240, y + 8 + 26 + 24 + 28 * 3, "Ligne 28 · sélection 26 · rayon 8 · picto 16 accent · texte 13", PINK)
    tag(x + 20, y + 8 + 26 - 18, "Section : Inter SemiBold 11 · gris 3", PINK)
    # toolbar
    cx0 = x + 8 + 226 + 14
    vdim(cx0 - 6, y + 13, y + 49, "36", side=-1)
    tag(cx0 + 90, y + 66, "Titre : Inter Display SemiBold 15 · −0,23", PINK)
    tag(cx0 + 330, y + 66, "Capsules de verre 36 · rayon 18 · écart 8 · picto 16", PINK)
    # icon grid
    tag(x + 4, y + h + 74, "Icônes 64 · cellule 128 × 116 · libellé Inter 12 · sélection : fond 76 × 74 r10 + gélule accent r5", PINK)
    # widgets
    tag(1104, 446, "Widgets : verre clair · rayon 24 · largeur 300 · écart 16", PINK)
    # dock
    tag(470, 808, "Dock : verre · rayon 22 · marge 7 · icônes 52 · écart 5 · point actif 3,5 · séparateur 1", PINK)
    vdim(1030, 900 - 66 - 7, 900 - 7, "66")
    vdim(1036, 900 - 7, 900, "7", side=-1)
    tag(1046, 892 - 66 / 2 - 20, "", CYAN) if False else None
    img.save(out)
    img.resize((W // 2, H // 2), Image.LANCZOS).save(out.replace(".png", "-1x.png"))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
