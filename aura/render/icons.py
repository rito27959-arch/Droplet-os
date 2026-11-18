"""DROPLET AURA app icons — original designs, layered glass material.

Every icon: continuous-corner squircle, a two-tone body gradient, a soft top sheen,
a thin inner rim (light above, shade below) and a white glyph with depth.
Rendered at 4x supersampling, returned as RGBA PIL images at the requested pixel size.
"""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from core import squircle_mask

SS = 4


def _grad(n, top, bot, angle=90):
    t = np.linspace(0, 1, n, dtype=np.float32)
    g = np.array(top, np.float32)[None, None] * (1 - t)[:, None, None] + np.array(bot, np.float32)[None, None] * t[:, None, None]
    return np.repeat(g, n, axis=1)


def rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _glyph_layer(N):
    img = Image.new("L", (N, N), 0)
    return img, ImageDraw.Draw(img)


LIGHT = np.array([0.50, -0.87], np.float32)   # the eclipse: upper right


def _compose(size, top, bot, glyph_fn, glyph_color=(1, 1, 1), glyph_grad=None, dark_glyph=False):
    """Layered Liquid-Glass icon: tinted body + a glass glyph layer floating above it."""
    from scipy.ndimage import gaussian_filter
    N = size * SS
    mask = squircle_mask(N, n=5.0, ss=1)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32) / N
    # body: diagonal gradient, brighter toward the light (upper right)
    t = np.clip(0.5 + ((xx - 0.5) * LIGHT[0] + (yy - 0.5) * LIGHT[1]) * 0.9, 0, 1)
    ctop, cbot = np.array(rgb(top), np.float32), np.array(rgb(bot), np.float32)
    body = cbot * (1 - t[..., None]) + ctop * t[..., None]
    # inner glow from the top: depth
    body = body + (np.exp(-((yy) / 0.35) ** 2) * 0.10)[..., None] * (1 - body)
    # glyph layer
    g_img, d = _glyph_layer(N)
    glyph_fn(d, N)
    g = np.asarray(g_img, np.float32) / 255
    # coloured shadow cast by the glass glyph (opposite the light, slightly blurred)
    sh = gaussian_filter(g, N * 0.025)
    sh = np.roll(np.roll(sh, int(N * 0.018), axis=0), -int(N * 0.010), axis=1)
    body = body * (1 - sh[..., None] * (0.12 if dark_glyph else 0.30))
    # glass glyph: almost white, a breath of the body colour, darker toward the shadow side
    gb = gaussian_filter(g, N * 0.006)
    gy, gx = np.gradient(gaussian_filter(g, N * 0.012))
    nrm = np.hypot(gx, gy) + 1e-6
    facing = np.clip(-(gx * LIGHT[0] + gy * LIGHT[1]) / nrm, -1, 1)
    edge = np.clip(nrm * N * 0.02, 0, 1)
    if glyph_grad:
        gc = _grad(N, rgb(glyph_grad[0]), rgb(glyph_grad[1]))
    else:
        base = np.array(glyph_color, np.float32)
        gc = base * (0.97 - 0.10 * (1 - t))[..., None] + (body * 0.10 if not dark_glyph else 0)
    gc = gc + (edge * np.clip(facing, 0, 1) * 0.55)[..., None] * (1 - gc)          # specular rim
    gc = gc * (1 - (edge * np.clip(-facing, 0, 1) * 0.18)[..., None])                # shaded rim
    ga = gb * (0.94 if not dark_glyph else 1.0)
    body = body * (1 - ga[..., None]) + gc * ga[..., None]
    # squircle rim: lit toward the light, darker opposite
    m_img = Image.fromarray((mask * 255).astype(np.uint8))
    inner = np.asarray(m_img.filter(ImageFilter.MinFilter(int(SS * 2) * 2 + 1)), np.float32) / 255
    rim = np.clip(mask - inner, 0, 1)
    my, mx = np.gradient(gaussian_filter(mask, SS * 2))
    mn = np.hypot(mx, my) + 1e-6
    mf = np.clip(-(mx * LIGHT[0] + my * LIGHT[1]) / mn, -1, 1)
    body = body + (rim * np.clip(mf, 0, 1) * 0.55)[..., None] * (1 - body) - (rim * np.clip(-mf, 0, 1) * 0.20)[..., None] * body
    rgba = np.dstack([np.clip(body, 0, 1), mask])
    im = Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA")
    return im.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------- glyphs
