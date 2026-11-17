#!/usr/bin/env python3
"""DROPLET BOOT — "Prismatic Eclipse" with liquid logotype (v3).

Sequences
  boot      : beam -> prismatic eclipse -> liquid wordmark condenses -> liquid progress
              -> handoff: wordmark evaporates, eclipse stays and becomes the login avatar
  shutdown  : wordmark evaporates -> corona retracts -> beam leaves -> black
  password  : disk-unlock prompt (encrypted storage), water-bead bullets

  eclipse.py boot     <outdir> [WxH] [seconds]
  eclipse.py shutdown <outdir> [WxH]
  eclipse.py password <outdir> [WxH]
  eclipse.py lite     <outdir> [WxH]     (single static frame for modest hardware)
"""
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from liquid import LiquidBar, LiquidWordmark, bead_row, shade

def c(h): return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)], np.float32)
OBSIDIAN, SPHERE, WHITE = c("#08090D"), c("#0B0E15"), c("#F5F7FC")
CYAN, ELECTRIC, SOFT, VIOLET, MUTED = c("#8FE3FF"), c("#3978F6"), c("#80A9FF"), c("#7B61FF"), c("#858D9D")
FPS = 50
INTER = "/usr/share/fonts/opentype/inter/InterDisplay-{}.otf"


