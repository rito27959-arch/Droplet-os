#!/usr/bin/env python3
"""Droplet Kvantum themes (DropletClair / DropletSombre): every Qt and KDE app drawn with the
macOS 27 kit metrics, so apps look like the shell.

Measurements (Apple macOS 27 kit, variables "Sizes" Medium and "Colors"):
  controls 24 pt high, radius 6; check box 16 pt radius 5.5; radio 16 pt, dot 4.8;
  slider knob 20 x 16 capsule; toggles 54 x 24; field insets 8; menus radius 12 with rows
  highlighted at radius 8; fills: primary 10 %, secondary 8 %, tertiary 5 %;
  labels 85 / 50 (55) / 25 %; window #FFFFFF / #1E1E1E.
Droplet keeps its own accent (goutte #EC002D under white text) where macOS uses blue.

Every piece is drawn from scratch here (no artwork from other themes). Kvantum reads, for a
frame element E in state S, the nine pieces E-S-{topleft,top,...} and the interior E-S.

    kvantum.py OUTDIR   -> OUTDIR/DropletClair/{DropletClair.kvconfig,.svg}, same for Sombre
"""
import sys
from pathlib import Path

ACCENT = "#ec002d"
STATES = ("normal", "focused", "pressed", "toggled", "disabled")

PALETTES = {
    "DropletClair": dict(
        dark=False, window="#ffffff", base="#ffffff", alt="#f5f5f5", text="#262626", text2="#808080",
        disabled="#bfbfbf", button="#e6e6e6", button_hover="#dcdcdc", button_press="#cfcfcf",
        button_on="#cccccc", field="#ffffff", field_line="#d9d9d9", check="#ffffff", check_line="#bfbfbf",
        track="#e0e0e0", knob="#ffffff", knob_line="#c7c7c7", menu="#f2f2f2", menu_line="#d4d4d4",
        hover="#e3e3e3", sel_inactive="#dbdbdb", tip="#f7f7f7", tip_line="#d9d9d9", group="#f5f5f5",
        frame_line="#e0e0e0", scroll="#00000080", tab_track="#ebebeb", tab_on="#ffffff",
        tab_on_line="#d4d4d4", header_line="#e6e6e6"),
    "DropletSombre": dict(
        dark=True, window="#1e1e1e", base="#1e1e1e", alt="#252525", text="#d9d9d9", text2="#8c8c8c",
        disabled="#5c5c5c", button="#3d3d3d", button_hover="#474747", button_press="#525252",
        button_on="#575757", field="#2a2a2a", field_line="#3d3d3d", check="#2e2e2e", check_line="#5a5a5a",
        track="#3a3a3a", knob="#d9d9d9", knob_line="#a6a6a6", menu="#2b2b2b", menu_line="#454545",
        hover="#3d3d3d", sel_inactive="#454545", tip="#2c2c2c", tip_line="#454545", group="#252525",
        frame_line="#363636", scroll="#ffffff8c", tab_track="#2e2e2e", tab_on="#5a5a5a",
        tab_on_line="#666666", header_line="#333333"),
}


