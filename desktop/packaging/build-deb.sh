#!/usr/bin/env bash
# =============================================================================
# Droplet OS 0.2 — builds droplet-desktop_<version>_amd64.deb
#   shell (C++23/QML), Wayland session, window decoration, colour schemes,
#   system defaults (/etc/xdg), login screen (SDDM), icons, symbols, wallpapers.
#
#   ./desktop/packaging/build-deb.sh [OUTDIR]
# Run on Ubuntu 26.04 with the build dependencies installed (see documentation/BUILD-0.2.md),
# e.g. inside the build chroot. Never installs anything on the machine it runs on.
# =============================================================================
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP="$(dirname "$HERE")"
REPO="$(dirname "$DESKTOP")"
OUT="${1:-$REPO/out/debs}"
VERSION="${DROPLET_DESKTOP_VERSION:-0.2.0}"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
PKG="$WORK/pkg"

echo "[deb] shell"
cmake -S "$DESKTOP/shell" -B "$WORK/build" -G Ninja -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release >/dev/null
ninja -C "$WORK/build" >/dev/null
DESTDIR="$PKG" ninja -C "$WORK/build" install >/dev/null
strip --strip-unneeded "$PKG/usr/bin/droplet-shell"

echo "[deb] Liquid Glass (KWin effect)"
cmake -S "$DESKTOP/effects/liquidglass" -B "$WORK/glass" -G Ninja -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release >/dev/null
ninja -C "$WORK/glass" >/dev/null
DESTDIR="$PKG" ninja -C "$WORK/glass" install >/dev/null
strip --strip-unneeded "$PKG"/usr/lib/x86_64-linux-gnu/qt6/plugins/kwin/effects/plugins/dropletglass.so

echo "[deb] living wallpaper"
WALL="${DROPLET_WALLPAPERS:-$REPO/out/wallpapers}"
[[ -f "$WALL/jour/fond.jpg" && -f "$WALL/transition/nuit-jour.mp4" ]] || {
  echo "wallpapers missing in $WALL: run aura/render/export_wallpapers.py $WALL first" >&2; exit 1; }
install -d "$PKG/usr/share/droplet/wallpapers"
(cd "$WALL" && find jour nuit transition -type f \( -name '*.jpg' -o -name '*.png' -o -name '*.json' -o -name '*.mp4' \) \
   -exec install -Dm644 {} "$PKG/usr/share/droplet/wallpapers/{}" \;)

echo "[deb] session"
install -Dm755 "$DESKTOP/session/startdroplet" "$PKG/usr/bin/startdroplet"
install -Dm755 "$DESKTOP/session/droplet-session-init" "$PKG/usr/lib/droplet/droplet-session-init"
install -Dm644 "$DESKTOP/session/droplet.desktop" "$PKG/usr/share/wayland-sessions/droplet.desktop"

echo "[deb] theme"
install -d "$PKG/usr/share/aurorae/themes" "$PKG/usr/share/color-schemes" "$PKG/etc/xdg" "$PKG/usr/share/sddm/themes"
cp -r "$DESKTOP/theme/aurorae/." "$PKG/usr/share/aurorae/themes/"
cp "$DESKTOP/theme/color-schemes/"*.colors "$PKG/usr/share/color-schemes/"
cp "$DESKTOP/theme/xdg/kdeglobals" "$DESKTOP/theme/xdg/kwinrc" "$DESKTOP/theme/xdg/kscreenlockerrc" \
   "$DESKTOP/theme/xdg/breezerc" "$PKG/etc/xdg/"
cp -r "$DESKTOP/theme/sddm/droplet" "$PKG/usr/share/sddm/themes/"
echo "[deb] icons (Breeze with Droplet folders)"
python3 "$DESKTOP/theme/render/icons_droplet.py" /usr/share/icons "$PKG/usr/share/icons" >/dev/null
install -d "$PKG/usr/share/Kvantum"
cp -r "$DESKTOP/theme/kvantum/." "$PKG/usr/share/Kvantum/"
install -Dm644 "$DESKTOP/theme/sddm/10-droplet.conf" "$PKG/etc/sddm.conf.d/10-droplet.conf"

echo "[deb] licences"
install -Dm644 "$REPO/LICENSE" "$PKG/usr/share/doc/droplet-desktop/copyright"
install -Dm644 "$REPO/aura/symbols/LICENSE.phosphor" "$PKG/usr/share/doc/droplet-desktop/LICENSE.phosphor-icons"

SIZE=$(du -sk "$PKG" | cut -f1)
install -d "$PKG/DEBIAN"
cat > "$PKG/DEBIAN/control" <<CTL
Package: droplet-desktop
Version: $VERSION
Architecture: amd64
Maintainer: Droplet OS <rito27959-arch@users.noreply.github.com>
Installed-Size: $SIZE
Section: x11
Priority: optional
Depends: kwin-wayland, kwin-style-aurorae, qt-style-kvantum | qt6-style-kvantum, qml6-module-qtmultimedia, libqt6multimedia6, plasma-workspace, plasma-integration, sddm,
 qml6-module-org-kde-layershell, qml6-module-qtquick, qml6-module-qtquick-window,
 qml6-module-qtquick-effects, qml6-module-qtqml-workerscript, qml6-module-org-kde-kirigami,
 qt6-wayland, kf6-breeze-icon-theme, fonts-inter, dbus-bin, libkf6service-bin
Recommends: network-manager, pipewire, wireplumber, brightnessctl, rfkill, dolphin, konsole, kate,
 systemsettings, kde-spectacle, kinfocenter, xwayland
Description: Droplet OS desktop (Aura)
 Wayland session on KWin with the Droplet shell: menu bar, Dock, search,
 Control Centre, notifications and desktop widgets, the Droplet window
 decoration, colour schemes and login screen.
CTL
mkdir -p "$OUT"
dpkg-deb --root-owner-group --build "$PKG" "$OUT/droplet-desktop_${VERSION}_amd64.deb" >/dev/null
echo "[deb] $OUT/droplet-desktop_${VERSION}_amd64.deb"
