#!/usr/bin/env python3
"""Droplet icon themes: Breeze, with folders in a fixed Droplet blue (Theme "dossier").

Breeze paints folders with the colour scheme's accent, so with the Droplet accent (#EC002D)
every folder turned red. macOS folders are blue, and so are Droplet's (design token
"dossier"). This takes Breeze's own folder icons (LGPL-3.0, KDE) and swaps their accent class
for a fixed colour; everything else is inherited from Breeze.

    icons_droplet.py BREEZE_ROOT OUT   (BREEZE_ROOT: /usr/share/icons, from the build system)
"""
import re
import shutil
import sys
from pathlib import Path

THEMES = {  # name: (inherits, folder colour)
    "Droplet": ("breeze", "#3c8bf5"),
    "Droplet-dark": ("breeze-dark", "#4f9dff"),
}


def recolor(svg, colour):
    # the accent-coloured shapes become a fixed fill; nothing else changes
    svg = re.sub(r'style="fill:currentColor"(\s*d="[^"]*"\s*)class="ColorScheme-(Accent|Highlight)"',
                 lambda m: f'style="fill:{colour}"{m.group(1)}', svg)
    svg = re.sub(r'class="ColorScheme-(Accent|Highlight)"(\s*)style="fill:currentColor"',
                 lambda m: f'{m.group(2)}style="fill:{colour}"', svg)
    return svg


def main(root, out):
    root, out = Path(root), Path(out)
    for name, (base, colour) in THEMES.items():
        src = root / base
        dst = out / name
        n = 0
        files = [f for ctx in ("places", "mimetypes") for pat in ("*/folder*.svg", "*/inode-directory*.svg")
                 for f in sorted((src / ctx).glob(pat))]
        for f in files:
            t = f.resolve().read_text() if f.exists() else ""
            if "ColorScheme-Accent" not in t and "ColorScheme-Highlight" not in t:
                continue
            target = dst / f.parent.parent.name / f.parent.name / f.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(recolor(t, colour))
            n += 1
        index = (src / "index.theme").read_text()
        index = re.sub(r"^Name=.*$", f"Name={name}", index, count=1, flags=re.M)
        index = re.sub(r"^Comment=.*$", "Comment=Breeze with Droplet folders", index, count=1, flags=re.M)
        index = re.sub(r"^Inherits=.*$", f"Inherits={base},hicolor", index, count=1, flags=re.M)
        if "Inherits=" not in index:
            index = index.replace("[Icon Theme]", f"[Icon Theme]\nInherits={base},hicolor", 1)
        (dst / "index.theme").write_text(index)
        # licence of the Breeze icons these folders are derived from (LGPL-3.0)
        for lic in (src / "COPYING", Path("/usr/share/doc/kf6-breeze-icon-theme/copyright")):
            if lic.exists():
                shutil.copy(lic, dst / ("COPYING.breeze" if lic.name == "copyright" else lic.name))
        print(dst, n, "folder icons")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