def g_files(d, N):
    u = N / 100
    d.rounded_rectangle([22 * u, 30 * u, 50 * u, 44 * u], radius=5 * u, fill=150)   # tab
    d.rounded_rectangle([22 * u, 36 * u, 78 * u, 72 * u], radius=7 * u, fill=255)


def g_browser(d, N):
    """Globe with meridians: an open world, not a compass."""
    u = N / 100
    c, R, w = 50 * u, 27 * u, int(4.2 * u)
    d.ellipse([c - R, c - R, c + R, c + R], outline=255, width=w)
    d.ellipse([c - R * 0.42, c - R, c + R * 0.42, c + R], outline=255, width=int(3.4 * u))
    d.line([c, c - R, c, c + R], fill=255, width=int(3.4 * u))
    d.line([c - R, c, c + R, c], fill=255, width=int(3.4 * u))
    for k in (-0.55, 0.55):
        y = c + k * R
        half = R * math.sqrt(1 - k * k)
        d.line([c - half + 1.5 * u, y, c + half - 1.5 * u, y], fill=255, width=int(3 * u))


def g_terminal(d, N):
    u = N / 100
    w = int(6 * u)
    d.line([30 * u, 38 * u, 44 * u, 50 * u, 30 * u, 62 * u], fill=255, width=w, joint="curve")
    for x, y in ((30 * u, 38 * u), (44 * u, 50 * u), (30 * u, 62 * u)):
        d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=255)
    d.rounded_rectangle([50 * u, 59 * u, 70 * u, 65 * u], radius=3 * u, fill=255)


def g_settings(d, N):
    u = N / 100
    c = 50 * u
    teeth = 10
    pts = []
    for i in range(teeth * 2):
        a = 2 * math.pi * i / (teeth * 2)
        for k in (-0.11, 0.11):
            r = (30 if i % 2 == 0 else 24) * u
            pts.append((c + r * math.cos(a + k), c + r * math.sin(a + k)))
    d.polygon(pts, fill=255)
    d.ellipse([c - 11 * u, c - 11 * u, c + 11 * u, c + 11 * u], fill=0)


def g_store(d, N):
    u = N / 100
    d.rounded_rectangle([28 * u, 38 * u, 72 * u, 74 * u], radius=8 * u, fill=255)
    d.arc([39 * u, 24 * u, 61 * u, 50 * u], 180, 360, fill=255, width=int(4.5 * u))
    d.ellipse([39 * u - 2.25 * u, 37 * u - 2.25 * u, 39 * u + 2.25 * u, 37 * u + 2.25 * u], fill=255)
    d.ellipse([61 * u - 2.25 * u, 37 * u - 2.25 * u, 61 * u + 2.25 * u, 37 * u + 2.25 * u], fill=255)


def g_photos(d, N):
    u = N / 100
    d.ellipse([58 * u, 26 * u, 72 * u, 40 * u], fill=255)
    d.polygon([(20 * u, 74 * u), (42 * u, 42 * u), (56 * u, 60 * u), (64 * u, 50 * u), (80 * u, 74 * u)], fill=255)


def g_music(d, N):
    u = N / 100
    d.polygon([(40 * u, 30 * u), (72 * u, 23 * u), (72 * u, 31 * u), (40 * u, 38 * u)], fill=255)
    d.rectangle([40 * u, 30 * u, 44.5 * u, 68 * u], fill=255)
    d.rectangle([67.5 * u, 24 * u, 72 * u, 62 * u], fill=255)
    d.ellipse([28 * u, 60 * u, 44.5 * u, 74 * u], fill=255)
    d.ellipse([55.5 * u, 54 * u, 72 * u, 68 * u], fill=255)


def g_trash(d, N):
    u = N / 100
    d.rounded_rectangle([32 * u, 34 * u, 68 * u, 76 * u], radius=6 * u, fill=255)
    d.rounded_rectangle([27 * u, 27 * u, 73 * u, 32 * u], radius=2.5 * u, fill=255)
    d.rounded_rectangle([43 * u, 22 * u, 57 * u, 28 * u], radius=2.5 * u, fill=255)
    for x in (42, 50, 58):
        d.rounded_rectangle([(x - 1.6) * u, 42 * u, (x + 1.6) * u, 68 * u], radius=1.6 * u, fill=0)


