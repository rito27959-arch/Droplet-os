#!/usr/bin/env python3
"""Droplet window decoration (KWin Aurorae): renders DropletSombre / DropletClair.

Metrics from the Apple macOS 27 kit (documentation/MACOS27-MESURES.md): title bar 32 px,
corner radius 16 (Aurorae can only round the top corners: the client paints the bottom ones),
traffic lights 14 px with 9 px gaps, window background #FFFFFF / #1E1E1E, active shadow
0/+18/54 at 30 % (light) or 57 % (dark), inactive 0/+7/21 at 20 % / 35 %, 1 px contact outline.
All baked into the 9-slice frame SVG that Aurorae stretches. Usage: aurorae.py OUTDIR
"""
import base64, io, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

PAD_L = PAD_R = 56
PAD_T, PAD_B = 40, 80
TH, R = 32, 16
BTN, BTN_GAP = 14, 9

THEMES = {
    "DropletSombre": dict(title=(30, 30, 30), client=(30, 30, 30), text="217,217,217", text_in="115,115,115",
                          rim=(255, 255, 255, 0.20), outline=(0, 0, 0, 0.80), shadow=0.57, shadow_in=0.35,
                          sep=0.0, inactive_title=(30, 30, 30), off="#3a3a3a", off_border="#2e2e2e"),
    "DropletClair": dict(title=(255, 255, 255), client=(255, 255, 255), text="38,38,38", text_in="166,166,166",
                         rim=(255, 255, 255, 0.0), outline=(0, 0, 0, 0.28), shadow=0.30, shadow_in=0.20,
                         sep=0.0, inactive_title=(255, 255, 255), off="#dcdcdc", off_border="#cfcfcf"),
}
LIGHTS = {  # fill (kit), border, glyph
    "close": ("#f06e6a", "#d65651", "#4d0000"),
    "minimize": ("#ffcd30", "#e0ac16", "#985700"),
    "maximize": ("#58c73b", "#3ead25", "#006500"),
}


def rrect_mask(H, W, x0, y0, x1, y1, r, top_only=True, ss=4):
    """anti-aliased mask of a rect whose top corners are rounded (bottom corners square)."""
    yy, xx = (np.mgrid[0:H * ss, 0:W * ss] + 0.5) / ss
    inside = (xx >= x0) & (xx <= x1) & (yy >= y0) & (yy <= y1)
    for cx in (x0 + r, x1 - r):
        cy = y0 + r
        corner = ((xx < x0 + r) if cx == x0 + r else (xx > x1 - r)) & (yy < cy)
        inside &= ~corner | ((xx - cx) ** 2 + (yy - cy) ** 2 <= r * r)
    return inside.reshape(H, ss, W, ss).mean(axis=(1, 3))


def render_frame(t, active=True, maximized=False):
    """returns RGBA float image of the template window."""
    pl, pr, pt, pb = (0, 0, 0, 0) if maximized else (PAD_L, PAD_R, PAD_T, PAD_B)
    W, H = pl + 2 * R + 40 + pr, pt + TH + 40 + pb
    x0, y0, x1, y1 = pl, pt, W - pr, H - pb
    r = 0 if maximized else R
    win = rrect_mask(H, W, x0, y0, x1, y1, r) if r else np.zeros((H, W))
    if not r:
        win[y0:y1, x0:x1] = 1
    img = np.zeros((H, W, 4))
    if not maximized:
        # Figma blur radius b ~ gaussian sigma b / 2
        k = t["shadow"] if active else t["shadow_in"]
        amb = gaussian_filter(np.roll(win, 18 if active else 7, axis=0), 27 if active else 10.5) * k
        contact = gaussian_filter(win, 0.5) * 0.25
        a = 1 - (1 - amb) * (1 - contact)
        img[..., 3] = a  # black shadow
    # window body: title bar (top TH rows) + client colour below
    body = np.zeros((H, W, 3))
    body[:] = np.array(t["client"]) / 255
    title = t["title"] if active else t["inactive_title"]
    body[: y0 + TH] = np.array(title) / 255
    # 1 px hairline under the title bar
    sep = np.array(t["outline"][:3]) / 255
    body[y0 + TH - 1] = body[y0 + TH - 1] * (1 - t["sep"]) + sep * t["sep"]
    # inner rim (top-lit): along the rounded top edge
    if not maximized:
        inner = rrect_mask(H, W, x0 + 1, y0 + 1, x1 - 1, y1 - 1, r - 1)
        rim = np.clip(win - inner, 0, 1)
        fade = np.ones((H, 1))      # kit: uniform inside stroke (dark mode, white 20 %)
        rr, rg, rb, ra = t["rim"]
        body = body * (1 - rim[..., None] * ra * fade[..., None]) + np.array([rr, rg, rb]) / 255 * rim[..., None] * ra * fade[..., None]
    # composite body over shadow
    a_s = img[..., 3]
    out = np.zeros_like(img)
    out[..., :3] = body * win[..., None]
    out[..., 3] = win + a_s * (1 - win)
    # outline just outside the window (darker edge that separates it from the desktop)
    if not maximized:
        grow = gaussian_filter(win, 0.6) > 0.02
        ring = np.clip(grow.astype(float) - win, 0, 1)
        oa = t["outline"][3] * ring
        out[..., 3] = np.maximum(out[..., 3], oa + out[..., 3] * (1 - oa))
    # un-premultiply
    with np.errstate(invalid="ignore", divide="ignore"):
        rgb = np.where(out[..., 3:4] > 0, out[..., :3] / out[..., 3:4], 0)
    res = np.dstack([np.clip(rgb, 0, 1), np.clip(out[..., 3], 0, 1)])
    return res, (x0, y0, x1, y1), (W, H)


