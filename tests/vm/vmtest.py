#!/usr/bin/env python3
"""Droplet OS 0.1 — automated VM tests (QEMU). Never touches the host system.

  vmtest.py functional <iso> <outdir>   serial console: login + system checks
  vmtest.py visual     <iso> <outdir>   1080p splash screenshots
  vmtest.py bios       <iso> <outdir>   unmodified ISO boot via GRUB (BIOS)
  vmtest.py uefi       <iso> <outdir>   unmodified ISO boot via GRUB (UEFI/OVMF)
  vmtest.py desktop    <iso> <outdir>   0.2: Droplet session (KWin + shell), checks + real screenshots

Uses KVM when /dev/kvm exists, otherwise TCG (slow but works anywhere).
Exit code 0 = all checks passed.
"""
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

KVM = os.path.exists("/dev/kvm")
OVMF = next((p for p in ["/usr/share/ovmf/OVMF.fd", "/usr/share/OVMF/OVMF_CODE.fd"] if os.path.exists(p)), None)


def extract(iso, member, dest):
    subprocess.run(["xorriso", "-osirrox", "on", "-indev", iso, "-extract", member, dest],
                   check=True, capture_output=True)
    return dest


def qemu_base(iso, tmp, extra=()):
    cmd = ["qemu-system-x86_64", "-m", "2048", "-smp", "2", "-cdrom", iso,
           "-qmp", f"unix:{tmp}/qmp.sock,server=on,wait=off",
           "-serial", f"unix:{tmp}/serial.sock,server=on,wait=off",
           "-display", "none", "-vga", "std", "-no-reboot"]
    cmd += ["-enable-kvm", "-cpu", "host"] if KVM else ["-accel", "tcg,thread=multi", "-cpu", "max"]
    return cmd + list(extra)


class Unix:
    def __init__(self, path, timeout=60):
        end = time.time() + timeout
        while True:
            try:
                self.s = socket.socket(socket.AF_UNIX); self.s.connect(path); break
            except OSError:
                if time.time() > end: raise
                time.sleep(0.2)
        self.s.settimeout(0.5)
        self.buf = b""

    def read(self):
        try:
            data = self.s.recv(65536)
            self.buf += data
            return data
        except socket.timeout:
            return b""

    def send(self, text):
        self.s.sendall(text.encode())


class QMP(Unix):
    def __init__(self, path):
        super().__init__(path)
        self.s.settimeout(10)
        self.s.recv(65536)
        self.cmd("qmp_capabilities")

    def cmd(self, name, **args):
        self.s.sendall(json.dumps({"execute": name, "arguments": args} if args else {"execute": name}).encode())
        out = b""
        while b"return" not in out and b"error" not in out:
            out += self.s.recv(65536)
        return out

    def shot(self, path):
        self.cmd("screendump", filename=str(path))


def wait_for(ser, pattern, timeout, log):
    end = time.time() + timeout
    rx = re.compile(pattern.encode())
    while time.time() < end:
        d = ser.read()
        if d:
            log.write(d); log.flush()
            # systemd/agetty ask the terminal for the cursor position (ESC[6n) to learn its size
            # and can wait for the answer: reply like a 24 x 80 terminal
            for _ in range(d.count(b"\x1b[6n")):   # one answer per query (they can arrive together)
                ser.send("\x1b[24;80R")
        if rx.search(ser.buf):
            return True
    return False


