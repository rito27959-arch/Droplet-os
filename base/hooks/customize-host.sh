#!/usr/bin/env bash
# Runs on the HOST as mmdebstrap's customize hook. $1 = rootfs, $2 = repo root.
# Copies Droplet files into the rootfs, then runs customize-chroot.sh inside it.
set -Eeuo pipefail
rootfs="$1"; repo="$2"

cp -a "$repo/system/overlay/." "$rootfs/"
install -d "$rootfs/usr/share/plymouth/themes/droplet"
cp -a "$repo/boot/plymouth/droplet/." "$rootfs/usr/share/plymouth/themes/droplet/"
install -m 0755 "$repo/base/hooks/customize-chroot.sh" "$rootfs/tmp/customize-chroot.sh"

# Layer "desktop": the droplet-desktop package (built by desktop/packaging/build-deb.sh)
if [[ " ${LAYERS:-} " == *" desktop "* ]]; then
  deb="$(ls -1 "$repo"/out/debs/droplet-desktop_*_amd64.deb 2>/dev/null | sort -V | tail -1)"
  [[ -n "$deb" ]] || { echo "droplet-desktop .deb missing: run desktop/packaging/build-deb.sh first" >&2; exit 1; }
  install -d "$rootfs/tmp/debs"
  cp "$deb" "$rootfs/tmp/debs/"
fi

chroot "$rootfs" env \
  DROPLET_VERSION="$DROPLET_VERSION" DROPLET_CODENAME="$DROPLET_CODENAME" \
  LIVE_USER="$LIVE_USER" LIVE_HOSTNAME="$LIVE_HOSTNAME" \
  DEFAULT_LOCALE="$DEFAULT_LOCALE" DEFAULT_TIMEZONE="$DEFAULT_TIMEZONE" \
  DEFAULT_KEYMAP="$DEFAULT_KEYMAP" PROFILE="$PROFILE" LAYERS="${LAYERS:-}" \
  /bin/bash /tmp/customize-chroot.sh

rm -rf "$rootfs/tmp/customize-chroot.sh" "$rootfs/tmp/debs"