class Svg:
    def __init__(self):
        self.parts, self.x, self.y, self.row_h = [], 10, 10, 0

    def place(self, w, h):
        """next free spot on the sheet (elements never overlap)"""
        if self.x + w > 1900:
            self.x, self.y, self.row_h = 10, self.y + self.row_h + 10, 0
        x, y = self.x, self.y
        self.x += w + 10
        self.row_h = max(self.row_h, h)
        return x, y

    def add(self, id_, w, h, body):
        """an element whose bounding box is exactly w x h (a transparent rect fixes it)"""
        x, y = self.place(w, h)
        self.parts.append(f'<g id="{id_}" transform="translate({x},{y})">'
                          f'<rect width="{w}" height="{h}" fill="#000" fill-opacity="0"/>{body}</g>')

    def nine(self, name, F, r, fill, line=None, lw=1.0, interior=True):
        """the nine pieces of a rounded rectangle (radius r <= F), frame width F"""
        h = lw / 2
        corner = (f'<path d="M0,{F} L0,{r} A{r},{r} 0 0 1 {r},0 L{F},0 L{F},{F} Z" fill="{fill}"/>')
        if line:
            ri = max(r - h, 0.01)
            corner += (f'<path d="M{h},{F} L{h},{r} A{ri},{ri} 0 0 1 {r},{h} L{F},{h}" fill="none" '
                       f'stroke="{line}" stroke-width="{lw}"/>')
        edge = f'<rect width="{F}" height="{F}" fill="{fill}"/>'
        if line:
            edge += f'<rect width="{F}" height="{lw}" fill="{line}"/>'
        rot = {"topleft": 0, "topright": 90, "bottomright": 180, "bottomleft": 270}
        for k, a in rot.items():
            self.add(f"{name}-{k}", F, F, f'<g transform="rotate({a} {F / 2} {F / 2})">{corner}</g>')
        for k, a in {"top": 0, "right": 90, "bottom": 180, "left": 270}.items():
            self.add(f"{name}-{k}", F, F, f'<g transform="rotate({a} {F / 2} {F / 2})">{edge}</g>')
        if interior:
            self.add(name, F, F, f'<rect width="{F}" height="{F}" fill="{fill}"/>')

    def text(self):
        # QtSvg reads #RRGGBB only: turn #RRGGBBAA into a colour + opacity
        import re
        body = "\n".join(self.parts)
        body = re.sub(r'(fill|stroke)="#([0-9a-fA-F]{6})([0-9a-fA-F]{2})"',
                      lambda m: f'{m.group(1)}="#{m.group(2)}" {m.group(1)}-opacity="{int(m.group(3), 16) / 255:.3f}"', body)
        self.parts = [body]
        return ('<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="%d">\n' % (self.y + self.row_h + 20)
                + "\n".join(self.parts) + "\n</svg>\n")


def chevron(direction, color, size=10, w=1.6):
    pts = {"down": "2.5,3.8 5,6.3 7.5,3.8", "up": "2.5,6.2 5,3.7 7.5,6.2",
           "right": "3.8,2.5 6.3,5 3.8,7.5", "left": "6.2,2.5 3.7,5 6.2,7.5"}[direction]
    k = size / 10
    return (f'<polyline points="{pts}" transform="scale({k})" fill="none" stroke="{color}" '
            f'stroke-width="{w / k}" stroke-linecap="round" stroke-linejoin="round"/>')