def functional(iso, out):
    tmp = tempfile.mkdtemp()
    k = extract(iso, "/casper/vmlinuz", f"{tmp}/vmlinuz"); i = extract(iso, "/casper/initrd", f"{tmp}/initrd")
    cmd = qemu_base(iso, tmp, ["-kernel", k, "-initrd", i, "-append",
                               "boot=casper console=ttyS0,115200n8 systemd.show_status=1 ---"])
    vm = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    log = open(out / "functional-serial.log", "wb")
    ser = Unix(f"{tmp}/serial.sock")
    results = {}
    t0 = time.time()
    try:
        ok = wait_for(ser, r"login:", 1500 if not KVM else 300, log)
        results["boot_to_login"] = ok
        results["boot_seconds"] = round(time.time() - t0)
        if not ok: return results
        ser.send("droplet\n"); time.sleep(3)
        if b"assword" in ser.buf[-200:]: ser.send("\n")
        wait_for(ser, r"droplet@droplet", 120, log)
        ser.send("export TERM=dumb PAGER=cat SYSTEMD_COLORS=0; unset GREP_COLORS; alias grep='grep --color=never'\n"); time.sleep(2)
        checks = {
            "os_release": ("grep -E '^(NAME|VERSION_ID|ID)=' /etc/os-release", r'NAME="Droplet OS"'),
            "kernel": ("uname -r", r"7\.0\.0-\d+-generic"),
            "system_state": ("systemctl is-system-running --wait", r"\n(running|degraded)\r?\n"),
            "plymouth_theme": ("readlink -f /etc/alternatives/default.plymouth", r"droplet/droplet\.plymouth"),
            "theme_in_initrd": ("lsinitramfs /cdrom/casper/initrd | grep -c 'themes/droplet/intro-'", r"\n82\r?\n"),
            "clean_console_unit": ("systemctl is-enabled droplet-clear-console.service", r"\nenabled"),
            "apparmor": ("sudo aa-enabled", r"\nYes"),
            "ufw": ("sudo ufw status | head -1", r"Status: active"),
            "root_locked": ("sudo passwd -S root", r"root L"),
            "network_manager": ("systemctl is-active NetworkManager", r"\nactive"),
            "packages_installed": ("dpkg -l | grep -c '^ii'", r"\n\d{3}\r?\n"),
        }
        for name, (c, rx) in checks.items():
            mark = f"__END_{name}__"
            ser.buf = b""
            ser.send(f"{c}; echo __E\"\"ND_{name}__\n")      # typed text != printed marker
            wait_for(ser, mark + r"\r?\n", 300, log)
            text = ser.buf.decode(errors="replace")
            text = re.sub(r"\x1b\][^\x1b\x07]*(\x1b\\|\x07)", "\n", text)   # OSC (systemd shell integration)
            text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)              # CSI colours
            results[name] = bool(re.search(rx, text))
            results[name + "_out"] = text.strip().splitlines()[1:-1][-3:]
        ser.buf = b""
        ser.send("systemctl --failed --no-legend; echo __E\"\"ND_failed__\n")
        wait_for(ser, r"__END_failed__\r?\n", 120, log)
        results["failed_units"] = [l for l in ser.buf.decode(errors="replace").splitlines() if ".service" in l or ".mount" in l]
        ser.send("sudo poweroff\n")
        try:
            vm.wait(120)          # clean exit -> QEMU finalises the captured WAV
        except subprocess.TimeoutExpired:
            pass
    finally:
        vm.kill()
    return results


class Session:
    """serial console of the live user, with the graphical session's D-Bus."""
    def __init__(self, ser, log):
        self.ser, self.log = ser, log

    def run(self, c, timeout=300):
        name = f"x{int(time.time() * 1000) % 10**8}"
        self.ser.buf = b""
        self.ser.send(f"{c}; echo __E\"\"ND_{name}__\n")
        wait_for(self.ser, f"__END_{name}__" + r"\r?\n", timeout, self.log)
        text = self.ser.buf.decode(errors="replace")
        text = re.sub(r"\x1b\][^\x1b\x07]*(\x1b\\|\x07)", "\n", text)
        text = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
        return "\n".join(text.strip().splitlines()[1:-1])

    def shell(self, method, *args):
        sig = "".join("b" if isinstance(x, bool) else "s" if isinstance(x, str) else "i" for x in args)
        vals = " ".join(("true" if x else "false") if isinstance(x, bool) else f"'{x}'" if isinstance(x, str) else str(x)
                        for x in args)
        return self.run(f"busctl --user call org.droplet.Shell /Shell org.droplet.Shell {method} {sig} {vals}".rstrip())


