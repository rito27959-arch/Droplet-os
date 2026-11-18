#include "system.h"

#include <QCoreApplication>
#include <QDir>
#include <QFile>
#include <QLocale>
#include <QProcess>
#include <QRegularExpression>
#include <QSettings>
#include <QDBusConnection>
#include <QDBusMessage>
#include <KConfigGroup>
#include <KSharedConfig>
#include <QStandardPaths>
#include <QStorageInfo>
#include <QSysInfo>

SystemControl::SystemControl(QObject *parent)
    : QObject(parent)
{
    // single source of truth: the colour scheme the applications use
    const KConfigGroup g(KSharedConfig::openConfig(QStringLiteral("kdeglobals")), QStringLiteral("General"));
    m_dark = g.readEntry("ColorScheme", QStringLiteral("DropletSombre")) != QLatin1String("DropletClair");
    m_reduceMotion = KConfigGroup(KSharedConfig::openConfig(QStringLiteral("kdeglobals")), QStringLiteral("KDE"))
                         .readEntry("AnimationDurationFactor", 1.0) <= 0.0;
    m_watcher = KConfigWatcher::create(KSharedConfig::openConfig(QStringLiteral("kdeglobals")));
    connect(m_watcher.data(), &KConfigWatcher::configChanged, this, [this](const KConfigGroup &g) {
        if (g.name() != QLatin1String("KDE")) return;
        const bool r = g.readEntry("AnimationDurationFactor", 1.0) <= 0.0;
        if (r != m_reduceMotion) { m_reduceMotion = r; Q_EMIT reduceMotionChanged(); }
    });
    connect(&m_poll, &QTimer::timeout, this, &SystemControl::refresh);
    m_poll.start(30000);
    refresh();
}

void SystemControl::run(const QString &program, const QStringList &args, std::function<void(int, const QString &)> done)
{
    if (QStandardPaths::findExecutable(program).isEmpty()) {
        if (done) done(-1, {});
        return;
    }
    auto *p = new QProcess(this);
    connect(p, &QProcess::finished, this, [p, done](int code, QProcess::ExitStatus) {
        if (done) done(code, QString::fromUtf8(p->readAllStandardOutput()));
        p->deleteLater();
    });
    p->start(program, args);
}

void SystemControl::setFastPoll(bool fast)
{
    if (fast == m_fastPoll) return;
    m_fastPoll = fast;
    m_poll.start(fast ? 2000 : 30000);
    if (fast) refresh();   // fresh values the moment the Control Centre opens
    Q_EMIT fastPollChanged();
}

void SystemControl::refresh()
{
    // Network (NetworkManager)
    run(QStringLiteral("nmcli"), {QStringLiteral("-t"), QStringLiteral("-f"), QStringLiteral("TYPE,STATE,CONNECTION"), QStringLiteral("device")},
        [this](int code, const QString &out) {
            m_wifiAvailable = false; m_wired = false; m_network.clear();
            if (code == 0) {
                for (const QString &line : out.split(u'\n', Qt::SkipEmptyParts)) {
                    const QStringList f = line.split(u':');
                    if (f.size() < 3) continue;
                    if (f[0] == u"wifi") { m_wifiAvailable = true; if (f[1] == u"connected") m_network = f[2]; }
                    if (f[0] == u"ethernet" && f[1] == u"connected") { m_wired = true; if (m_network.isEmpty()) m_network = f[2]; }
                }
            }
            Q_EMIT changed();
        });
    run(QStringLiteral("nmcli"), {QStringLiteral("radio"), QStringLiteral("wifi")}, [this](int code, const QString &out) {
        m_wifiEnabled = code == 0 && out.trimmed() == u"enabled";
        Q_EMIT changed();
    });
    // Bluetooth (rfkill)
    run(QStringLiteral("rfkill"), {QStringLiteral("-n"), QStringLiteral("-o"), QStringLiteral("SOFT"), QStringLiteral("list"), QStringLiteral("bluetooth")},
        [this](int code, const QString &out) {
            const QString o = out.trimmed();
            m_btAvailable = code == 0 && !o.isEmpty();
            m_btEnabled = m_btAvailable && o.contains(u"unblocked");
            Q_EMIT changed();
        });
    // Audio (PipeWire / WirePlumber)
    run(QStringLiteral("wpctl"), {QStringLiteral("get-volume"), QStringLiteral("@DEFAULT_AUDIO_SINK@")}, [this](int code, const QString &out) {
        static const QRegularExpression re(QStringLiteral(R"(Volume:\s*([0-9.]+))"));
        const auto m = re.match(out);
        m_audioAvailable = code == 0 && m.hasMatch();
        if (m_audioAvailable) {
            m_volume = qRound(m.captured(1).toDouble() * 100);
            m_muted = out.contains(u"MUTED");
        }
        Q_EMIT changed();
    });
    // Backlight
    run(QStringLiteral("brightnessctl"), {QStringLiteral("-m"), QStringLiteral("-c"), QStringLiteral("backlight")}, [this](int code, const QString &out) {
        const QStringList f = out.trimmed().split(u',');
        m_brightnessAvailable = code == 0 && f.size() >= 4;
        if (m_brightnessAvailable)
            m_brightness = QString(f[3]).remove(u'%').toInt();
        Q_EMIT changed();
    });
    readBattery();
    readStorage();
}