def build(name, p):
    s = Svg()
    a = ACCENT
    # ---- push buttons (kit Medium: 24 pt, radius 6); hover/press darken, default: accent ring
    for st, c in zip(STATES, (p["button"], p["button_hover"], p["button_press"], p["button_on"], p["button"])):
        s.nine(f"button-{st}", 6, 6, c)
    # tool buttons: flat until hovered (macOS toolbar items)
    for st, c in zip(STATES, ("#00000000", p["hover"], p["button_press"], p["button_on"], "#00000000")):
        s.nine(f"tbutton-{st}", 6, 6, c)
    # ---- text fields (kit Fields: insets 8, radius 6); focus: accent 2 pt ring
    for st in STATES:
        line = a if st == "focused" else p["field_line"]
        s.nine(f"lineedit-{st}", 6, 6, p["field"], line=line, lw=2 if st == "focused" else 1)
    # ---- check boxes and radios (16 pt)
    ck = '<polyline points="4.2,8.4 6.9,11 11.8,5.2" fill="none" stroke="#fff" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"/>'
    dash = '<rect x="4.5" y="7.1" width="7" height="1.8" rx="0.9" fill="#fff"/>'
    for st in STATES:
        line = p["text2"] if st in ("focused", "pressed") else p["check_line"]
        box = f'<rect x="0.5" y="0.5" width="15" height="15" rx="5" fill="{p["check"]}" stroke="{line}"/>'
        on = f'<rect width="16" height="16" rx="5.5" fill="{a if st != "disabled" else p["disabled"]}"/>'
        for prefix in ("", "item-", "menu-"):
            s.add(f"{prefix}checkbox-{st}", 16, 16, box)
            s.add(f"{prefix}checkbox-checked-{st}", 16, 16, on + ck)
            s.add(f"{prefix}checkbox-tristate-{st}", 16, 16, on + dash)
            s.add(f"{prefix}radio-{st}" if prefix != "item-" else f"item-radio-{st}", 16, 16,
                  f'<circle cx="8" cy="8" r="7.5" fill="{p["check"]}" stroke="{line}"/>')
            s.add(f"{prefix}radio-checked-{st}" if prefix != "item-" else f"item-radio-checked-{st}", 16, 16,
                  f'<circle cx="8" cy="8" r="8" fill="{a if st != "disabled" else p["disabled"]}"/>'
                  '<circle cx="8" cy="8" r="2.4" fill="#fff"/>')
    # ---- slider: 4 pt capsule track, filled part in accent; knob 20 x 16 capsule (kit)
    for st in STATES:
        s.nine(f"slider-{st}", 2, 2, p["track"])
    s.nine("slider-toggled", 2, 2, a)
    knob = (f'<rect x="0.5" y="1.5" width="19" height="14" rx="7" fill="#000" fill-opacity="0.10"/>'
            f'<rect x="0.5" y="0.5" width="19" height="14" rx="7" fill="{p["knob"]}" stroke="{p["knob_line"]}" stroke-width="0.6"/>')
    for st in STATES:
        s.add(f"slidercursor-{st}", 20, 16, knob)
        s.add(f"slidercursor-tickless-{st}", 20, 16, knob)
    # ---- progress: 6 pt capsule, accent fill
    for st in STATES:
        s.nine(f"progress-{st}", 3, 3, p["track"])
        s.nine(f"progress-pattern-{st}", 3, 3, a)
    # ---- scroll bars: overlay capsule (macOS), no groove
    for st, op in zip(STATES, (1, 1, 1, 1, 0.5)):
        s.nine(f"scrollbarslider-{st}", 4, 4, p["scroll"])
    # ---- menus (kit: radius 12, rows highlighted at radius 8)
    s.nine("menu-normal", 12, 12, p["menu"] + "f2", line=p["menu_line"], lw=1)
    for st in STATES:
        s.nine(f"menuitem-{st}", 6, 6, p["hover"] if st in ("focused", "pressed", "toggled") else "#00000000")
    for st in STATES:
        s.nine(f"menubaritem-{st}", 6, 6, p["hover"] if st in ("focused", "pressed", "toggled") else "#00000000")
    # ---- item views: selection in accent (active) or grey (inactive), radius 6
    for st, c in zip(STATES, ("#00000000", p["hover"], a, a, "#00000000")):
        s.nine(f"itemview-{st}", 6, 6, c)
    for st in STATES:
        s.nine(f"itemview-{st}-inactive", 6, 6, p["sel_inactive"] if st in ("pressed", "toggled") else "#00000000")
    # ---- tabs as a segmented control (kit Segmented Control): grey track, raised selected segment
    s.nine("tabbarframe-normal", 7, 7, p["tab_track"])
    for st, c in zip(STATES, (p["tab_track"], p["hover"], p["button_press"], p["tab_on"], p["tab_track"])):
        if st == "toggled":
            s.nine(f"tab-{st}", 6, 6, c, line=p["tab_on_line"], lw=0.6)
        else:
            s.nine(f"tab-{st}", 6, 6, c)
    s.nine("tabframe-normal", 10, 10, p["window"], line=p["frame_line"], lw=1)
    # ---- frames, group boxes, tooltips, headers, focus
    s.nine("common-normal", 4, 4, p["base"], line=p["frame_line"], lw=1, interior=False)
    s.nine("group-normal", 10, 10, p["group"])
    s.nine("tooltip-normal", 6, 6, p["tip"], line=p["tip_line"], lw=1)
    for st in STATES:
        s.nine(f"header-{st}", 1, 0.01, p["base"])
    s.nine("focus", 6, 6, "#00000000", line=a + "80", lw=2.5, interior=False)
    # ---- arrows / chevrons
    for d in ("down", "up", "left", "right"):
        for st in STATES:
            col = p["disabled"] if st == "disabled" else p["text"]
            for prefix in ("arrow", "flat-arrow", "iarrow"):
                s.add(f"{prefix}-{d}-{st}", 10, 10, chevron(d, col))
    for st in STATES:
        col = p["disabled"] if st == "disabled" else p["text"]
        for prefix in ("arrow", "iarrow"):
            s.add(f"{prefix}-plus-{st}", 10, 10, f'<path d="M5,2 V8 M2,5 H8" stroke="{col}" stroke-width="1.6" stroke-linecap="round"/>')
            s.add(f"{prefix}-minus-{st}", 10, 10, f'<path d="M2,5 H8" stroke="{col}" stroke-width="1.6" stroke-linecap="round"/>')
    for st in ("normal", "focused", "pressed"):
        s.add(f"tab-close-{st}" if st == "normal" else ("tab-closeFocused" if st == "focused" else "tab-closePressed"),
              12, 12, f'<circle cx="6" cy="6" r="6" fill="{p["hover"] if st != "normal" else "#00000000"}"/>'
              f'<path d="M3.8,3.8 L8.2,8.2 M8.2,3.8 L3.8,8.2" stroke="{p["text2"]}" stroke-width="1.3" stroke-linecap="round"/>')
    # ---- separators and grips: hairlines or nothing (macOS draws no handles)
    line = p["frame_line"]
    for idn in ("toolbar-separator", "menu-separator", "menuitem-separator", "separator"):
        s.add(idn, 10, 10, f'<rect x="4.5" y="0" width="1" height="10" fill="{line}"/>')
    for idn in ("toolbar-handle", "button-default-indicator", "flat-button-default-indicator",
                "resize-grip", "splitter-grip", "grip-normal", "grip-focused", "grip-pressed"):
        s.add(idn, 10, 10, "")
    return s.text()