def desktop(iso, out):
    """0.2: boots to the Droplet session, checks it and takes real screenshots of each surface."""
    from PIL import Image
    tmp = tempfile.mkdtemp()
    k = extract(iso, "/casper/vmlinuz", f"{tmp}/vmlinuz"); i = extract(iso, "/casper/initrd", f"{tmp}/initrd")
    cmd = ["qemu-system-x86_64", "-m", "4096", "-smp", "2", "-cdrom", iso,
           "-qmp", f"unix:{tmp}/qmp.sock,server=on,wait=off",
           "-serial", f"unix:{tmp}/serial.sock,server=on,wait=off",
           "-display", "none", "-device", "virtio-vga,xres=1440,yres=900", "-no-reboot",
           "-audiodev", "none,id=snd0", "-device", "intel-hda", "-device", "hda-duplex,audiodev=snd0",
           "-kernel", k, "-initrd", i, "-append",
           "boot=casper quiet splash console=ttyS0,115200n8 console=tty1 video=1440x900 ---"]
    # TCG: llvmpipe crashes on QEMU 8.2's emulated AVX ("-cpu max"); a CPU without AVX (128-bit llvmpipe) is stable
    cmd += ["-enable-kvm", "-cpu", "host"] if KVM else ["-accel", "tcg,thread=multi", "-cpu", "Nehalem-v2"]
    vm = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    log = open(out / "desktop-serial.log", "wb")
    ser = Unix(f"{tmp}/serial.sock"); qmp = QMP(f"{tmp}/qmp.sock")
    shots = out / "captures"; shots.mkdir(exist_ok=True)
    results = {}
    t0 = time.time()

    def shot(name):
        ppm = Path(tmp) / f"{name}.ppm"
        qmp.shot(ppm); time.sleep(1.5)
        Image.open(ppm).save(shots / f"{name}.png")
        results.setdefault("captures", []).append(f"{name}.png")

    try:
        ok = wait_for(ser, r"login:", 2400 if not KVM else 300, log)
        results["boot_to_login"] = ok
        if not ok:
            shot("echec-demarrage"); return results
        ser.send("droplet\n"); time.sleep(3)
        if b"assword" in ser.buf[-200:]: ser.send("\n")
        wait_for(ser, r"droplet@droplet", 120, log)
        S = Session(ser, log)
        S.run("export TERM=dumb PAGER=cat SYSTEMD_COLORS=0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/$(id -u)/bus")
        # wait for the shell (TCG + llvmpipe: several minutes)
        for _ in range(120):
            if re.search(r"^\d+$", S.run("pgrep -x droplet-shell | head -1"), re.M):
                break
            time.sleep(10)
        results["seconds_to_shell"] = round(time.time() - t0)
        time.sleep(90 if not KVM else 15)
        checks = {
            "session_droplet": ("loginctl show-session $(loginctl list-sessions --no-legend | awk '/seat0/{print $1; exit}') -p Desktop -p Type", r"(?i)Desktop=droplet[\s\S]*Type=wayland|Type=wayland[\s\S]*Desktop=droplet"),
            "kwin_running": ("pgrep -c kwin_wayland", r"^[1-9]"),
            "shell_running": ("pgrep -c droplet-shell", r"^[1-9]"),
            "compositing_opengl": ("busctl --user call org.kde.KWin /KWin org.kde.KWin supportInformation | sed 's/\\\\n/\\n/g' | grep -iE 'Compositing Type|OpenGL renderer|OpenGL version string' | head -3", r"OpenGL"),
            "glass_effect_loaded": ("busctl --user call org.kde.KWin /Effects org.kde.kwin.Effects isEffectLoaded s dropletglass", r"^b true"),
            "notifications_server": ("busctl --user call org.freedesktop.Notifications /org/freedesktop/Notifications org.freedesktop.Notifications GetServerInformation", r"Droplet Shell"),
            "shell_dbus": ("busctl --user introspect org.droplet.Shell /Shell | grep -c ToggleLauncher", r"^1"),
        }
        for name, (c, rx) in checks.items():
            o = S.run(c)
            results[name] = bool(re.search(rx, o, re.M))
            results[name + "_out"] = o.splitlines()[-3:]
        results["shell_errors"] = S.run("journalctl --user -b --no-pager -o cat 2>/dev/null | grep -iE 'qml|droplet' | grep -iE 'error|warning|unable|cannot' | tail -15").splitlines()

        slow = 1 if KVM else 3
        shot("01-bureau-nuit")
        S.shell("Launch", "org.kde.dolphin.desktop"); time.sleep(25 * slow)
        shot("02-fenetre")
        S.shell("ShowMenu", "droplet"); time.sleep(6 * slow); shot("03-menu-droplet")
        S.shell("ShowMenu", "app"); time.sleep(6 * slow); shot("04-menu-app")
        S.shell("CloseAll"); S.shell("ToggleControlCenter"); time.sleep(6 * slow); shot("05-centre-de-controle")
        S.shell("CloseAll"); S.shell("ToggleLauncher"); time.sleep(6 * slow); shot("06-recherche")
        S.shell("CloseAll"); S.shell("ShowAbout"); time.sleep(6 * slow); shot("07-a-propos")
        S.shell("CloseAll")
        S.run("notify-send -a Fichiers -i org.kde.dolphin 'Copie terminée' '3 éléments copiés dans Documents.'")
        time.sleep(3 * slow); shot("08-notification")
        # appearance: night -> day (the drawn transition), then the living garden
        S.shell("SetDarkMode", False)
        for j in range(4):
            time.sleep(4 * slow); shot(f"09-transition-{j}")
        time.sleep(30 * slow); shot("10-bureau-jour")
        S.shell("ToggleControlCenter"); time.sleep(6 * slow); shot("11-centre-de-controle-jour")
        S.shell("CloseAll")
        ser.send("sudo poweroff\n")
        try:
            vm.wait(180)
        except subprocess.TimeoutExpired:
            pass
    finally:
        vm.kill()
    results["total_seconds"] = round(time.time() - t0)
    return results