void SystemControl::readBattery()
{
    const QDir dir(QStringLiteral("/sys/class/power_supply"));
    m_batteryPresent = false;
    for (const QString &e : dir.entryList({QStringLiteral("BAT*")}, QDir::Dirs | QDir::NoDotAndDotDot)) {
        QFile cap(dir.filePath(e + QStringLiteral("/capacity")));
        QFile st(dir.filePath(e + QStringLiteral("/status")));
        if (cap.open(QIODevice::ReadOnly)) {
            m_batteryPresent = true;
            m_battery = QString::fromLatin1(cap.readAll()).trimmed().toInt();
            if (st.open(QIODevice::ReadOnly))
                m_charging = QString::fromLatin1(st.readAll()).trimmed() == u"Charging";
            break;
        }
    }
}

void SystemControl::readStorage()
{
    const QStorageInfo home(QDir::homePath());
    const QLocale fr(QLocale::French);
    const double gb = home.bytesAvailable() / 1e9, total = home.bytesTotal() / 1e9;
    m_freeSpace = fr.toString(gb, 'f', gb < 10 ? 1 : 0) + QStringLiteral(" Go disponibles");
    m_totalSpace = QStringLiteral("sur ") + fr.toString(total, 'f', total < 10 ? 1 : 0) + QStringLiteral(" Go");
    m_storageUsed = home.bytesTotal() > 0 ? 1.0 - double(home.bytesAvailable()) / home.bytesTotal() : 0;
    Q_EMIT changed();
}

void SystemControl::setWifi(bool on)
{
    run(QStringLiteral("nmcli"), {QStringLiteral("radio"), QStringLiteral("wifi"), on ? QStringLiteral("on") : QStringLiteral("off")},
        [this](int, const QString &) { refresh(); });
}

void SystemControl::setBluetooth(bool on)
{
    run(QStringLiteral("rfkill"), {on ? QStringLiteral("unblock") : QStringLiteral("block"), QStringLiteral("bluetooth")},
        [this](int, const QString &) { refresh(); });
}

void SystemControl::setVolume(int percent)
{
    percent = std::clamp(percent, 0, 100);
    m_volume = percent;
    Q_EMIT changed();
    run(QStringLiteral("wpctl"), {QStringLiteral("set-volume"), QStringLiteral("@DEFAULT_AUDIO_SINK@"),
                                  QString::number(percent / 100.0, 'f', 2)});
}

void SystemControl::toggleMute()
{
    run(QStringLiteral("wpctl"), {QStringLiteral("set-mute"), QStringLiteral("@DEFAULT_AUDIO_SINK@"), QStringLiteral("toggle")},
        [this](int, const QString &) { refresh(); });
}