def png_b64(arr):
    im = Image.fromarray((arr * 255 + 0.5).astype(np.uint8), "RGBA")
    b = io.BytesIO(); im.save(b, "PNG", optimize=True)
    return base64.b64encode(b.getvalue()).decode()


def slices(img, rect, size, maximized):
    x0, y0, x1, y1 = rect
    W, H = size
    xa = x0 + (0 if maximized else R) + 2
    xb = W - (W - x1) - (0 if maximized else R) - 2
    ya = y0 + TH                      # top border = padding + title bar
    yb = y1 - 1                       # bottom border = 1 px outline + padding
    cols = {"left": (0, xa), "": (xa, xa + 4), "right": (xb, W)}
    rows = {"top": (0, ya), "": (ya, ya + 4), "bottom": (yb, H)}
    out = {}
    for rn, (r0, r1) in rows.items():
        for cn, (c0, c1) in cols.items():
            name = (rn + cn) or "center"
            if r1 > r0 and c1 > c0:
                out[name] = img[r0:r1, c0:c1]
    # side borders: shadow + 1 px outline (client sits inside)
    out["left"] = img[ya:ya + 4, 0:x0 + (0 if maximized else 1)]
    out["right"] = img[ya:ya + 4, x1 - (0 if maximized else 1):W]
    out["topleft"] = img[0:ya, 0:xa]
    out["topright"] = img[0:ya, xb:W]
    out["top"] = img[0:ya, xa:xa + 4]
    out["bottomleft"] = img[yb:H, 0:x0 + (0 if maximized else 1)]
    out["bottomright"] = img[yb:H, x1 - (0 if maximized else 1):W]
    out["bottom"] = img[yb:H, xa:xa + 4]
    out["center"] = img[ya:ya + 4, xa:xa + 4]
    return out


def decoration_svg(t):
    parts, x = [], 0
    for prefix, active, maxed in (("decoration", True, False), ("decoration-inactive", False, False),
                                  ("decoration-maximized", True, True), ("decoration-maximized-inactive", False, True)):
        img, rect, size = render_frame(t, active, maxed)
        y = 0
        for name, arr in slices(img, rect, size, maxed).items():
            h, w = arr.shape[:2]
            if h == 0 or w == 0:
                continue
            parts.append(f'<image id="{prefix}-{name}" x="{x}" y="{y}" width="{w}" height="{h}" '
                         f'preserveAspectRatio="none" xlink:href="data:image/png;base64,{png_b64(arr)}"/>')
            y += h + 2
        x += 400
    return ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{x}" height="1000">\n' + "\n".join(parts) + "\n</svg>\n")