def screenshots(iso, out, tag, extra, seconds, every):
    tmp = tempfile.mkdtemp()
    ex = list(extra)
    vm = subprocess.Popen(qemu_base(iso, tmp, ex), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    shots = []
    try:
        q = QMP(f"{tmp}/qmp.sock")
        t0 = time.time()
        n = 0
        while time.time() - t0 < seconds and vm.poll() is None:
            p = out / f"{tag}-{n:03d}.ppm"
            q.shot(p); shots.append((round(time.time() - t0, 1), p)); n += 1
            time.sleep(every)
    finally:
        vm.terminate(); time.sleep(2); vm.kill()
    return shots


def main():
    mode, iso, out = sys.argv[1], sys.argv[2], Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
    if mode == "functional":
        r = functional(iso, out)
        (out / "functional.json").write_text(json.dumps(r, indent=1))
        bools = {k: v for k, v in r.items() if isinstance(v, bool)}
        print(json.dumps(r, indent=1))
        sys.exit(0 if all(bools.values()) else 1)
    if mode == "desktop":
        r = desktop(iso, out)
        (out / "desktop.json").write_text(json.dumps(r, indent=1, ensure_ascii=False))
        print(json.dumps(r, indent=1, ensure_ascii=False))
        bools = {k: v for k, v in r.items() if isinstance(v, bool)}
        sys.exit(0 if bools and all(bools.values()) else 1)
    slow = 1 if KVM else 1.4   # TCG: boot to login takes ~100 s
    if mode == "visual":
        tmp = tempfile.mkdtemp()
        k = extract(iso, "/casper/vmlinuz", f"{tmp}/vmlinuz"); i = extract(iso, "/casper/initrd", f"{tmp}/initrd")
        shots = screenshots(iso, out, "visual", ["-kernel", k, "-initrd", i, "-append",
                            "boot=casper quiet splash loglevel=3 systemd.show_status=false video=1920x1080 vt.global_cursor_default=0 ---"],
                            seconds=110 * slow, every=0.5 if KVM else 1.0)
    elif mode == "bios":
        shots = screenshots(iso, out, "bios", [], seconds=100 * slow, every=3.0)
    elif mode == "uefi":
        if not OVMF: print("OVMF not installed"); sys.exit(2)
        shots = screenshots(iso, out, "uefi", ["-bios", OVMF], seconds=100 * slow, every=3.0)
    print(json.dumps([(t, str(p)) for t, p in shots]))


if __name__ == "__main__":
    main()
