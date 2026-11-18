#!/usr/bin/env python3
"""Runs desktop/effects/liquidglass/liquidglass.frag offline (OpenGL via Mesa llvmpipe, EGL).

The same GLSL file is what the compositor effect uses, so a prototype rendered here is the
material the system will draw. Usage (library):

    gl = GlassGL(W, H)
    img = gl.apply(img, rect=(x, y, w, h), radius=22, **GlassGL.REGULAR_DARK)
"""
from pathlib import Path
import moderngl
import numpy as np

SHADER = Path(__file__).resolve().parents[2] / "desktop/effects/liquidglass/liquidglass.frag"

VERT = """#version 330
in vec2 pos; out vec2 v_uv;
void main() { v_uv = pos * 0.5 + 0.5; gl_Position = vec4(pos, 0.0, 1.0); }
"""


class GlassGL:
    # material presets in 1x points (multiplied by the render scale)
    REGULAR_DARK = dict(bevel=16, refraction=7, dispersion=0.8, frost=3.5, tintColor=(0.05, 0.06, 0.09),
                        tintAmount=0.20, saturation=1.6, brightness=0.0, specular=0.9,
                        shadowAlpha=0.28, shadowBlur=24, shadowY=8)
    REGULAR_LIGHT = dict(bevel=16, refraction=7, dispersion=0.7, frost=3.5, tintColor=(1.0, 1.0, 1.0),
                         tintAmount=0.26, saturation=1.5, brightness=0.03, specular=1.0,
                         shadowAlpha=0.14, shadowBlur=24, shadowY=8)
    CLEAR = dict(bevel=14, refraction=7, dispersion=0.8, frost=1.0, tintColor=(0, 0, 0),
                 tintAmount=0.08, saturation=1.3, brightness=0.0, specular=0.95,
                 shadowAlpha=0.12, shadowBlur=18, shadowY=6)

    @staticmethod
    def material(dark, w, h):
        """Size-adaptive material measured on the Apple macOS 27 kit (Materials / Liquid Glass):
        frost 6 for small controls, 16 for panels and the Dock, 25 for menus and large popups;
        shadow 0/+18/48 at 25 % (light) or 45 % (dark) for panels, almost none for small controls.
        Must stay identical to materialFor() in dropletglass.cpp."""
        md = min(w, h)
        s = min(max((md - 44) / 56, 0), 1)          # 0 = small control, 1 = panel
        big = min(max((md - 100) / 80, 0), 1)       # menus, launcher, large popups
        mix = lambda a, b, k: a + (b - a) * k
        m = dict(bevel=mix(10, 18, s), refraction=7, dispersion=0.35, frost=6 + 10 * s + 9 * big,
                 shadowBlur=mix(10, 40, s), shadowY=mix(3, 14, s), lumaTarget=0.0, lumaAmount=0.0)
        if dark:
            m.update(tintColor=(0.10, 0.10, 0.10), tintAmount=0.0, saturation=1.35, brightness=0.0,
                     specular=0.75, shadowAlpha=mix(0.12, 0.40, s), lumaTarget=0.10,
                     lumaAmount=mix(0.55, 0.75, s), rimDark=0.0, edgeGlow=0.06)
        else:
            m.update(tintColor=(1.0, 1.0, 1.0), tintAmount=mix(0.42, 0.62, s), saturation=1.25,
                     brightness=0.0, specular=0.85, shadowAlpha=mix(0.06, 0.22, s), rimDark=0.10,
                     edgeGlow=0.05)
        return m

    def __init__(self, W, H, scale=2):
        self.W, self.H, self.s = W, H, scale
        self.ctx = moderngl.create_standalone_context(backend="egl")
        self.prog = self.ctx.program(vertex_shader=VERT, fragment_shader=SHADER.read_text())
        quad = np.array([-1, -1, 1, -1, -1, 1, 1, 1], "f4")
        self.vao = self.ctx.vertex_array(self.prog, [(self.ctx.buffer(quad), "2f", "pos")])
        self.fbo = self.ctx.simple_framebuffer((W, H), components=4, dtype="f4")
        self.tex = self.ctx.texture((W, H), 3, dtype="f4")
        self.tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)

    def apply(self, img, rect, radius, light=(-0.3, -0.95), **m):
        """img: HxWx3 float (top row first). rect/radius and material lengths in points."""
        s = self.s
        self.tex.write(np.ascontiguousarray(img, dtype="f4").tobytes())   # texture y=0 = top row
        self.tex.build_mipmaps()                                       # the shader frosts on the mip chain
        self.tex.use(0)
        u = self.prog
        u["bg"].value = 0
        u["res"].value = (self.W, self.H)
        u["rect"].value = tuple(v * s for v in rect)
        u["radius"].value = min(radius, rect[2] / 2, rect[3] / 2) * s
        u["bevel"].value = min(m["bevel"], radius, rect[3] / 2) * s
        for k in ("refraction", "frost", "shadowBlur", "shadowY"):
            u[k].value = m[k] * s
        for k in ("dispersion", "tintAmount", "saturation", "brightness", "specular", "shadowAlpha"):
            u[k].value = m[k]
        if "maxLod" in u:
            u["maxLod"].value = m.get("maxLod", 4.0)
        for k in ("lumaTarget", "lumaAmount", "rimDark", "edgeGlow"):
            if k in u:
                u[k].value = m.get(k, 0.0)
        u["tintColor"].value = tuple(m["tintColor"])
        ln = np.array(light, float); ln /= np.linalg.norm(ln)   # toward the light
        u["lightDir"].value = tuple(ln)
        self.fbo.use()
        if getattr(self, "scissor_only", False):     # benchmark: shade only the shape (+ shadow), like KWin
            pad = (m["shadowBlur"] + m["shadowY"] + 2) * s
            x, y, w, h = (v * s for v in rect)
            self.fbo.scissor = (int(x - pad), int(self.H - (y + h + pad)), int(w + 2 * pad), int(h + 2 * pad))
        self.vao.render(moderngl.TRIANGLE_STRIP)
        self.fbo.scissor = None
        out = np.frombuffer(self.fbo.read(components=4, dtype="f4"), "f4").reshape(self.H, self.W, 4)
        return out[::-1, :, :3].copy()
