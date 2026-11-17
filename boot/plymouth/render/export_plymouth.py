#!/usr/bin/env python3
"""Export the DROPLET splash as a Plymouth script theme.

Plymouth cannot render glass/liquid in real time, so every frame is computed
here (same Scene as the preview videos) and Plymouth only swaps images:
  intro-N.png    eclipse + liquid wordmark, 0 -> 3.3 s       (25 fps)
  idle-N.png     light drift, played forward/backward forever (seamless ping-pong)
  beam-N.png     the incoming light beam, left of the main region
  bar-N.png      liquid progress bar, one image per progress step
  shut-N.png, shutbeam-N.png   shutdown / reboot sequence
  pw-*.png       disk-unlock prompt (pre-rendered text: no font needed in initramfs)
and writes droplet.script with the measured geometry.

  export_plymouth.py <theme_dir>
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from eclipse import OBSIDIAN, MUTED, WHITE, Scene, ease_in_out, rounded_rect_alpha, smooth, text_alpha
from liquid import bead_row, shade

FPS = 25
BAYER = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], np.float32) + 0.5) / 16 - 0.5


def save_rgb(img, path):
    """Opaque frame; ordered dither only where the image differs from the background,
    so frame edges are bit-identical to Plymouth's background colour."""
    h, w = img.shape[:2]
    d = np.tile(BAYER, (h // 4 + 1, w // 4 + 1))[:h, :w][..., None] / 255
    diff = np.abs(img - OBSIDIAN).max(axis=2, keepdims=True) > 1.5 / 255
    out = np.where(diff, img + d, OBSIDIAN)
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path, optimize=True)


def save_rgba_alpha(a, color, path):
    rgba = np.dstack([np.broadcast_to(color, a.shape + (3,)), a])
    Image.fromarray((np.clip(rgba, 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(path, optimize=True)


def save_pm(pm, path):
    a = pm[..., 3:4]
    rgb = np.where(a > 1e-4, pm[..., :3] / np.maximum(a, 1e-4), 0)
    Image.fromarray((np.clip(np.dstack([rgb, a]), 0, 1) * 255 + 0.5).astype(np.uint8), "RGBA").save(path, optimize=True)


def main(dest):
    dest = Path(dest); dest.mkdir(parents=True, exist_ok=True)
    for old in dest.glob("*.png"): old.unlink()
    sc = Scene(1920, 1080)
    sc.idle_w = math.pi / 3          # half period 3 s -> idle loop = 3.0 s, ping-pong
    BIG = 1e9
    lw_w, lw_h = sc.liquid.size
    RW = int(max(sc.box, lw_w + 24)) // 2 * 2
    rx0 = int(sc.cx - RW / 2)
    ry0 = sc.y0
    ry1 = int(sc.wm_y + lw_h / 2 + 4)
    crop = lambda f: f[ry0:ry1, rx0:rx0 + RW]

    # intro: 0 -> 3.3 s  (3.3 s = an extreme of the idle drift, so the loop joins smoothly)
    T_INTRO, T_IDLE = 3.3, 3.0
    n_intro, n_idle = int(T_INTRO * FPS), int(T_IDLE * FPS) + 1
    n_beam = int(1.0 * FPS)
    for i in range(n_intro):
        f = sc.boot(i / FPS, BIG, BIG)
        save_rgb(crop(f), dest / f"intro-{i}.png")
        if i < n_beam:
            yc = int(round(sc.cy))
            save_rgb(f[yc - 6:yc + 7, 0:rx0], dest / f"beam-{i}.png")
    for i in range(n_idle):
        save_rgb(crop(sc.boot(T_INTRO + i / FPS, BIG, BIG)), dest / f"idle-{i}.png")

    # liquid progress bar
    n_bar = 41
    la = sc.light_angle(T_INTRO, 1.0)
    for i in range(n_bar):
        pm = sc.bar.render(i / (n_bar - 1), 0.0, la)
        bg = np.zeros(pm.shape[:2] + (3,), np.float32) + OBSIDIAN
        h, w = pm.shape[:2]
        track = np.zeros((h, w), np.float32)
        tw = int(170 * sc.k); th = max(1, int(round(sc.k)))
        track[h // 2 - th // 2:h // 2 - th // 2 + th, (w - tw) // 2:(w - tw) // 2 + tw] = 0.08
        bg = bg + track[..., None] * (WHITE - bg)
        save_rgb(bg * (1 - pm[..., 3:4]) + pm[..., :3], dest / f"bar-{i}.png")
    bar_h, bar_w = pm.shape[:2]

    # shutdown / reboot
    n_shut, n_sbeam = int(1.6 * FPS), int(0.9 * FPS)
    for i in range(n_shut):
        save_rgb(crop(sc.shutdown(i / FPS)), dest / f"shut-{i}.png")
    for i in range(n_sbeam):
        f = sc.shutdown(1.5 + i / FPS)
        yc = int(round(sc.cy))
        save_rgb(f[yc - 6:yc + 7, 0:rx0], dest / f"shutbeam-{i}.png")

    # disk-unlock prompt
    k = sc.k
    save_rgba_alpha(text_alpha("Ce disque est chiffré", 22 * k, "Medium"), WHITE * 0.92 + OBSIDIAN * 0.08, dest / "pw-title.png")
    save_rgba_alpha(text_alpha("Saisissez la phrase secrète pour démarrer Droplet", 15 * k, "Regular"), MUTED, dest / "pw-subtitle.png")
    w, h = int(230 * k), int(38 * k)
    m = rounded_rect_alpha(w, h, h // 2)
    inner = rounded_rect_alpha(w - 2, h - 2, h // 2 - 1)
    rim = m.copy(); rim[1:-1, 1:-1] -= inner
    grad = np.linspace(1.0, 0.45, h, dtype=np.float32)[:, None]
    a = np.clip(m * 0.055 + np.clip(rim, 0, 1) * grad * 0.30, 0, 1)
    save_rgba_alpha(a, WHITE, dest / "pw-field.png")
    S, r = bead_row(1, 1, 13 * k)
    save_pm(shade(S, 2, r, -math.pi / 4), dest / "pw-bead.png")

    geom = dict(RW=RW, RH=ry1 - ry0, DX=rx0 - sc.cx, DY=ry0 - sc.cy, BEAM_W=rx0,
                BAR_DY=sc.bar_y - sc.cy, BAR_W=bar_w, BAR_H=bar_h,
                PW_TITLE_DY=sc.R + 56 * k, PW_SUB_DY=sc.R + 86 * k, PW_FIELD_DY=sc.R + 140 * k,
                PW_FIELD_W=w, BEAD_GAP=13 * k * 1.9,
                N_INTRO=n_intro, N_IDLE=n_idle, N_BEAM=n_beam, N_BAR=n_bar, N_SHUT=n_shut, N_SBEAM=n_sbeam)
    tpl = (Path(__file__).parent / "droplet.script.in").read_text()
    for key, val in geom.items():
        tpl = tpl.replace(f"@{key}@", f"{val:.0f}" if isinstance(val, float) else str(val))
    (dest / "droplet.script").write_text(tpl)
    (dest / "droplet.plymouth").write_text(
        "[Plymouth Theme]\nName=Droplet\nDescription=DROPLET BOOT — prismatic eclipse, liquid wordmark\n"
        "ModuleName=script\n\n[script]\nImageDir=/usr/share/plymouth/themes/droplet\n"
        "ScriptFile=/usr/share/plymouth/themes/droplet/droplet.script\n")
    size = sum(p.stat().st_size for p in dest.iterdir())
    print(f"theme -> {dest}  ({len(list(dest.glob('*.png')))} images, {size / 1e6:.1f} MB)", geom)


if __name__ == "__main__":
    main(sys.argv[1])
