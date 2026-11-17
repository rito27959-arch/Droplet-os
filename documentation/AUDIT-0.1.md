# Droplet OS 0.1 — technical audit (verified 2026-11-17)

Sources: Ubuntu archive indexes for `resolute` (main/universe, amd64) queried directly,
upstream repositories shallow-cloned, release announcements. Nothing below is assumed.

## 1. Base

| Item | Choice | Evidence |
|---|---|---|
| Ubuntu LTS | **26.04 "Resolute Raccoon"** | released 2026-04-23; standard support to 2031; Kubuntu flavour to 2029 |
| Kernel | linux-generic **7.0.0-14** | archive index |
| Qt 6 | **6.10.2** (frozen for the LTS) | archive `qt6-base-dev 6.10.2+dfsg-7` |
| KDE Plasma / KWin | **6.6.4** (Wayland only, no X11 session in Kubuntu 26.04) | `kwin-wayland 4:6.6.4` |
| KDE Frameworks / Gear | 6.24 / 25.12.3, maintained 3 years ("Bullet-Proof KDE") | Kubuntu announcement |
| Plymouth | 24.004.60 (script plugin in `plymouth`) | Contents index |
| casper (live) | 26.04.2 | archive |
| Installer candidate | calamares 3.3.14 available; Ubuntu uses subiquity/curtin | archive |

**Compatibility Wayland / KWin / Qt 6: OK** — Plasma 6.6 is built on Qt 6.10.2 in the
same archive; no PPA needed for 0.1/0.2.

## 2. The 15 applications

| App | Repo checked | Last commit | Licence | Ubuntu 26.04 pkg | Toolkit | Notes |
|---|---|---|---|---|---|---|
| Dolphin | KDE/dolphin ✅ | 2026-11-17 | GPL-2.0+ (REUSE) | 25.12.3 | Qt 6 | |
| Konsole | KDE/konsole ✅ | 2026-11-17 | GPL-2.0+ | 25.12.3 | Qt 6 | |
| Kate | KDE/kate ✅ | 2026-11-17 | GPL-2.0+/LGPL | 25.12.3 | Qt 6 | |
| Okular | KDE/okular ✅ | 2026-11-17 | GPL-2.0+ | 25.12.3 | Qt 6 | |
| Ark | KDE/ark ✅ | 2026-11-17 | GPL-2.0+ | 25.12.3 | Qt 6 | |
| KCalc | KDE/kcalc ✅ | 2026-11-17 | GPL-2.0+ | 25.12.3 | Qt 6 | |
| Gwenview | KDE/gwenview ✅ | 2026-11-17 | GPL-2.0 | 25.12.3 | Qt 6 | |
| Elisa | KDE/elisa ✅ | 2026-11-16 | LGPL-3.0+ | 25.12.3 | Qt 6 | |
| Haruna | **HarunaProject/haruna ✗ (not reachable)** → KDE/haruna ✅ | 2026-11-17 | GPL-3.0+ | 1.7.1 | Qt 6 | project lives at KDE |
| Spectacle | KDE/spectacle ✅ | 2026-11-17 | GPL-2.0+ | `kde-spectacle` 25.12.3 | Qt 6 | master needs Qt 6.11 → use the Ubuntu package, do not build master |
| KeePassXC | keepassxreboot/keepassxc ✅ | 2026-11-15 | GPL-2/3 | 2.7.10 | **Qt 5** in Ubuntu | upstream master is Qt 6 |
| Mission Center | **mission-center-devs/mission-center ✗ on GitHub** (lives on GitLab) | — | GPL-3.0+ | **not packaged** | **GTK4/libadwaita (Rust)** | Flathub only; not Qt — consider Plasma System Monitor |
| Falkon | KDE/falkon ✅ | 2026-11-17 | GPL-3.0 | 25.12.3 | Qt 6 (WebEngine) | |
| KAIChat | **AdrianKohler/KAIChat ✗ (does not exist / not reachable)** | — | GPL-3.0+ (KDE) | **not packaged** | Qt 6/Kirigami | real project: KDE KAIChat 0.9.0 (2026-10-06), apps.kde.org |
| Crow Translate | crow-translate/crow-translate (GitHub mirror, stale 2024) → invent.kde.org | — | GPL-3.0+ | 2.11.1 (**Qt 5**) | Qt 6 upstream since 4.0.2 | use Flatpak or build 4.x |

Spec corrections: 3 repository URLs in the spec are wrong or obsolete (Haruna, Mission
Center, KAIChat). Qt 5 is still required by 2 Ubuntu packages (KeePassXC, Crow Translate):
acceptable (Qt 5.15.18 ships in 26.04), or use their Qt 6 Flatpaks.

## 3. WhiteSur icon theme

vinceliuice/WhiteSur-icon-theme — **GPL-3.0**, active (2026-09-10), 84 MB source.
Contains Apple marks: `start-here` is the **Apple logo** by default (`install.sh -p`
replaces it with the KDE logo) plus `folder-apple`, `application-vnd.apple.*` icons.
Decision: install with our own `start-here` (Droplet mark) and keep GPL notices; long term
replace with DROPLET AURA ICONS. Redistribution is fine under GPL-3.0 with source.

## 4. Boot components

Selected: **Plymouth (script plugin)** + own pre-rendered theme. Studied: adi1090x
plymouth-themes (GPL-3.0, last commit 2023-08, frame-sequence technique reused as an
idea, no assets reused). Not used: EasySplash/xbootsplash (embedded-oriented), Dragon Boot,
CipherBoot, Vortex (no need for third-party art).

## 5. Hardware estimate (0.1 live, measured)

ISO 432 MB (vm profile). RAM: boots in a 2 GB VM; 1 GB minimum for the console base.
With the 0.2 Plasma session: 4 GB recommended, 2 GB minimum. Any x86-64 with
UEFI or BIOS; GPU: none required for the splash (2D image swaps).

## 6. Licences

Droplet code: GPL-3.0-or-later (compatible with WhiteSur GPL-3.0 and KDE GPL-2.0+).
Artwork (splash, logotype): original, generated from code in this repository.
Font used in pre-rendered texts: Inter (SIL OFL 1.1).
