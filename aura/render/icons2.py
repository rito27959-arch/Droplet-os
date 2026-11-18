"""DROPLET AURA app icons v2 — layered Liquid Glass (HIG model).

Background layer (gradient) + foreground layers: filled, overlapping shapes with
defined edges, some translucent. Each foreground layer gets what the system adds
in Tahoe: contact shadow, frosted refraction of what lies beneath, a specular rim
lit from the top-left and a faint counter-rim. The squircle gets its own glass rim.
"""
import io
import math

import cairosvg
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

from core import squircle_mask

SS = 3
PH = "/home/claude/aura-deps/ph/package/assets"


def rgb(h):
    h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], np.float32)


class Icon:
    def __init__(self, size, top, bot, angle=0.0):
        self.size, self.N = size, size * SS
        N = self.N
        yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
        t = np.clip(yy * math.cos(angle) + xx * math.sin(angle), 0, 1)
        self.px = rgb(top) * (1 - t[..., None]) + rgb(bot) * t[..., None]
        # background light: a broad soft bloom from the top
        self.px += (np.exp(-((xx - 0.35) ** 2 + (yy + 0.1) ** 2) / 0.18) * 0.10)[..., None] * (1 - self.px)
        self.yy, self.xx = yy, xx
        self.u = N / 100

    # ---- masks ----------------------------------------------------------
    def mask(self, draw_fn):
        im = Image.new("L", (self.N, self.N), 0)
        draw_fn(ImageDraw.Draw(im), self.u)
        return np.asarray(im, np.float32) / 255

    def glyph(self, name, cx, cy, size, weight="fill"):
        svg = open(f"{PH}/{weight}/{name}{'' if weight == 'regular' else '-' + weight}.svg").read()
        px = int(size * self.u)
        png = cairosvg.svg2png(bytestring=svg.encode(), output_width=px, output_height=px)
        g = Image.open(io.BytesIO(png)).convert("RGBA").split()[3]
        im = Image.new("L", (self.N, self.N), 0)
        im.paste(g, (int(cx * self.u - px / 2), int(cy * self.u - px / 2)))
        return np.asarray(im, np.float32) / 255

    # ---- a glass foreground layer ------------------------------------------
    def layer(self, M, color, opacity=1.0, depth=1.0, frost=1.0):
        N, u = self.N, self.u
        col = rgb(color) if isinstance(color, str) else np.asarray(color, np.float32)
        # contact shadow on what lies beneath
        sh = gaussian_filter(M, 2.2 * u)
        sh = np.roll(sh, int(1.6 * u), axis=0)
        self.px *= (1 - sh[..., None] * 0.22 * depth)
        # frosted refraction of the layers beneath, brightened like glass
        under = np.stack([gaussian_filter(self.px[..., c], 1.8 * u * frost) for c in range(3)], -1)
        under = under + (1 - under) * 0.10
        body = under * (1 - opacity) + col * opacity
        # inner shading: lighter at the top of the shape, deeper at the bottom
        soft = gaussian_filter(M, 6 * u)
        gy, gx = np.gradient(gaussian_filter(M, 1.2 * u))
        nrm = np.hypot(gx, gy) + 1e-6
        nx, ny = -gx / nrm, -gy / nrm                            # outward normal
        L = np.array([-0.5, -0.86])
        facing = np.clip(nx * L[0] + ny * L[1], 0, 1)
        back = np.clip(-(nx * L[0] + ny * L[1]), 0, 1)
        edge = np.clip(M - gaussian_filter(M, 0.9 * u), 0, 1) * 2.2
        edge = np.clip(edge, 0, 1)
        body = body * (1.04 - 0.10 * self.yy[..., None])
        body = body + edge[..., None] * (facing ** 1.2)[..., None] * 0.65 * (1 - body)
        body = body - edge[..., None] * (back ** 2)[..., None] * 0.18 * body
        body = body + (soft * (1 - self.yy) * 0.04)[..., None]
        self.px = self.px * (1 - M[..., None]) + np.clip(body, 0, 1) * M[..., None]

    def text(self, s, cx, cy, size, weight_file, color):
        im = Image.new("L", (self.N, self.N), 0)
        f = ImageFont.truetype("/usr/share/fonts/opentype/inter/" + weight_file, int(size * self.u))
        ImageDraw.Draw(im).text((cx * self.u, cy * self.u), s, font=f, fill=255, anchor="mm")
        M = np.asarray(im, np.float32) / 255
        self.px = self.px * (1 - M[..., None]) + rgb(color) * M[..., None]

    def finish(self):
        N, u = self.N, self.u
        mask = squircle_mask(N, n=5.0, ss=1)
        # squircle glass rim: bright thin line on the upper-left, faint below
        inner = gaussian_filter(mask, 0.9 * u)
        rim = np.clip(mask - inner, 0, 1) * 2.0
        lit = np.clip(1 - (self.xx * 0.6 + self.yy), 0, 1)
        px = self.px + (rim * (0.25 + 0.6 * lit))[..., None] * (1 - self.px) * 0.8
        px = px - (rim * self.yy * 0.15)[..., None] * px
        rgba = np.dstack([np.clip(px, 0, 1), mask])
        return Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").resize((self.size, self.size), Image.LANCZOS)