def folder_icon(size, top="#5fb4ff", bot="#1f7cf0"):
    """Standalone folder object (content view), layered: back plate, tab, front glass."""
    N = size * SS
    u = N / 100
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    back = Image.new("L", (N, N), 0); db = ImageDraw.Draw(back)
    db.rounded_rectangle([8 * u, 18 * u, 46 * u, 34 * u], radius=6 * u, fill=255)
    db.rounded_rectangle([8 * u, 24 * u, 92 * u, 84 * u], radius=8 * u, fill=255)
    front = Image.new("L", (N, N), 0); df = ImageDraw.Draw(front)
    df.rounded_rectangle([8 * u, 33 * u, 92 * u, 84 * u], radius=8 * u, fill=255)
    gb = _grad(N, rgb(bot), rgb("#0d4fc2"))
    gf = _grad(N, rgb(top), rgb(bot))
    yy = np.mgrid[0:N, 0:N][0].astype(np.float32) / N
    gf = gf + (np.exp(-((yy - 0.33) / 0.05) ** 2) * 0.25)[..., None] * (1 - gf)      # lit top edge
    a_b = np.asarray(back, np.float32) / 255; a_f = np.asarray(front, np.float32) / 255
    sh = np.asarray(front.filter(ImageFilter.GaussianBlur(N * 0.02)), np.float32) / 255
    rgb_ = gb * (1 - sh[..., None] * 0.25)
    rgb_ = rgb_ * (1 - a_f[..., None]) + gf * a_f[..., None]
    alpha = np.clip(a_b + a_f, 0, 1)
    out = np.dstack([np.clip(rgb_, 0, 1), alpha])
    return Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGBA").resize((size, size), Image.LANCZOS)


def doc_icon(size, kind="pdf", thumb=None):
    """Document page: paper, folded corner, content hint; image files show a thumbnail."""
    N = size * SS
    u = N / 100
    page = Image.new("L", (N, N), 0); d = ImageDraw.Draw(page)
    d.polygon([(20 * u, 8 * u), (64 * u, 8 * u), (80 * u, 24 * u), (80 * u, 92 * u), (20 * u, 92 * u)], fill=255)
    img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    paper = Image.new("RGBA", (N, N), (246, 247, 250, 255))
    img.paste(paper, (0, 0), page)
    dd = ImageDraw.Draw(img)
    dd.polygon([(64 * u, 8 * u), (64 * u, 24 * u), (80 * u, 24 * u)], fill=(214, 218, 226, 255))
    if kind == "pdf":
        dd.rounded_rectangle([28 * u, 22 * u, 54 * u, 30 * u], radius=2 * u, fill=(236, 0, 45, 255))
        for i, w in enumerate((44, 40, 44, 30, 44, 38, 26)):
            dd.rounded_rectangle([28 * u, (38 + i * 7) * u, (28 + w) * u, (41 + i * 7) * u], radius=1.5 * u, fill=(176, 182, 194, 255))
    elif kind == "sheet":
        for r in range(7):
            for col in range(3):
                x0, y0 = (28 + col * 15) * u, (30 + r * 8) * u
                dd.rectangle([x0, y0, x0 + 13 * u, y0 + 6 * u], fill=(48, 209, 88, 255) if r == 0 else (205, 230, 212, 255))
    elif kind == "text":
        for i, w in enumerate((30, 44, 40, 44, 22, 44, 36, 40)):
            dd.rounded_rectangle([28 * u, (24 + i * 7.5) * u, (28 + w) * u, (27 + i * 7.5) * u], radius=1.5 * u, fill=(150, 158, 172, 255))
    elif kind == "image" and thumb is not None:
        t = thumb.resize((int(52 * u), int(64 * u)), Image.LANCZOS)
        tm = Image.new("L", t.size, 0); ImageDraw.Draw(tm).rounded_rectangle([0, 0, t.size[0] - 1, t.size[1] - 1], radius=3 * u, fill=255)
        img.paste(t, (int(24 * u), int(24 * u)), tm)
    # soft shadow under the page
    sh = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    sh.putalpha(page.filter(ImageFilter.GaussianBlur(N * 0.03)).point(lambda v: int(v * 0.35)))
    base = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    base.alpha_composite(sh, (0, int(N * 0.015)))
    base.alpha_composite(img)
    return base.resize((size, size), Image.LANCZOS)


