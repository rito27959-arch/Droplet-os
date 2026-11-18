// Droplet — Liquid Glass material (GLSL 3.30). One pass per glass shape.
//
// This is the shader the KWin effect will run on the compositor side (where the pixels behind
// a surface are available). The offline prototype (aura/render/glassgl.py) runs this exact file.
//
// Model: a slab of glass with a rounded-rectangle footprint whose rim is a convex bevel.
//  * lensing     - across the bevel the surface normal tilts, rays bend: the background is
//                  displaced (magnified toward the rim), the flat centre stays undistorted
//  * dispersion  - red / green / blue bend by different amounts at the rim
//  * frost       - a light blur (regular variant) so text on top stays legible
//  * adaptivity  - luminosity pulled toward a tint that depends on what is behind
//  * specular    - light from the upper-left: a bright thin edge + a broad sheen on the bevel,
//                  a fainter counter-reflection on the opposite rim
//  * shadow      - soft contact shadow under the slab
#version 330
// (KWin replaces the line above with its own #version and defines KWIN.)

uniform sampler2D bg;
uniform vec2  res;          // offline: framebuffer size (px)
uniform vec4  rect;         // x, y, w, h (px, top-left origin)
uniform float radius;       // corner radius (px)
uniform float bevel;        // width of the curved rim (px)
uniform float refraction;   // max displacement at the rim (px)
uniform float dispersion;   // 0..1 spread between R and B
uniform float frost;        // blur radius (px)
uniform vec3  tintColor;
uniform float tintAmount;   // 0..1
uniform float saturation;   // 1 = unchanged
uniform float brightness;   // added after tint (-1..1)
uniform float lumaTarget;   // luminosity blend (macOS dark glass): pull luminance to this value,
uniform float lumaAmount;   //   keeping hue and saturation of what is behind (0 = off)
uniform float rimDark;      // hairline just inside the edge (light mode outline, Linear Burn in the kit)
uniform float edgeGlow;
uniform float maxLod;
uniform int   debugView;
uniform float presence;     // 0..1: the shape materialising / dissolving (compositor animation)    // 0 normal, 1 raw capture, 2 frosted capture (diagnostics)       // deepest mip level available to the frost (0 disables the mip chain)     // inner glow along the top and bottom edges (kit: inner shadows ±40, Dodge)
uniform vec2  lightDir;     // normalised, pointing *toward* the light, y down
uniform float specular;     // 0..1
uniform float shadowAlpha;
uniform float shadowBlur;   // px
uniform float shadowY;      // px

#ifdef KWIN
in vec2 lpos;               // logical pixel position (global)
uniform vec4 capRect;       // where the captured background lies (logical px)
#define PIXEL_POS lpos
#define TEX_LO (capRect.xy + 0.5)
#define TEX_HI (capRect.xy + capRect.zw - 0.5)
#define TEX_UV(px) vec2(((px).x - capRect.x) / capRect.z, 1.0 - ((px).y - capRect.y) / capRect.w)
#else
in vec2 v_uv;
#define PIXEL_POS (vec2(v_uv.x, 1.0 - v_uv.y) * res)
#define TEX_LO vec2(0.5)
#define TEX_HI (res - 0.5)
#define TEX_UV(px) ((px) / res)
#endif
out vec4 frag;

float sdRoundRect(vec2 p) {
    vec2 c = rect.xy + rect.zw * 0.5;
    vec2 q = abs(p - c) - rect.zw * 0.5 + radius;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - radius;
}

// analytic outward normal of the rounded rectangle (one evaluation instead of four)
vec2 sdNormal(vec2 p) {
    vec2 c = rect.xy + rect.zw * 0.5;
    vec2 sp = sign(p - c);
    vec2 q = abs(p - c) - rect.zw * 0.5 + radius;
    if (q.x > 0.0 && q.y > 0.0) return normalize(q) * sp;     // in a corner
    return q.x > q.y ? vec2(sp.x, 0.0) : vec2(0.0, sp.y);     // along a side
}

vec3 tex(vec2 px) { return texture(bg, TEX_UV(clamp(px, TEX_LO, TEX_HI))).rgb; }
vec3 texLod(vec2 px, float lod) { return textureLod(bg, TEX_UV(clamp(px, TEX_LO, TEX_HI)), lod).rgb; }

// frost: 9 taps on the mip chain (the capture is mipmapped) instead of a 40-tap spiral.
// The level is chosen so that one texel is about half the blur radius; a ring of 8 taps
// at 0.7 r fills in a smooth, roughly gaussian footprint.
vec3 frosted(vec2 px, float r) {
    if (r < 0.5) return tex(px);
    float lod = clamp(log2(r) - 0.5, 0.0, maxLod);
    vec3 acc = texLod(px, lod) * 2.0;
    const float c = 0.70710678;
    vec2 o[8] = vec2[8](vec2(1, 0), vec2(-1, 0), vec2(0, 1), vec2(0, -1),
                        vec2(c, c), vec2(-c, c), vec2(c, -c), vec2(-c, -c));
    for (int i = 0; i < 8; ++i) acc += texLod(px + o[i] * r * 0.7, lod);
    // when the mip level is capped, a second, inner ring keeps the footprint smooth
    if (log2(r) - 0.5 > maxLod + 0.5) {
        for (int i = 0; i < 8; ++i) acc += texLod(px + o[i].yx * r * 0.35, lod);
        return acc / 18.0;
    }
    return acc / 10.0;
}