def rr(box, r):
    return lambda d, u: d.rounded_rectangle([b * u for b in box], radius=r * u, fill=255)


def circ(cx, cy, r):
    return lambda d, u: d.ellipse([(cx - r) * u, (cy - r) * u, (cx + r) * u, (cy + r) * u], fill=255)


# ------------------------------------------------------------------ designs
def i_fichiers(s):
    ic = Icon(s, "#3d9bff", "#0a4ccf")
    ic.layer(ic.mask(lambda d, u: (d.rounded_rectangle([20 * u, 22 * u, 48 * u, 36 * u], radius=6 * u, fill=255),
                                   d.rounded_rectangle([20 * u, 28 * u, 80 * u, 72 * u], radius=8 * u, fill=255))),
             "#ffffff", 0.34, frost=1.4)
    ic.layer(ic.mask(rr((14, 40, 86, 80), 9)), "#ffffff", 0.94)
    return ic.finish()


def i_navigateur(s):
    ic = Icon(s, "#7f73ff", "#2f22c4")
    ic.layer(ic.mask(circ(50, 50, 30)), "#ffffff", 0.24, frost=1.6)
    ic.layer(ic.glyph("globe-hemisphere-west", 50, 50, 64), "#ffffff", 0.95)
    return ic.finish()


def i_store(s):
    ic = Icon(s, "#ff6684", "#d90a37")
    ic.layer(ic.mask(rr((36, 26, 80, 68), 9)), "#ffffff", 0.32, frost=1.4)
    front = ic.mask(rr((20, 40, 66, 82), 9))
    handle = ic.mask(lambda d, u: d.arc([31 * u, 26 * u, 55 * u, 52 * u], 180, 360, fill=255, width=int(5 * u)))
    ic.layer(np.clip(front + handle, 0, 1), "#ffffff", 0.95)
    return ic.finish()


def i_photos(s):
    ic = Icon(s, "#ffbe55", "#ff3358", angle=0.35)
    ic.layer(ic.mask(circ(64, 34, 13)), "#ffffff", 0.45, frost=1.3)
    ic.layer(ic.mask(lambda d, u: d.polygon([(14 * u, 80 * u), (40 * u, 44 * u), (55 * u, 63 * u), (66 * u, 51 * u), (86 * u, 80 * u)], fill=255)),
             "#ffffff", 0.95)
    return ic.finish()


def i_musique(s):
    ic = Icon(s, "#cf74ff", "#5a2ee0")
    ic.layer(ic.mask(circ(40, 58, 22)), "#ffffff", 0.22, frost=1.6)
    ic.layer(ic.mask(circ(62, 42, 22)), "#ffffff", 0.22, frost=1.6)
    ic.layer(ic.glyph("music-notes-simple", 50, 50, 58), "#ffffff", 0.96)
    return ic.finish()


def i_calendrier(s):
    ic = Icon(s, "#ffffff", "#e8eaef")
    ic.layer(ic.mask(rr((0, 0, 100, 30), 0)), "#ff2d55", 0.0, depth=0.0)  # no-op keeps API symmetric
    ic.text("MAR.", 50, 25, 14, "Inter-SemiBold.otf", "#ec002d")
    ic.text("17", 50, 61, 50, "InterDisplay-Light.otf", "#1d1d1f")
    return ic.finish()


def i_assistant(s):
    ic = Icon(s, "#1c2236", "#05070c")
    N, u = ic.N, ic.u
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / u
    r = np.hypot(xx - 50, yy - 50); th = np.arctan2(yy - 50, xx - 50)
    lobe = (1 + np.cos(th - math.radians(-130))) / 2
    R = 22
    halo = (rgb("#ff6a88") * (np.exp(-((r - R - 2) / 3.2) ** 2) * (0.15 + 0.85 * lobe ** 2.5))[..., None] * 0.9
            + rgb("#ff2d55") * (np.exp(-((r - R - 7) / 7) ** 2) * (0.1 + 0.9 * lobe ** 2))[..., None] * 0.5
            + rgb("#7b4dff") * (np.exp(-((r - R - 16) / 12) ** 2) * (0.2 + 0.8 * lobe ** 2))[..., None] * 0.35) * (r > R)[..., None]
    ic.px = ic.px + halo
    ring = np.clip(1 - np.abs(r - R - 0.6) / 1.1, 0, 1) * (0.3 + 0.7 * lobe ** 3)
    ic.px = ic.px + ring[..., None] * (1 - ic.px) * 0.95
    ic.layer(np.clip((R - r) / 0.8, 0, 1), "#06080f", 1.0, depth=0.4)
    return ic.finish()