void SystemControl::setBrightness(int percent)
{
    percent = std::clamp(percent, 1, 100);
    m_brightness = percent;
    Q_EMIT changed();
    run(QStringLiteral("brightnessctl"), {QStringLiteral("-q"), QStringLiteral("-c"), QStringLiteral("backlight"),
                                          QStringLiteral("set"), QString::number(percent) + u'%'});
}

void SystemControl::setDarkMode(bool dark)
{
    if (dark == m_dark)
        return;
    m_dark = dark;
    Q_EMIT darkModeChanged();
    const QString scheme = dark ? QStringLiteral("DropletSombre") : QStringLiteral("DropletClair");

    // 1. applications: colour scheme (writes kdeglobals and notifies running apps)
    run(QStringLiteral("plasma-apply-colorscheme"), {scheme});

    // 2. icons that read well on the new background
    KConfigGroup icons(KSharedConfig::openConfig(QStringLiteral("kdeglobals")), QStringLiteral("Icons"));
    icons.writeEntry("Theme", dark ? QStringLiteral("breeze-dark") : QStringLiteral("breeze"), KConfig::Notify);
    icons.sync();
    QDBusMessage iconSig = QDBusMessage::createSignal(QStringLiteral("/KIconLoader"), QStringLiteral("org.kde.KIconLoader"),
                                                      QStringLiteral("iconChanged"));
    iconSig << 0;
    QDBusConnection::sessionBus().send(iconSig);

    // 3. window decoration, then ask KWin to reload its configuration
    KConfigGroup deco(KSharedConfig::openConfig(QStringLiteral("kwinrc")), QStringLiteral("org.kde.kdecoration2"));
    deco.writeEntry("theme", QStringLiteral("__aurorae__svg__") + scheme);
    deco.sync();
    QDBusConnection::sessionBus().send(QDBusMessage::createSignal(QStringLiteral("/KWin"), QStringLiteral("org.kde.KWin"),
                                                                  QStringLiteral("reloadConfig")));
}

void SystemControl::suspend() { run(QStringLiteral("systemctl"), {QStringLiteral("suspend")}); }
void SystemControl::reboot() { run(QStringLiteral("systemctl"), {QStringLiteral("reboot")}); }
void SystemControl::powerOff() { run(QStringLiteral("systemctl"), {QStringLiteral("poweroff")}); }
void SystemControl::lock() { run(QStringLiteral("loginctl"), {QStringLiteral("lock-session")}); }
void SystemControl::logout() { QCoreApplication::quit(); } // the session ends with the shell

void SystemControl::openSettings(const QString &module)
{
    QStringList args;
    if (!module.isEmpty()) args << module;
    QProcess::startDetached(QStringLiteral("systemsettings"), args);
}

QVariantMap SystemControl::about() const
{
    QVariantMap m;
    QString cpu, mem;
    QFile f(QStringLiteral("/proc/cpuinfo"));
    if (f.open(QIODevice::ReadOnly)) {
        for (const QByteArray &l : f.readAll().split('\n'))
            if (l.startsWith("model name")) { cpu = QString::fromUtf8(l.mid(l.indexOf(':') + 1)).trimmed(); break; }
    }
    QFile mi(QStringLiteral("/proc/meminfo"));
    if (mi.open(QIODevice::ReadOnly)) {
        const QByteArray l = mi.readLine();
        const double gb = QString::fromLatin1(l).section(u':', 1).trimmed().section(u' ', 0, 0).toDouble() / 1024 / 1024;
        mem = QLocale(QLocale::French).toString(gb, 'f', 1) + QStringLiteral(" Go");
    }
    QSettings osr(QStringLiteral("/etc/os-release"), QSettings::IniFormat);
    m[QStringLiteral("version")] = osr.value(QStringLiteral("VERSION")).toString();
    m[QStringLiteral("cpu")] = cpu;
    m[QStringLiteral("memory")] = mem;
    m[QStringLiteral("kernel")] = QSysInfo::kernelVersion();
    m[QStringLiteral("host")] = QSysInfo::machineHostName();
    return m;
}