def eclipse_icon(size):
    """The Droplet OS mark as an app icon (Assistant): eclipse on night glass."""
    N = size * SS
    mask = squircle_mask(N, n=5.0, ss=1)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float32)
    body = _grad(N, rgb("#1a1f33"), rgb("#05070c"))
    c, R = N / 2, N * 0.24
    r = np.hypot(xx - c, yy - c); th = np.arctan2(yy - c, xx - c)
    lobe = ((1 + np.cos(th - math.radians(-140))) / 2)
    ring = lambda off, w: np.exp(-((r - (R + off * N / 100)) / (w * N / 100)) ** 2)
    light = (np.array(rgb("#ffffff")) * (ring(0, 0.9) * (0.25 + 0.75 * lobe ** 4))[..., None]
             + np.array(rgb("#ff6a88")) * (ring(2, 2.6) * (0.15 + 0.85 * lobe ** 2.5))[..., None] * 0.9
             + np.array(rgb("#ff2d55")) * (ring(6, 6) * (0.1 + 0.9 * lobe ** 2))[..., None] * 0.55
             + np.array(rgb("#7b4dff")) * (ring(13, 10) * (0.2 + 0.8 * lobe ** 2))[..., None] * 0.35) * (r > R)[..., None]
    body = body + light
    inside = np.clip((R - r) / SS, 0, 1)
    body = body * (1 - inside[..., None]) + np.array(rgb("#06080f")) * inside[..., None]
    body = body + np.exp(-((yy / N) / 0.42) ** 2)[..., None] * 0.06
    rgba = np.dstack([np.clip(body, 0, 1), mask])
    return Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), "RGBA").resize((size, size), Image.LANCZOS)


def calendar_icon(size, day="17", month="MAR."):
    N = size * SS
    base = _compose(size, "#ffffff", "#e9ebf0", lambda d, n: None)
    big = base.resize((N, N), Image.LANCZOS)
    d = ImageDraw.Draw(big)
    f1 = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", int(N * 0.15))
    f2 = ImageFont.truetype("/usr/share/fonts/opentype/inter/InterDisplay-Light.otf", int(N * 0.52))
    d.text((N / 2, N * 0.27), month, font=f1, fill=(236, 0, 45, 255), anchor="mm")
    d.text((N / 2, N * 0.62), day, font=f2, fill=(29, 29, 31, 255), anchor="mm")
    return big.resize((size, size), Image.LANCZOS)


SPECS = {
    "fichiers":  ("#3b9bff", "#0a5fe0", g_files, None),
    "navigateur": ("#6f7bff", "#3a2fd1", g_browser, None),
    "terminal":  ("#3a3f4b", "#121419", g_terminal, None),
    "reglages":  ("#a7adb8", "#5c6370", g_settings, None),
    "store":     ("#ff6a88", "#e5103f", g_store, None),
    "photos":    ("#ffb340", "#ff2d55", g_photos, None),
    "musique":   ("#c86bff", "#6a35e8", g_music, None),
    "corbeille": ("#e8ecf3", "#b9c0cc", g_trash, None),
}


def icon(name, size):
    if name == "assistant":
        return eclipse_icon(size)
    if name == "calendrier":
        return calendar_icon(size)
    top, bot, fn, _ = SPECS[name]
    dark = name == "corbeille"
    return _compose(size, top, bot, fn, glyph_color=(0.30, 0.33, 0.39) if dark else (1, 1, 1), dark_glyph=dark)


if __name__ == "__main__":
    names = ["fichiers", "navigateur", "store", "photos", "musique", "calendrier", "assistant", "terminal", "reglages", "corbeille"]
    size = 256
    sheet = Image.new("RGBA", (len(names) * (size + 40) + 40, size + 80), (5, 7, 12, 255))
    for i, n in enumerate(names):
        im = icon(n, size)
        sheet.alpha_composite(im, (40 + i * (size + 40), 40))
    sheet.save("/tmp/aura/icons-sheet.png")
    print("ok")