def smooth(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
def ease_out(x):
    x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3
def ease_in_out(x):
    x = min(max(x, 0.0), 1.0); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2


def text_alpha(txt, px, weight="Light", tracking=0.0):
    s = 4
    font = ImageFont.truetype(INTER.format(weight), max(1, int(px * s)))
    w = font.getlength(txt) + tracking * px * s * len(txt) + 8
    img = Image.new("L", (int(w), int(px * s * 1.5)), 0)
    d, x = ImageDraw.Draw(img), 2
    for ch in txt:
        d.text((x, 0), ch, font=font, fill=255); x += font.getlength(ch) + tracking * px * s
    bb = img.getbbox()
    if not bb: return np.zeros((1, 1), np.float32)
    img = img.crop(bb)
    return np.asarray(img.resize((max(1, img.width // s), max(1, img.height // s)), Image.LANCZOS), np.float32) / 255


def rounded_rect_alpha(w, h, r, s=4):
    img = Image.new("L", (w * s, h * s), 0)
    ImageDraw.Draw(img).rounded_rectangle([0, 0, w * s - 1, h * s - 1], radius=r * s, fill=255)
    return np.asarray(img.resize((w, h), Image.LANCZOS), np.float32) / 255


def dither_save(img, path, rng=np.random.default_rng(0)):
    """Item 7: triangular dither before 8-bit quantisation -> no banding in dark gradients."""
    noise = (rng.random(img.shape, np.float32) - rng.random(img.shape, np.float32)) / 255
    Image.fromarray((np.clip(img + noise, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)


class Scene:
    def __init__(self, W, H):
        self.W, self.H, self.k = W, H, H / 1080
        self.idle_w = 0.45      # idle light drift (rad/s)
        k = self.k
        self.cx, self.cy = W / 2, H / 2 - 0.06 * H
        self.R = 64 * k
        box = int(self.R * 6)
        self.x0, self.y0, self.box = int(self.cx - box / 2), int(self.cy - box / 2), box
        yy, xx = np.mgrid[0:box, 0:box].astype(np.float32)
        dx, dy = xx + self.x0 - self.cx, yy + self.y0 - self.cy
        self.r, self.th = np.hypot(dx, dy), np.arctan2(dy, dx)
        self.liquid = LiquidWordmark(cap_px=48 * k)
        self.bar = LiquidBar(170 * k, 5 * k)
        self.wm_y = self.cy + self.R + 116 * k
        self.bar_y = self.cy + self.R + 196 * k

    # ---- light ---------------------------------------------------------------
    def light_angle(self, s, settle):
        """Brightest point of the corona; the liquid reflections follow it (item 2)."""
        return math.pi + (-math.pi / 4 - math.pi) * settle + 0.22 * math.sin(max(s - 1.8, 0) * self.idle_w)

    def corona(self, s, wrap, settle, intensity=1.0):
        r, th, R, k = self.r, self.th, self.R, self.k
        d_from_left = np.pi - np.abs(th)
        cover = smooth((wrap * np.pi * 1.25 - d_from_left) / 0.25)
        la = self.light_angle(s, settle)
        lobe = ((1 + np.cos(th - la)) / 2) ** 3
        bright = 0.16 + 0.84 * (lobe * settle + (1 - settle) * np.exp(-(d_from_left / 0.6) ** 2))
        def band(off, width): return np.exp(-((r - (R + off * k)) / (width * k)) ** 2)
        inner, mid, outer = band(-0.5, 1.0), band(1.0, 1.5), band(3.0, 2.6)
        glow = np.exp(-np.clip(r - R, 0, None) / (14 * k)) * (r > R - 1)
        haze = np.exp(-np.clip(r - R, 0, None) / (42 * k)) * (r > R - 1)
        disperse = 0.7 + 1.1 * math.exp(-((s - 0.95) / 0.35) ** 2) + 0.15 * float(smooth((s - 1.4) / 0.6))
        col = (WHITE * inner[..., None] * 0.95
               + (CYAN * 0.6 + ELECTRIC * 0.4) * mid[..., None] * 0.9 * disperse
               + VIOLET * outer[..., None] * 0.55 * disperse
               + ELECTRIC * glow[..., None] * 0.38 + SOFT * haze[..., None] * 0.10)
        return col * (cover * bright * intensity)[..., None]

    def glint(self, s):
        a = float(smooth((s - 1.30) / 0.12) * (1 - smooth((s - 1.50) / 0.45)))
        if a <= 0: return 0
        k = self.k; ang = -np.pi / 4
        gx, gy = self.cx + math.cos(ang) * (self.R + 0.6 * k), self.cy + math.sin(ang) * (self.R + 0.6 * k)
        dx = self.r * np.cos(self.th) + self.cx - gx
        dy = self.r * np.sin(self.th) + self.cy - gy
        core = np.exp(-(dx ** 2 + dy ** 2) / (3.2 * k) ** 2)
        rays = (np.exp(-(dy / (0.6 * k)) ** 2 - (dx / (12 * k)) ** 2) + np.exp(-(dx / (0.6 * k)) ** 2 - (dy / (8 * k)) ** 2)) * 0.30
        return WHITE * ((core + rays + np.exp(-(dx ** 2 + dy ** 2) / (11 * k) ** 2) * 0.25) * a)[..., None]

    def sphere(self, vis):
        inside = smooth((self.R - self.r) / (1.0 * self.k))
        refl = np.exp(-((self.r * np.sin(self.th) + self.R * 0.55) / (self.R * 0.28)) ** 2) * (self.r < self.R * 0.82) * 0.035 * vis
        body = OBSIDIAN + (SPHERE - OBSIDIAN) * vis
        return inside, body * inside[..., None] + WHITE * refl[..., None]

    def beam(self, f, head, fade, direction=1):
        if head <= 0 or fade <= 0: return
        k = self.k
        x_hit = self.cx - self.R
        xs = np.arange(self.W, dtype=np.float32)
        if direction > 0:     # arriving from the left edge
            xh = head * x_hit
            along = np.clip((xs - (xh - 0.45 * self.W)) / (0.45 * self.W), 0, 1) ** 2 * (xs <= xh)
            along += np.exp(-((xs - xh) / (6 * k)) ** 2) * 0.8
        else:                 # leaving towards the left edge
            xt = x_hit * (1 - head)
            along = np.clip((xs - xt) / max(x_hit - xt, 1), 0, 1) ** 0.5 * (xs >= xt) * (xs <= x_hit)
        ys = np.arange(-6, 7, dtype=np.float32)
        prof = np.exp(-(ys / (0.6 * k + 0.4)) ** 2)[:, None]
        yc = int(round(self.cy))
        f[yc - 6:yc + 7] += (prof * along[None, :] * fade)[..., None] * WHITE

    # ---- compositing helpers ---------------------------------------------------
    def put(self, f, pm, cx, cy):
        h, w = pm.shape[:2]
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
        reg = f[y0:y0 + h, x0:x0 + w]
        reg[:] = reg * (1 - pm[..., 3:4]) + pm[..., :3]

    def put_alpha(self, f, a, cx, cy, color, k=1.0):
        h, w = a.shape
        x0, y0 = int(round(cx - w / 2)), int(round(cy - h / 2))
        reg = f[y0:y0 + h, x0:x0 + w]
        reg[:] = reg + (a * k)[..., None] * (color - reg)

    def eclipse_layer(self, f, s, wrap, settle, intensity=1.0, sphere_vis=1.0, glint=True):
        reg = f[self.y0:self.y0 + self.box, self.x0:self.x0 + self.box]
        reg += self.corona(s, wrap, settle, intensity)
        inside, body = self.sphere(sphere_vis)
        reg[:] = reg * (1 - inside[..., None]) + body
        if glint: reg += self.glint(s)

    # ---- sequences --------------------------------------------------------------
    def boot(self, s, total, done_at):
        f = np.zeros((self.H, self.W, 3), np.float32) + OBSIDIAN
        self.beam(f, ease_in_out((s - 0.15) / 0.45), 1 - float(smooth((s - 0.65) / 0.35)))
        wrap, settle = ease_in_out((s - 0.55) / 0.60), ease_out((s - 0.9) / 0.9)
        self.eclipse_layer(f, s, wrap, settle, sphere_vis=float(smooth((s - 0.55) / 0.8)))
        la = self.light_angle(s, settle)
        # liquid wordmark: condenses, then evaporates when boot is done (item 4)
        tw = s - 1.25
        if tw > 0:
            out = s >= done_at
            pm = self.liquid.render(s - done_at if out else tw, la, out=out)
            self.put(f, pm, self.cx, self.wm_y)
        # liquid progress bar (item 3): fills with the boot, drains away at handoff
        ba = float(smooth((s - 3.6) / 0.4)) * (1 - float(smooth((s - done_at) / 0.35)))
        if ba > 0:
            w, h = int(170 * self.k), max(1, int(round(1 * self.k)))
            self.put_alpha(f, np.ones((h, w), np.float32), self.cx, self.bar_y, WHITE, 0.08 * ba)
            p = min(1.0, max(0.0, (s - 3.4) / (done_at - 3.4)))
            pm = self.bar.render(p, s, la) * ba
            self.put(f, pm, self.cx, self.bar_y)
        # login: the eclipse stays exactly in place and becomes the avatar
        lg = float(smooth((s - done_at - 0.7) / 0.7))
        if lg > 0:
            self.login_ui(f, lg)
        return np.clip(f, 0, 1)

    def login_ui(self, f, a):
        k = self.k
        # clock, macOS-like hierarchy
        self.put_alpha(f, text_alpha("mardi 17 novembre", 20 * k, "Medium"), self.cx, 96 * k, WHITE, 0.70 * a)
        self.put_alpha(f, text_alpha("13:12", 92 * k, "Light"), self.cx, 172 * k, WHITE, 0.92 * a)
        # avatar initial inside the sphere
        self.put_alpha(f, text_alpha("U", 46 * k, "Light"), self.cx, self.cy, SOFT, 0.85 * a)
        self.put_alpha(f, text_alpha("Utilisateur", 22 * k, "Medium"), self.cx, self.cy + self.R + 44 * k, WHITE, 0.92 * a)
        self.glass_field(f, self.cy + self.R + 104 * k, a, "Saisir le mot de passe")

    def glass_field(self, f, cy, a, placeholder, beads=0):
        k = self.k
        w, h = int(230 * k), int(38 * k)
        m = rounded_rect_alpha(w, h, h // 2)
        inner = rounded_rect_alpha(w - 2, h - 2, h // 2 - 1)
        rim = m.copy(); rim[1:-1, 1:-1] -= inner
        grad = np.linspace(1.0, 0.45, h, dtype=np.float32)[:, None]
        self.put_alpha(f, m, self.cx, cy, WHITE, 0.055 * a)                 # frosted fill
        self.put_alpha(f, np.clip(rim, 0, 1) * grad, self.cx, cy, WHITE, 0.30 * a)   # lit rim
        if beads:
            S, r = bead_row(beads, 12, 13 * k)
            pm = shade(S, 2, r, -math.pi / 4) * a
            self.put(f, pm, self.cx - w / 2 + 12 * k + pm.shape[1] / 2, cy)
        else:
            self.put_alpha(f, text_alpha(placeholder, 15 * k, "Regular"), self.cx, cy, MUTED, 0.9 * a)

    def shutdown(self, s):
        f = np.zeros((self.H, self.W, 3), np.float32) + OBSIDIAN
        retract = ease_in_out((s - 0.9) / 0.9)                 # corona unwinds to the left
        wrap = 1 - retract
        self.eclipse_layer(f, 3.0 + s, wrap, 1.0 - 0.6 * retract, sphere_vis=1 - float(smooth((s - 1.2) / 0.6)), glint=False)
        pm = self.liquid.render(s, self.light_angle(3.0 + s, 1.0), out=True)
        self.put(f, pm, self.cx, self.wm_y)
        self.beam(f, ease_in_out((s - 1.55) / 0.55), 1 - float(smooth((s - 2.0) / 0.3)), direction=-1)
        return np.clip(f, 0, 1)

    def password(self, beads=6):
        f = np.zeros((self.H, self.W, 3), np.float32) + OBSIDIAN
        self.eclipse_layer(f, 3.0, 1.0, 1.0, glint=False)
        k = self.k
        self.put_alpha(f, text_alpha("Ce disque est chiffré", 22 * k, "Medium"), self.cx, self.cy + self.R + 56 * k, WHITE, 0.92)
        self.put_alpha(f, text_alpha("Saisissez la phrase secrète pour démarrer Droplet", 15 * k, "Regular"),
                       self.cx, self.cy + self.R + 86 * k, MUTED, 0.95)
        self.glass_field(f, self.cy + self.R + 140 * k, 1.0, "", beads=beads)
        return np.clip(f, 0, 1)


def encode(fdir, mp4):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(fdir / "%04d.png"),
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p",
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", str(mp4)], check=True)


def main():
    mode, out = sys.argv[1], Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
    W, H = (int(v) for v in (sys.argv[3] if len(sys.argv) > 3 else "1920x1080").split("x"))
    sc = Scene(W, H)
    tag = f"{W}x{H}"
    if mode == "boot":
        total = float(sys.argv[4]) if len(sys.argv) > 4 else 9.0
        done_at = total - 2.4
        fdir = out / f"boot-{tag}"; fdir.mkdir(exist_ok=True)
        keys = [0.75, 1.38, 1.8, 2.15, 5.0, done_at + 0.45, total - 0.05]
        shots = []
        for i in range(int(total * FPS)):
            s = i / FPS
            img = sc.boot(s, total, done_at)
            dither_save(img, fdir / f"{i:04d}.png")
            if any(i == round(kt * FPS) for kt in keys): shots.append(img)
        encode(fdir, out / f"droplet-boot-{tag}.mp4")
        cw, ch = int(640 * sc.k), int(560 * sc.k)
        x0, y0 = int(sc.cx - cw / 2), int(sc.cy - 170 * sc.k)
        crops = [Image.fromarray((np.clip(im, 0, 1) * 255).astype(np.uint8)).crop((x0, y0, x0 + cw, y0 + ch)) for im in shots[:6]]
        sheet = Image.new("RGB", (cw * 3 + 16, ch * 2 + 8), (40, 40, 48))
        for n, im in enumerate(crops): sheet.paste(im, ((n % 3) * (cw + 8), (n // 3) * (ch + 8)))
        sheet.save(out / f"boot-keyframes-{tag}.png")
        dither_save(shots[4], out / f"boot-still-{tag}.png")
        dither_save(shots[-1], out / f"login-{tag}.png")
    elif mode == "shutdown":
        fdir = out / f"shutdown-{tag}"; fdir.mkdir(exist_ok=True)
        for i in range(int(2.6 * FPS)):
            dither_save(sc.shutdown(i / FPS), fdir / f"{i:04d}.png")
        encode(fdir, out / f"droplet-shutdown-{tag}.mp4")
    elif mode == "password":
        dither_save(sc.password(), out / f"password-{tag}.png")
    elif mode == "lite":
        dither_save(sc.boot(5.0, 9.0, 6.6), out / f"lite-{tag}.png")
    print("ok", mode, tag)


if __name__ == "__main__":
    main()
