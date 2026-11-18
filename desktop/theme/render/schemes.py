#!/usr/bin/env python3
"""Droplet colour schemes (KDE .colors) + system defaults (kdeglobals, kwinrc) from the Aura tokens.
Usage: schemes.py OUTDIR  -> OUTDIR/color-schemes/*.colors, OUTDIR/xdg/{kdeglobals,kwinrc}"""
import sys
from pathlib import Path

ACCENT = "236,0,45"          # goutte-remplie: carries white text (4.55:1)
SCHEMES = {
    # window / view: kit Window Background #1E1E1E / #FFFFFF; text: Labels Primary 85 %, Secondary 55 / 50 %
    "DropletSombre": dict(name="Droplet sombre", window="30,30,30", view="30,30,30", alt="37,37,37",
                          button="56,56,56", fg="217,217,217", inactive="140,140,140", link="255,55,95",
                          visited="191,90,242", negative="255,69,58", neutral="255,159,10", positive="48,209,88",
                          tooltip="42,44,51", focus="255,55,95", contrast=4),
    "DropletClair": dict(name="Droplet clair", window="255,255,255", view="255,255,255", alt="245,245,245",
                         button="255,255,255", fg="38,38,38", inactive="128,128,128", link="255,45,85",
                         visited="175,82,222", negative="209,43,33", neutral="159,83,0", positive="16,122,67",
                         tooltip="246,246,248", focus="255,45,85", contrast=3),
}


def group(s, bg, alt=None, fg=None):
    fg = fg or s["fg"]
    return "\n".join([
        f"BackgroundAlternate={alt or s['alt']}", f"BackgroundNormal={bg}",
        f"DecorationFocus={s['focus']}", f"DecorationHover={s['focus']}",
        f"ForegroundActive={s['link']}", f"ForegroundInactive={s['inactive']}",
        f"ForegroundLink={s['link']}", f"ForegroundNegative={s['negative']}",
        f"ForegroundNeutral={s['neutral']}", f"ForegroundNormal={fg}",
        f"ForegroundPositive={s['positive']}", f"ForegroundVisited={s['visited']}"])


def colors(sid, s):
    sel = dict(s, link="255,255,255", inactive="255,214,222")
    return f"""[ColorEffects:Disabled]
Color=56,56,56
ColorAmount=0
ColorEffect=0
ContrastAmount=0.65
ContrastEffect=1
IntensityAmount=0.1
IntensityEffect=2

[ColorEffects:Inactive]
ChangeSelectionColor=false
Enable=false

[Colors:Button]
{group(s, s['button'])}

[Colors:Complementary]
{group(SCHEMES['DropletSombre'], '22,24,31')}

[Colors:Header]
{group(s, s['window'])}

[Colors:Header][Inactive]
{group(s, s['window'])}

[Colors:Selection]
{group(sel, ACCENT, alt=ACCENT, fg='255,255,255')}

[Colors:Tooltip]
{group(s, s['tooltip'])}

[Colors:View]
{group(s, s['view'])}

[Colors:Window]
{group(s, s['window'])}

[General]
ColorScheme={sid}
Name={s['name']}
shadeSortColumn=true
AccentColor={ACCENT}

[KDE]
contrast={s['contrast']}

[WM]
activeBackground={s['window']}
activeBlend={s['window']}
activeForeground={s['fg']}
inactiveBackground={s['window']}
inactiveBlend={s['window']}
inactiveForeground={s['inactive']}
"""


KDEGLOBALS_HEAD = """[General]
ColorScheme=DropletSombre
AccentColor=236,0,45
font=Inter,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1
menuFont=Inter,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1
smallestReadableFont=Inter,8,-1,5,400,0,0,0,0,0,0,0,0,0,0,1
toolBarFont=Inter,10,-1,5,400,0,0,0,0,0,0,0,0,0,0,1

[Icons]
Theme=breeze-dark

[KDE]
widgetStyle=Breeze
SingleClick=false
AnimationDurationFactor=0.75

[WM]
activeFont=Inter,10,-1,5,700,0,0,0,0,0,0,0,0,0,0,1
"""

KWINRC = """[org.kde.kdecoration2]
library=org.kde.kwin.aurorae
theme=__aurorae__svg__DropletSombre
ButtonsOnLeft=XIA
ButtonsOnRight=
BorderSize=Normal
BorderSizeAuto=false

[Plugins]
# the Droplet Liquid Glass effect replaces blur and background contrast
blurEnabled=false
contrastEnabled=false
dropletglassEnabled=true
# window motion, macOS-like: windows zoom in/out (scale), minimise into their Dock icon (magic
# lamp = genie, the Dock publishes each icon's geometry), dialogs slide from their parent (sheet)
slidingpopupsEnabled=true
scaleEnabled=true
squashEnabled=false
magiclampEnabled=true
sheetEnabled=true
maximizeEnabled=true
fadingpopupsEnabled=true

[Effect-scale]
InScale=0.9
OutScale=0.94

[Effect-magiclamp]
AnimationDuration=360

[Compositing]
Backend=OpenGL
LatencyPolicy=Medium

[Windows]
Placement=Centered
BorderlessMaximizedWindows=false

[Desktops]
Number=1
Rows=1

[NightColor]
Active=false
"""


def main(out):
    out = Path(out)
    (out / "color-schemes").mkdir(parents=True, exist_ok=True)
    (out / "xdg").mkdir(parents=True, exist_ok=True)
    for sid, s in SCHEMES.items():
        (out / "color-schemes" / f"{sid}.colors").write_text(colors(sid, s))
    # kdeglobals = defaults + the dark scheme groups (apps read colours from kdeglobals)
    dark = colors("DropletSombre", SCHEMES["DropletSombre"])
    body = "\n".join(b for b in dark.split("\n\n") if not b.startswith("[General]"))
    (out / "xdg" / "kdeglobals").write_text(KDEGLOBALS_HEAD + "\n" + body)
    (out / "xdg" / "kwinrc").write_text(KWINRC)
    print("ok", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
