#!/usr/bin/env bash
# =============================================================================
# Droplet OS — bootable live ISO builder (x86-64, BIOS + UEFI)
#
#   sudo ./base/build.sh                      # PROFILE=vm (default)
#   sudo PROFILE=hardware ./base/build.sh     # real machines (firmware + microcode)
#   sudo LAYERS= ./base/build.sh              # console base only (0.1); default LAYERS=desktop (0.2)
#
# Pipeline: mmdebstrap (Ubuntu 26.04 rootfs) -> customize hook (branding, plymouth,
# live config, security baseline) -> squashfs -> casper layout -> grub-mkrescue ISO.
# Never touches the host system outside $WORK and $OUT.
# =============================================================================
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=base/config/droplet.conf
source "$ROOT/base/config/droplet.conf"

WORK="${WORK:-$ROOT/work}"
OUT="${OUT:-$ROOT/out}"
LAYERS="${LAYERS:-}"
ROOTFS="$WORK/rootfs"
STAGE="$WORK/iso"
ISO="$OUT/droplet-os-${DROPLET_VERSION}-${PROFILE}-${ARCH}.iso"

log()  { printf '\033[1;34m[droplet]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[droplet] ERROR:\033[0m %s\n' "$*" >&2; exit 1; }
trap 'die "build failed at line $LINENO"' ERR

# --- preflight ---------------------------------------------------------------
[[ $EUID -eq 0 ]] || die "run as root (mmdebstrap root mode, chroot, squashfs ownership)"
[[ "$ARCH" == amd64 ]] || die "0.1 targets x86-64 only"
for tool in mmdebstrap mksquashfs grub-mkrescue xorriso mformat; do
  command -v "$tool" >/dev/null || die "missing tool: $tool (see documentation/BUILD.md)"
done
[[ -d /usr/lib/grub/i386-pc ]]    || die "missing grub-pc-bin (BIOS boot)"
[[ -d /usr/lib/grub/x86_64-efi ]] || die "missing grub-efi-amd64-bin (UEFI boot)"
[[ -f "$ROOT/base/packages/$PROFILE.list" ]] || die "unknown PROFILE=$PROFILE"

read_list() { grep -hv '^\s*#' "$@" | sed '/^\s*$/d' | tr '\n' ',' | sed 's/,$//'; }
lists=("$ROOT/base/packages/common.list" "$ROOT/base/packages/$PROFILE.list")
for layer in $LAYERS; do
  [[ -f "$ROOT/base/packages/$layer.list" ]] || die "unknown layer: $layer"
  lists+=("$ROOT/base/packages/$layer.list")
done
PACKAGES="$(read_list "${lists[@]}")"

# Refuse to rm -rf anything that is not clearly ours
case "$WORK" in "$ROOT"/*|/tmp/*|/var/tmp/*) ;; *) die "WORK must live under $ROOT or /tmp";; esac
rm -rf "$WORK"
mkdir -p "$STAGE"/{casper,boot/grub,.disk} "$OUT"

# --- assets ------------------------------------------------------------------
if [[ ! -f "$ROOT/boot/plymouth/droplet/droplet.script" ]]; then
  log "rendering DROPLET BOOT theme (eclipse + liquid wordmark)"
  python3 "$ROOT/boot/plymouth/render/export_plymouth.py" "$ROOT/boot/plymouth/droplet"
fi

# --- 1. root filesystem ------------------------------------------------------
log "mmdebstrap $SUITE ($PROFILE${LAYERS:+ + $LAYERS})"
export DROPLET_VERSION DROPLET_CODENAME LIVE_USER LIVE_HOSTNAME DEFAULT_LOCALE \
       DEFAULT_TIMEZONE DEFAULT_KEYMAP PROFILE LAYERS
mmdebstrap \
  --mode=root --variant=apt --arch="$ARCH" \
  --components="${COMPONENTS// /,}" \
  --include="$PACKAGES" \
  --aptopt='APT::Install-Recommends "false"' \
  --dpkgopt='path-exclude=/usr/share/doc/*' \
  --dpkgopt='path-include=/usr/share/doc/*/copyright' \
  --customize-hook="\"$ROOT/base/hooks/customize-host.sh\" \"\$1\" \"$ROOT\"" \
  "$SUITE" "$ROOTFS" "$MIRROR"

# --- 2. casper layout --------------------------------------------------------
log "casper layout"
kernel="$(ls -1 "$ROOTFS"/boot/vmlinuz-* | sort -V | tail -1)"
initrd="$(ls -1 "$ROOTFS"/boot/initrd.img-* | sort -V | tail -1)"
cp "$kernel" "$STAGE/casper/vmlinuz"
cp "$initrd" "$STAGE/casper/initrd"
chroot "$ROOTFS" dpkg-query -W --showformat='${Package} ${Version}\n' > "$STAGE/casper/filesystem.manifest"
du -sx --block-size=1 "$ROOTFS" | cut -f1 > "$STAGE/casper/filesystem.size"
printf 'Droplet OS %s "%s" - %s (%s)\n' "$DROPLET_VERSION" "$DROPLET_CODENAME" "$ARCH" "$(date -u +%Y%m%d)" > "$STAGE/.disk/info"

log "squashfs ($SQUASHFS_COMP)"
mksquashfs "$ROOTFS" "$STAGE/casper/filesystem.squashfs" \
  -comp "$SQUASHFS_COMP" -noappend -no-progress -wildcards \
  -e 'proc/*' 'sys/*' 'dev/*' 'run/*' 'tmp/*' 'var/cache/apt/archives/*.deb'

# --- 3. bootloader -----------------------------------------------------------
sed -e "s/@VERSION@/$DROPLET_VERSION/g" "$ROOT/boot/grub/grub.cfg" > "$STAGE/boot/grub/grub.cfg"
(cd "$STAGE" && find . -type f ! -name md5sum.txt -print0 | xargs -0 md5sum > md5sum.txt)

log "ISO (BIOS + UEFI hybrid)"
grub-mkrescue -o "$ISO" "$STAGE" -- -volid "$ISO_VOLID" 2>&1 | grep -v '^xorriso : UPDATE' || true
[[ -s "$ISO" ]] || die "ISO not produced"
(cd "$OUT" && sha256sum "$(basename "$ISO")" > "$(basename "$ISO").sha256")
cp "$STAGE/casper/filesystem.manifest" "$OUT/$(basename "$ISO" .iso).manifest"

log "done: $ISO ($(du -h "$ISO" | cut -f1))"
