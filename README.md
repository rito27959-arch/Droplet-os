# Droplet OS

> One Intelligence. Every Device. One Ecosystem.

**Version 0.1 "Foundation"** — a bootable, installable-ready x86-64 live system built on
Ubuntu 26.04 LTS (Resolute Raccoon), with its own identity and boot experience.

| Area | 0.1 status |
|---|---|
| Base: Ubuntu 26.04 LTS, Linux 7.0, systemd, APT | ✅ built and booted in a VM |
| Live ISO, BIOS + UEFI (GRUB hybrid, casper) | ✅ built, booted in QEMU (BIOS + UEFI) |
| DROPLET BOOT splash (Plymouth, eclipse + liquid wordmark) | ✅ runs in a VM at 1080p |
| Identity (`/etc/os-release`, hostname, issue) | ✅ |
| Security baseline: AppArmor, UFW (deny in), root locked, polkit | ✅ verified in VM |
| Network: NetworkManager | ✅ |
| Wayland / KWin / Qt 6 session | ⏳ optional layer `LAYERS=session-kwin`, not validated yet (0.2) |
| Disk installer | ⏳ 0.6 (live only in 0.1) |

## Quick start

```bash
# on Ubuntu 24.04+ (root needed: mmdebstrap root mode + chroot)
sudo apt install mmdebstrap xorriso squashfs-tools grub-pc-bin grub-efi-amd64-bin \
                 grub-common mtools dosfstools qemu-system-x86 ovmf \
                 python3-numpy python3-scipy python3-pil fonts-inter ffmpeg
sudo ./base/build.sh                       # -> out/droplet-os-0.1.0-vm-amd64.iso
sudo PROFILE=hardware ./base/build.sh      # real machines (firmware + microcode)

# tests (never touch the host)
sudo python3 tests/vm/vmtest.py functional out/droplet-os-0.1.0-vm-amd64.iso /tmp/vmt
sudo python3 tests/vm/vmtest.py visual     out/droplet-os-0.1.0-vm-amd64.iso /tmp/vmt
sudo python3 tests/vm/vmtest.py bios       out/droplet-os-0.1.0-vm-amd64.iso /tmp/vmt
sudo python3 tests/vm/vmtest.py uefi       out/droplet-os-0.1.0-vm-amd64.iso /tmp/vmt

# try it
qemu-system-x86_64 -m 2048 -enable-kvm -cdrom out/droplet-os-0.1.0-vm-amd64.iso
```

Live session: user `droplet`, no password, `sudo` allowed. Press **Esc** during the 2 s
GRUB countdown for the menu (safe graphics, diagnostics, recovery).

## Repository layout

```
base/            ISO builder: config, package lists, chroot hooks
boot/grub/       boot menu (hidden, seamless)
boot/plymouth/   DROPLET BOOT: render/ (Python renderer) -> droplet/ (generated theme)
system/overlay/  files copied as-is into the root filesystem
tests/vm/        QEMU test harness (functional, visual, BIOS, UEFI)
documentation/   build, boot design, tests, licences
desktop/ aura/ engine/ store/ ai/ installer/ ...   later versions (0.2+)
```

See `documentation/` for details. Licence: GPL-3.0-or-later (see `LICENSE`).