void main() {
    vec2 p = PIXEL_POS;                            // pixel, top-left origin
    float d = sdRoundRect(p);

    // ---- contact shadow (outside the slab)
    float ds = sdRoundRect(p - vec2(0.0, shadowY));
    float sh = shadowAlpha * (1.0 - smoothstep(-shadowBlur * 0.35, shadowBlur, ds));
    float alpha = clamp(0.5 - d, 0.0, 1.0);
#ifndef KWIN
    vec3 col = mix(tex(p), vec3(0.0), sh * smoothstep(-1.0, 1.0, d));
#endif
#ifdef KWIN
    // composited with premultiplied blending: outside the slab only the shadow is painted, so
    // neighbouring shapes (and their glass) are never overwritten
    if (alpha <= 0.0) { frag = vec4(0.0, 0.0, 0.0, sh * smoothstep(-1.0, 1.0, d) * presence); return; }
#else
    if (alpha <= 0.0) { frag = vec4(col, 1.0); return; }
#endif

    // ---- lens: bevel profile (a rounded slab: quarter-circle rim, flat top)
    float e = -d;                                   // distance inside the edge
    float t = clamp(1.0 - e / bevel, 0.0, 1.0);     // 1 at the edge, 0 on the flat top
    vec2 n = sdNormal(p);                           // outward
    // slope of a circular rim -> refraction grows sharply toward the edge; the rim gathers
    // light from *outside* the shape (that is what makes glass look thick)
    float slope = t / sqrt(max(1.0 - t * t, 0.04));
    float bend = refraction * min(slope, 5.0) * 0.45;
    vec2 base = p + n * bend;

    vec3 g = frosted(base, frost);
#ifdef KWIN
    if (debugView == 1) { frag = vec4(tex(p) * alpha, alpha); return; }
    if (debugView == 2) { frag = vec4(g * alpha, alpha); return; }
#endif
    if (dispersion > 0.0 && t > 0.0) {
        // dispersion only exists on the rim: two extra taps shift red out and blue in
        float k = dispersion * t * 0.5;
        float lod = clamp(log2(max(frost, 1.0)) - 0.5, 0.0, maxLod);
        vec3 rs = texLod(base + n * bend * k, lod), bs = texLod(base - n * bend * k, lod);
        vec3 cs = texLod(base, lod);
        g.r += rs.r - cs.r;
        g.b += bs.b - cs.b;
    }

    // ---- material: saturation, adaptive tint, luminosity
    float L = dot(g, vec3(0.2126, 0.7152, 0.0722));
    g = mix(vec3(L), g, saturation);
    g = mix(g, tintColor, tintAmount * (1.0 - 0.45 * t));   // the rim stays clearer than the face
    if (lumaAmount > 0.0) {
        float L2 = dot(g, vec3(0.2126, 0.7152, 0.0722));
        g += (lumaTarget - L2) * lumaAmount * (1.0 - 0.35 * t);
        g = max(g, vec3(lumaTarget * 0.9));                  // the kit's Lighten layer: a floor
    }
    g += brightness;

    // ---- light: the slab's rim catches the light on the lit side and on the opposite corner
    float facing = dot(n, lightDir);                // > 0: rim turned toward the light
    float lit = max(facing, 0.0);
    float back = max(-facing, 0.0);
    float edge = exp(-e / 1.5);                     // thin bright line
    float band = smoothstep(0.0, 1.0, t) * (1.0 - smoothstep(0.85, 1.0, t)); // inside the rim
    float spec = specular * (edge * (0.20 + 1.10 * pow(lit, 1.5) + 0.55 * pow(back, 2.0))
                            + band * (0.45 * pow(lit, 2.0) + 0.18 * pow(back, 3.0)));
    // the far side of the rim is thicker glass: slightly darker
    g *= 1.0 - 0.16 * t * back;
    // soft glow inside the top and bottom edges (the kit paints it with two inner shadows)
    float dTop = p.y - rect.y, dBot = rect.y + rect.w - p.y;
    float glowW = clamp(min(rect.z, rect.w) * 0.18, 4.0, 12.0);
    g += edgeGlow * (exp(-dTop / glowW) + exp(-dBot / glowW));
    g *= 1.0 - rimDark * (1.0 - smoothstep(0.0, 1.2, e));
    g = g + (1.0 - g) * clamp(spec, 0.0, 1.0);

#ifdef KWIN
    alpha *= presence;
    frag = vec4(clamp(g, 0.0, 1.0) * alpha, alpha);
#else
    frag = vec4(mix(col, clamp(g, 0.0, 1.0), alpha), 1.0);
#endif
}