def kvconfig(name, p):
    t = p["text"]
    return f"""[%General]
author=Droplet OS
comment=Droplet {"sombre" if p["dark"] else "clair"} — macOS 27 kit metrics, Droplet accent
x11drag=menubar_and_primary_toolbar
alt_mnemonic=true
left_tabs=false
attach_active_tab=false
embedded_tabs=false
center_doc_tabs=true
center_normal_tabs=true
group_toolbar_buttons=false
spread_progressbar=true
composite=true
menu_shadow_depth=0
tooltip_shadow_depth=0
spread_menuitems=true
menu_separator_height=11
scroll_width=11
scroll_arrows=false
scroll_min_extent=36
transient_scrollbar=true
transient_groove=true
slider_width=4
slider_handle_width=20
slider_handle_length=16
tickless_slider_handle_size=20
check_size=16
textless_progressbar=false
progressbar_thickness=6
menubar_mouse_tracking=true
toolbutton_style=0
click_behavior=0
translucent_windows=false
blurring=false
popup_blurring=true
vertical_spin_indicators=false
inline_spin_indicators=true
fill_rubberband=true
merge_menubar_with_toolbar=true
small_icon_size=16
large_icon_size=32
button_icon_size=16
toolbar_icon_size=18
combo_as_lineedit=true
combo_menu=true
combo_focus_rect=false
remove_extra_frames=true
animate_states=true
no_inactiveness=true
dialog_button_layout=3
layout_spacing=8
layout_margin=16
submenu_overlap=0
menu_blur_radius=0
contrast=1.00
intensity=1.00
saturation=1.00

[GeneralColors]
window.color={p["window"]}
base.color={p["base"]}
alt.base.color={p["alt"]}
button.color={p["button"]}
light.color={p["base"]}
mid.light.color={p["alt"]}
dark.color={p["field_line"]}
mid.color={p["frame_line"]}
highlight.color={ACCENT}
inactive.highlight.color={p["sel_inactive"]}
text.color={t}
window.text.color={t}
button.text.color={t}
disabled.text.color={p["disabled"]}
tooltip.text.color={t}
highlight.text.color=#ffffff
link.color={"#ff375f" if p["dark"] else "#d6002b"}
link.visited.color={"#bf5af2" if p["dark"] else "#8e3fb0"}
progress.indicator.text.color={t}

[Hacks]
transparent_ktitle_label=true
transparent_dolphin_view=false
transparent_pcmanfm_sidepane=true
blur_translucent=true
transparent_menutitle=true
respect_darkness=true
force_size_grip=false
iconless_pushbutton=true
iconless_menu=false
transparent_arrow_button=true
single_top_toolbar=true
no_selection_tint=true
centered_forms=false
kcapacitybar_as_progressbar=true
middle_click_scroll=false
normal_default_pushbutton=true
tint_on_mouseover=0
disabled_icon_opacity=40
lxqtmainmenu_iconsize=16
tint_on_mouseover=0

[PanelButtonCommand]
frame=true
frame.element=button
frame.top=6
frame.bottom=6
frame.left=6
frame.right=6
interior=true
interior.element=button
indicator.size=10
indicator.element=arrow
text.normal.color={t}
text.focus.color={t}
text.press.color={t}
text.toggle.color={t}
text.disabled.color={p["disabled"]}
text.shadow=0
text.margin=1
text.iconspacing=6
text.margin.top=0
text.margin.bottom=0
text.margin.left=10
text.margin.right=10
min_width=+0.5font
min_height=+0.2font
frame.expansion=0

[PanelButtonTool]
inherits=PanelButtonCommand

[ToolbarButton]
inherits=PanelButtonCommand
frame.element=tbutton
interior.element=tbutton
text.margin.left=4
text.margin.right=4

[Dock]
inherits=PanelButtonCommand
frame=false
interior=false

[DockTitle]
inherits=PanelButtonCommand
frame=false
interior=false
text.bold=true

[IndicatorSpinBox]
inherits=PanelButtonCommand
frame=false
interior=false
indicator.element=arrow

[RadioButton]
inherits=PanelButtonCommand
frame=false
interior.element=radio
text.margin.left=4

[CheckBox]
inherits=PanelButtonCommand
frame=false
interior.element=checkbox
text.margin.left=4

[Focus]
inherits=PanelButtonCommand
frame=false
frame.element=focus
frame.top=6
frame.bottom=6
frame.left=6
frame.right=6
interior=false

[GenericFrame]
inherits=PanelButtonCommand
frame=true
interior=false
frame.element=common
interior.element=common
frame.top=4
frame.bottom=4
frame.left=4
frame.right=4
frame.expansion=0

[LineEdit]
inherits=PanelButtonCommand
frame.element=lineedit
interior.element=lineedit
frame.top=6
frame.bottom=6
frame.left=6
frame.right=6
text.margin.left=2
text.margin.right=2

[DropDownButton]
inherits=PanelButtonCommand
indicator.element=arrow-down

[IndicatorArrow]
indicator.element=arrow
indicator.size=10

[ToolboxTab]
inherits=PanelButtonCommand

[Tab]
inherits=PanelButtonCommand
frame.element=tab
interior.element=tab
frame.top=6
frame.bottom=6
frame.left=6
frame.right=6
text.margin.left=10
text.margin.right=10
text.margin.top=1
text.margin.bottom=1
indicator.element=tab
indicator.size=12
focusFrame=false
min_width=4font

[TabBarFrame]
inherits=PanelButtonCommand
frame=true
interior=true
frame.element=tabbarframe
interior.element=tabbarframe
frame.top=7
frame.bottom=7
frame.left=7
frame.right=7

[TabFrame]
inherits=PanelButtonCommand
frame.element=tabframe
interior.element=tabframe
frame.top=10
frame.bottom=10
frame.left=10
frame.right=10

[TreeExpander]
inherits=PanelButtonCommand
frame=false
interior=false
indicator.size=10
indicator.element=arrow

[HeaderSection]
inherits=PanelButtonCommand
frame.element=header
interior.element=header
frame.top=1
frame.bottom=1
frame.left=1
frame.right=1
text.bold=false
text.normal.color={p["text2"]}
text.margin.left=6
text.margin.right=6

[SizeGrip]
indicator.element=resize-grip

[Toolbar]
inherits=PanelButtonCommand
frame=false
interior=false
indicator.element=toolbar
indicator.size=5
text.margin=0

[Slider]
inherits=PanelButtonCommand
frame.element=slider
interior.element=slider
frame.top=2
frame.bottom=2
frame.left=2
frame.right=2

[SliderCursor]
inherits=PanelButtonCommand
frame=false
interior.element=slidercursor

[Progressbar]
inherits=PanelButtonCommand
frame.element=progress
interior.element=progress
frame.top=3
frame.bottom=3
frame.left=3
frame.right=3
text.margin=0
text.bold=false
text.normal.color={p["text2"]}

[ProgressbarContents]
inherits=PanelButtonCommand
frame=true
frame.element=progress-pattern
interior.element=progress-pattern
frame.top=3
frame.bottom=3
frame.left=3
frame.right=3

[ItemView]
inherits=PanelButtonCommand
frame.element=itemview
interior.element=itemview
frame.top=6
frame.bottom=6
frame.left=6
frame.right=6
text.margin.top=2
text.margin.bottom=2
text.margin.left=4
text.margin.right=4
text.press.color=#ffffff
text.toggle.color=#ffffff
min_width=0
min_height=0

[Splitter]
indicator.size=32

[Scrollbar]
inherits=PanelButtonCommand
indicator.element=arrow
indicator.size=10

[ScrollbarSlider]
inherits=PanelButtonCommand
frame.element=scrollbarslider
interior=false
frame.left=4
frame.right=4
frame.top=4
frame.bottom=4
indicator.element=grip
indicator.size=0

[ScrollbarGroove]
inherits=PanelButtonCommand
interior=false
frame=false

[MenuItem]
inherits=PanelButtonCommand
frame=true
frame.element=menuitem
interior.element=menuitem
indicator.element=menuitem
frame.top=6
frame.bottom=6
frame.left=6
frame.right=6
text.margin.top=0
text.margin.bottom=0
text.margin.left=6
text.margin.right=6
text.focus.color={t}
text.press.color={t}
min_width=0
min_height=+0.4font

[MenuBar]
inherits=PanelButtonCommand
frame=false
interior=false

[MenuBarItem]
inherits=PanelButtonCommand
frame.element=menubaritem
interior.element=menubaritem
frame.top=6
frame.bottom=6
frame.left=6
frame.right=6
text.margin.left=4
text.margin.right=4

[TitleBar]
inherits=PanelButtonCommand
frame=false
interior=false
text.bold=true

[ComboBox]
inherits=PanelButtonCommand
indicator.element=arrow-down

[Menu]
inherits=PanelButtonCommand
frame.element=menu
interior.element=menu
frame.top=12
frame.bottom=12
frame.left=12
frame.right=12
text.normal.color={t}

[GroupBox]
inherits=GenericFrame
frame=true
frame.element=group
interior=true
interior.element=group
frame.top=10
frame.bottom=10
frame.left=10
frame.right=10
text.bold=true
text.margin=0

[ToolTip]
inherits=GenericFrame
frame.element=tooltip
interior.element=tooltip
interior=true
frame.top=6
frame.bottom=6
frame.left=6
frame.right=6
text.normal.color={t}

[StatusBar]
inherits=GenericFrame
frame=false
interior=false

[Window]
interior=false
frame=false
"""


def main(out):
    for name, p in PALETTES.items():
        d = Path(out) / name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.svg").write_text(build(name, p))
        (d / f"{name}.kvconfig").write_text(kvconfig(name, p))
        print(d)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "kvantum")