def i_terminal(s):
    ic = Icon(s, "#3e4350", "#121419")
    ic.layer(ic.mask(rr((16, 22, 84, 78), 8)), "#ffffff", 0.08, frost=1.2)
    chev = ic.mask(lambda d, u: d.line([28 * u, 38 * u, 41 * u, 50 * u, 28 * u, 62 * u], fill=255, width=int(6 * u), joint="curve"))
    ends = ic.mask(lambda d, u: [d.ellipse([(x - 3) * u, (y - 3) * u, (x + 3) * u, (y + 3) * u], fill=255) for x, y in ((28, 38), (41, 50), (28, 62))])
    ic.layer(np.clip(chev + ends, 0, 1), "#ffffff", 0.96, depth=0.5)
    ic.layer(ic.mask(rr((47, 58, 68, 64), 3)), "#ff375f", 0.96, depth=0.5)
    return ic.finish()


def i_reglages(s):
    ic = Icon(s, "#a2a8b4", "#4b525f")
    ic.layer(ic.glyph("gear-six", 50, 50, 84), "#ffffff", 0.40, frost=1.4)
    ic.layer(ic.mask(circ(50, 50, 13)), "#ffffff", 0.96)
    return ic.finish()


def i_corbeille(s):
    ic = Icon(s, "#f1f3f7", "#c2c8d2")
    ic.layer(ic.mask(rr((27, 24, 73, 31), 3)), "#5b6270", 0.85, depth=0.5)
    ic.layer(ic.mask(rr((31, 35, 69, 80), 7)), "#ffffff", 0.55, frost=1.5)
    ic.layer(ic.mask(lambda d, u: [d.rounded_rectangle([(x - 2) * u, 43 * u, (x + 2) * u, 72 * u], radius=2 * u, fill=255) for x in (42, 50, 58)]),
             "#5b6270", 0.75, depth=0.3)
    return ic.finish()


def i_editeur(s):
    ic = Icon(s, "#ffd36b", "#ff9a1f", angle=0.2)
    ic.layer(ic.mask(rr((22, 16, 78, 84), 9)), "#ffffff", 0.95)
    ic.layer(ic.mask(lambda d, u: [d.rounded_rectangle([32 * u, y * u, (68 if i % 3 != 2 else 54) * u, (y + 4) * u], radius=2 * u, fill=255)
                                   for i, y in enumerate((30, 40, 50, 60, 70))]), "#c9781a", 0.55, depth=0.3)
    return ic.finish()


def i_capture(s):
    ic = Icon(s, "#5e6475", "#1e2129")
    ic.layer(ic.mask(rr((22, 30, 78, 72), 8)), "#ffffff", 0.16, frost=1.5)
    corners = ic.mask(lambda d, u: [d.line(p, fill=255, width=int(5 * u), joint="curve") for p in (
        [16 * u, 34 * u, 16 * u, 22 * u, 28 * u, 22 * u], [72 * u, 22 * u, 84 * u, 22 * u, 84 * u, 34 * u],
        [84 * u, 66 * u, 84 * u, 78 * u, 72 * u, 78 * u], [28 * u, 78 * u, 16 * u, 78 * u, 16 * u, 66 * u])])
    ic.layer(corners, "#ffffff", 0.96, depth=0.5)
    ic.layer(ic.mask(circ(50, 51, 9)), "#ff375f", 0.96, depth=0.5)
    return ic.finish()


ICONS = {"fichiers": i_fichiers, "navigateur": i_navigateur, "store": i_store, "photos": i_photos,
         "musique": i_musique, "calendrier": i_calendrier, "assistant": i_assistant, "terminal": i_terminal,
         "reglages": i_reglages, "corbeille": i_corbeille,
         "editeur": i_editeur, "capture": i_capture}


def icon(name, size):
    return ICONS[name](size)


if __name__ == "__main__":
    names = list(ICONS)
    sz = 256
    sheet = Image.new("RGBA", (len(names) * (sz + 48) + 48, sz + 96), (26, 22, 44, 255))
    for i, n in enumerate(names):
        sheet.alpha_composite(icon(n, sz), (48 + i * (sz + 48), 48))
    sheet.save("/tmp/aura/icons2-sheet.png")
    sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS).save("/tmp/aura/icons2-small.png")
    print("ok")