GLYPHS = {
    "close": '<path d="M7.6 7.6 L12.4 12.4 M12.4 7.6 L7.6 12.4" stroke="{g}" stroke-width="1.3" stroke-linecap="round" fill="none"/>',
    "minimize": '<path d="M7.2 10 H12.8" stroke="{g}" stroke-width="1.4" stroke-linecap="round" fill="none"/>',
    "maximize": '<path d="M7.4 10 H12.6 M10 7.4 V12.6" stroke="{g}" stroke-width="1.3" stroke-linecap="round" fill="none"/>',
    "restore": '<path d="M7.4 10 H12.6" stroke="{g}" stroke-width="1.3" stroke-linecap="round" fill="none"/>',
}


def button_svg(kind, t):
    fill, border, glyph = LIGHTS["maximize" if kind == "restore" else kind]
    c = BTN / 2
    def circle(cx, f, b, extra="", dim=0.0):
        shade = f'<circle cx="{c}" cy="{c}" r="{c}" fill="#000" opacity="{dim}"/>' if dim else ""
        g = f'<g transform="translate({c - 10},{c - 10})">{extra}</g>' if extra else ""
        return (f'<circle cx="{c}" cy="{c}" r="{c - 0.25}" fill="{f}" stroke="{b}" stroke-width="0.5"/>' + shade + g)
    states = {
        "active": circle(10, fill, border),
        "hover": circle(10, fill, border, GLYPHS[kind].format(g=glyph)),
        "pressed": circle(10, fill, border, GLYPHS[kind].format(g=glyph), dim=0.18),
        "inactive": circle(10, t["off"], t["off_border"]),
        "deactivated": circle(10, t["off"], t["off_border"]),
    }
    groups = []
    for i, (state, body) in enumerate(states.items()):
        groups.append(f'<g id="{state}-center" transform="translate({i * (BTN + 4)},0)">'
                      f'<rect width="{BTN}" height="{BTN}" fill="none" opacity="0"/>{body}</g>')
    wsvg = 5 * (BTN + 4)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{wsvg}" height="{BTN}" viewBox="0 0 {wsvg} {BTN}">\n'
            + "\n".join(groups) + "\n</svg>\n")


def rc(t):
    return f"""[General]
ActiveTextColor={t['text']}
InactiveTextColor={t['text_in']}
TitleAlignment=Center
TitleVerticalAlignment=Center
Animation=120
Shadow=true

[Layout]
BorderLeft=1
BorderRight=1
BorderBottom=1
TitleEdgeTop=0
TitleEdgeBottom=0
TitleEdgeLeft=12
TitleEdgeRight=12
TitleBorderLeft=8
TitleBorderRight=8
TitleHeight={TH}
ButtonWidth={BTN}
ButtonHeight={BTN}
ButtonSpacing={BTN_GAP}
ButtonMarginTop={(TH - BTN) // 2}
ExplicitButtonSpacer=10
PaddingTop={PAD_T}
PaddingBottom={PAD_B}
PaddingLeft={PAD_L}
PaddingRight={PAD_R}
TitleEdgeTopMaximized=0
TitleEdgeBottomMaximized=0
TitleEdgeLeftMaximized=12
TitleEdgeRightMaximized=12
TitleBorderLeftMaximized=8
TitleBorderRightMaximized=8
TitleHeightMaximized={TH}
"""


def main(out):
    for name, t in THEMES.items():
        d = Path(out) / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "decoration.svg").write_text(decoration_svg(t))
        for kind in ("close", "minimize", "maximize", "restore"):
            (d / f"{kind}.svg").write_text(button_svg(kind, t))
        (d / f"{name}rc").write_text(rc(t))
        pretty = "Droplet sombre" if name.endswith("Sombre") else "Droplet clair"
        (d / "metadata.desktop").write_text(
            f"[Desktop Entry]\nName={pretty}\nComment=Décoration de fenêtre de Droplet OS\n"
            f"X-KDE-PluginInfo-Name={name}\nX-KDE-PluginInfo-Version=0.2\nX-KDE-PluginInfo-License=GPL-3.0\n"
            "X-KDE-PluginInfo-Author=Droplet OS\n")
        (d / "metadata.json").write_text(json.dumps({"KPlugin": {
            "Id": name, "Name": pretty, "Description": "Décoration de fenêtre de Droplet OS",
            "Version": "0.2", "License": "GPL-3.0", "Authors": [{"Name": "Droplet OS"}]},
            "X-Plasma-API": "declarativeappletscript"}, ensure_ascii=False, indent=1))
        print(d)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "aurorae")
