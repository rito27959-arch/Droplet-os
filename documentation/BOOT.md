# DROPLET BOOT — design and implementation

## Concept: "Prismatic Eclipse" + liquid logotype

1. Absolute black (Obsidian `#08090D`), the sphere is invisible.
2. A hairline of light crosses the screen from the left.
3. It strikes a dark-glass sphere and wraps around its edge, dispersing into a thin
   prismatic band (cyan → electric blue → violet).
4. The corona closes; light settles at the upper right. A brief "diamond ring" glint.
5. The **DROPLET** logotype condenses out of water beads (left → right), the beads
   coalesce into the letters, the surface settles with a damped ripple.
6. Idle: the light drifts slowly round the rim; reflections in the water follow it.
7. Slow boot only (> 3.6 s): a liquid progress thread with a rounded meniscus.

Design principles (research): macOS restraint (one mark, a thin progress bar shown late),
Fedora/GNOME flicker-free continuity (same background from GRUB to the end), pre-rendered
frame sequences for effects Plymouth cannot compute live.

## Logotype

`boot/plymouth/render/glyphs.py` — original monoline geometric letterforms built from
analytic distance fields (no font): stroke 0.17 cap, round terminals (surface tension),
a perfectly circular **O** echoing the eclipse.

## Water material (`liquid.py`)

Clear water: no body colour. Fresnel rim, inner thickness band, caustic on the lower
edge, sharp specular from the eclipse, plus the eclipse ring reflected and refracted
(inverted) in every curved stroke. Light angle is shared with the corona each frame.

## Pipeline

```
render/eclipse.py          Scene (preview videos, stills, login/password/shutdown mock-ups)
render/export_plymouth.py  -> boot/plymouth/droplet/   (~290 PNG, 7.6 MB, + droplet.script)
render/droplet.script.in   Plymouth script template (geometry injected at export)
```

Plymouth only swaps images (25 fps on its 50 Hz refresh): no GPU requirement, works on
simpledrm / efifb. Frames are opaque, ordered-dithered only where they differ from the
background, so their edges are bit-identical to Plymouth's background (no visible box).

Modes handled by the script: `boot`, `shutdown`/`reboot` (reverse sequence), disk
unlock prompt (pre-rendered French text, water-bead bullets), system messages.

## Fallbacks

- Script or image failure → Plymouth's built-in text splash; boot is never blocked.
- GRUB menu (Esc): *Graphismes sans échec* (`nomodeset`), *Diagnostic* (no splash, serial),
  *Récupération* (`rescue.target`).
- `plymouth.enable=0` on the kernel command line disables the splash.

## Known limits (0.1)

- Frames are 1x (1080p-class). On HiDPI screens Plymouth applies its device scale.
  A 2x set can be exported but doubles initramfs size (~+20 MB) — decision for 0.2.
- The login screen and the eclipse-as-avatar transition are designed (mock-ups) but
  need the graphical session (SDDM theme, 0.2). In 0.1 the splash hands off to tty1,
  which is cleared by `droplet-clear-console.service`.
- No startup sound (removed by product decision).

## Regenerate

```bash
cd boot/plymouth
python3 render/export_plymouth.py droplet                   # theme
python3 render/eclipse.py boot /tmp/preview 1920x1080 9     # preview video
python3 render/eclipse.py password /tmp/preview 3840x2160   # 4K still
```
