# Droplet OS 0.1 — test report (2026-11-17)

Environment: QEMU 8.2 on an Ubuntu 24.04 build host, **TCG (no KVM)**, 2 vCPU, 2 GB RAM,
VGA std (bochs-drm). ISO `droplet-os-0.1.0-vm-amd64.iso`, 427 MB.
Harness: `tests/vm/vmtest.py` (never touches the host; exit code 0 = pass).

## Functional (serial console) — PASS 13/13

| Check | Result |
|---|---|
| boots to login | ✅ 95 s under TCG (software CPU emulation; expect ~10-15 s with KVM) |
| `/etc/os-release` → `NAME="Droplet OS"`, `VERSION_ID="0.1.0"`, `ID=droplet` | ✅ |
| kernel 7.0.0-14-generic | ✅ |
| `systemctl is-system-running` → `running`, failed units: none | ✅ |
| default Plymouth theme = droplet | ✅ |
| theme inside the live initrd (82 intro frames) | ✅ |
| `droplet-clear-console.service` enabled | ✅ |
| AppArmor enabled | ✅ |
| UFW active (deny incoming) | ✅ |
| root account locked | ✅ |
| NetworkManager active | ✅ |
| 296 packages installed | ✅ |

## Visual

| Test | Result |
|---|---|
| 1080p (`video=1920x1080`): beam → eclipse → liquid wordmark → liquid progress | ✅ 88 consecutive splash screenshots |
| handoff: no systemd status lines, tty1 cleared, `Droplet OS 0.1.0 droplet tty1` | ✅ |
| BIOS boot of the unmodified ISO: hidden GRUB (black) → splash 1280x800 → login | ✅ |
| UEFI boot (OVMF) of the unmodified ISO: same | ✅ |

## Known issues

1. Under SeaBIOS (VM, BIOS mode, direct kernel boot) the firmware's text can flash for
   about one screenshot between the end of the splash and the cleared console. Not seen
   in UEFI. Fix candidate for 0.2: graphical session takes over before plymouth quits.
2. Not yet tested on physical hardware (next step: USB stick on a real UEFI laptop).
3. `PROFILE=hardware` (firmware + microcode) builds the same way but was not booted here.
4. No disk installer in 0.1 (live system only) — planned for 0.6.

## Reproduce

```bash
sudo python3 tests/vm/vmtest.py functional out/droplet-os-0.1.0-vm-amd64.iso /tmp/vmt
sudo python3 tests/vm/vmtest.py visual     out/droplet-os-0.1.0-vm-amd64.iso /tmp/vmt
sudo python3 tests/vm/vmtest.py bios       out/droplet-os-0.1.0-vm-amd64.iso /tmp/vmt
sudo python3 tests/vm/vmtest.py uefi       out/droplet-os-0.1.0-vm-amd64.iso /tmp/vmt
```
