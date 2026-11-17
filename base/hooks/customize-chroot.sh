#!/usr/bin/env bash
# Runs INSIDE the rootfs chroot. Applies Droplet identity, live config and security baseline.
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive LC_ALL=C

# --- identity ---------------------------------------------------------------
# /etc/os-release is a symlink to /usr/lib/os-release on Ubuntu. We keep ID_LIKE=ubuntu
# so that apt tooling and third-party scripts keep working, and keep the Ubuntu
# UBUNTU_CODENAME so PPAs / repos resolve. We do NOT use Ubuntu trademarks as our name.
cat > /usr/lib/os-release <<EOF
PRETTY_NAME="Droplet OS ${DROPLET_VERSION}"
NAME="Droplet OS"
VERSION_ID="${DROPLET_VERSION}"
VERSION="${DROPLET_VERSION} (${DROPLET_CODENAME})"
VERSION_CODENAME=${DROPLET_CODENAME}
ID=droplet
ID_LIKE="ubuntu debian"
UBUNTU_CODENAME=resolute
HOME_URL="https://github.com/droplet-os/droplet-os"
LOGO=droplet-logo
EOF
ln -sf ../usr/lib/os-release /etc/os-release
printf 'Droplet OS %s \\n \\l\n\n' "$DROPLET_VERSION" > /etc/issue
printf 'Droplet OS %s\n' "$DROPLET_VERSION" > /etc/issue.net
echo "$LIVE_HOSTNAME" > /etc/hostname
printf '127.0.0.1 localhost\n127.0.1.1 %s\n::1 localhost ip6-localhost ip6-loopback\n' "$LIVE_HOSTNAME" > /etc/hosts
echo "${DROPLET_VERSION}" > /etc/droplet-release

# --- locale / time / keyboard -----------------------------------------------
sed -i "s/^# *\(${DEFAULT_LOCALE} UTF-8\)/\1/; s/^# *\(en_US.UTF-8 UTF-8\)/\1/" /etc/locale.gen
locale-gen >/dev/null
update-locale LANG="$DEFAULT_LOCALE"
ln -sf "/usr/share/zoneinfo/${DEFAULT_TIMEZONE}" /etc/localtime
echo "$DEFAULT_TIMEZONE" > /etc/timezone
sed -i "s/^XKBLAYOUT=.*/XKBLAYOUT=\"${DEFAULT_KEYMAP}\"/" /etc/default/keyboard

# --- live session (casper) ----------------------------------------------------
cat > /etc/casper.conf <<EOF
export USERNAME="${LIVE_USER}"
export USERFULLNAME="Droplet Live"
export HOST="${LIVE_HOSTNAME}"
export BUILD_SYSTEM="Ubuntu"
export FLAVOUR="Droplet"
EOF

# --- networking: NetworkManager owns all interfaces ---------------------------
install -d /etc/NetworkManager/conf.d
printf '[keyfile]\nunmanaged-devices=none\n' > /etc/NetworkManager/conf.d/10-droplet-manage-all.conf
systemctl enable NetworkManager.service systemd-resolved.service >/dev/null 2>&1 || true

# --- security baseline ----------------------------------------------------------
# AppArmor: enabled by default in Ubuntu kernels; make sure the service is on.
systemctl enable apparmor.service >/dev/null 2>&1 || true
# UFW: deny incoming / allow outgoing; enabled at boot (iptables is not usable in chroot,
# so we set the persistent flag instead of calling `ufw enable`).
sed -i 's/^DEFAULT_INPUT_POLICY=.*/DEFAULT_INPUT_POLICY="DROP"/; s/^DEFAULT_OUTPUT_POLICY=.*/DEFAULT_OUTPUT_POLICY="ACCEPT"/' /etc/default/ufw
sed -i 's/^ENABLED=.*/ENABLED=yes/' /etc/ufw/ufw.conf
systemctl enable ufw.service >/dev/null 2>&1 || true
# No root password; root login over console is locked (sudo for the live user only).
passwd -l root >/dev/null

# --- DROPLET BOOT: Plymouth ------------------------------------------------------
# Register the theme and make it the default. If the theme ever fails to load,
# plymouth falls back to its built-in text/details splash (boot is never blocked).
update-alternatives --install /usr/share/plymouth/themes/default.plymouth default.plymouth \
  /usr/share/plymouth/themes/droplet/droplet.plymouth 200 >/dev/null
update-alternatives --set default.plymouth /usr/share/plymouth/themes/droplet/droplet.plymouth >/dev/null
printf "[Daemon]\nTheme=droplet\nShowDelay=0\nDeviceTimeout=8\n" > /etc/plymouth/plymouthd.conf

# --- clean handoff: clear tty1 when the splash ends (no firmware/systemd text left) ----
systemctl enable droplet-clear-console.service >/dev/null 2>&1

# --- initramfs: rebuild so it contains casper + the droplet theme ---------------
update-initramfs -u -k all >/dev/null 2>&1 || update-initramfs -u -k all

# --- cleanup -------------------------------------------------------------------
apt-get clean
rm -rf /var/lib/apt/lists/* /var/log/*.log /root/.bash_history
truncate -s 0 /etc/machine-id    # regenerated on first boot
