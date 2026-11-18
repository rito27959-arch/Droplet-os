#include "shell.h"

#include <KGlobalAccel>
#include <QAction>
#include <QDBusConnection>
#include <KIO/OpenUrlJob>
#include <KService>
#include <QFile>
#include <QUrl>

#include "apps.h"
#include "system.h"

Shell::Shell(QObject *parent)
    : QObject(parent)
{
    auto bus = QDBusConnection::sessionBus();
    bus.registerService(QStringLiteral("org.droplet.Shell"));
    bus.registerObject(QStringLiteral("/Shell"), this, QDBusConnection::ExportAllSlots);

    // Super + Space opens the launcher (KGlobalAccel, Wayland-safe)
    auto *launcher = new QAction(this);
    launcher->setObjectName(QStringLiteral("toggle-launcher"));
    launcher->setText(QStringLiteral("Ouvrir la recherche"));
    launcher->setProperty("componentName", QStringLiteral("droplet-shell"));
    launcher->setProperty("componentDisplayName", QStringLiteral("Droplet Shell"));
    KGlobalAccel::self()->setDefaultShortcut(launcher, {QKeySequence(Qt::META | Qt::Key_Space)});
    KGlobalAccel::self()->setShortcut(launcher, {QKeySequence(Qt::META | Qt::Key_Space)});
    connect(launcher, &QAction::triggered, this, &Shell::ToggleLauncher);
}

QString Shell::dataDir() const
{
    const QByteArray env = qgetenv("DROPLET_DATA_DIR");
    return QStringLiteral("file://") + (env.isEmpty() ? QStringLiteral("/usr/share/droplet") : QString::fromLocal8Bit(env));
}

QString Shell::iconFor(const QString &appId) const
{
    return AppsModel::iconForDesktopId(appId);
}

void Shell::openUrl(const QString &url)
{
    auto *job = new KIO::OpenUrlJob(QUrl(url));
    job->start();
}

void Shell::launch(const QString &storageId)
{
    AppsModel::launchId(storageId);
}

QString Shell::readText(const QString &url) const
{
    QFile f(QUrl(url).isLocalFile() ? QUrl(url).toLocalFile() : url);
    return f.open(QIODevice::ReadOnly) ? QString::fromUtf8(f.readAll()) : QString();
}

QStringList Shell::launchers(const QStringList &storageIds) const
{
    QStringList out;
    for (const QString &id : storageIds)
        if (KService::serviceByStorageId(id))
            out << QStringLiteral("applications:") + id;
    return out;
}

void Shell::ToggleLauncher()
{
    m_launcherOpen = !m_launcherOpen;
    if (m_launcherOpen) { m_ccOpen = false; m_openMenu.clear(); Q_EMIT controlCenterOpenChanged(); Q_EMIT openMenuChanged(); }
    Q_EMIT launcherOpenChanged();
}

void Shell::ToggleControlCenter()
{
    m_ccOpen = !m_ccOpen;
    if (m_ccOpen) { m_launcherOpen = false; m_openMenu.clear(); Q_EMIT launcherOpenChanged(); Q_EMIT openMenuChanged(); }
    Q_EMIT controlCenterOpenChanged();
}

void Shell::ShowMenu(const QString &name)
{
    m_openMenu = (m_openMenu == name) ? QString() : name;
    if (!m_openMenu.isEmpty() && m_ccOpen) { m_ccOpen = false; Q_EMIT controlCenterOpenChanged(); }
    Q_EMIT openMenuChanged();
}

void Shell::ShowAbout()
{
    CloseAll();
    m_aboutOpen = true;
    Q_EMIT aboutOpenChanged();
}

void Shell::CloseAll()
{
    m_launcherOpen = m_ccOpen = m_aboutOpen = false;
    m_openMenu.clear();
    Q_EMIT aboutOpenChanged();
    Q_EMIT launcherOpenChanged();
    Q_EMIT controlCenterOpenChanged();
    Q_EMIT openMenuChanged();
}

void Shell::SetDarkMode(bool dark)
{
    // the QML engine owns the SystemControl singleton; reach it through the same engine
    if (auto *engine = qmlEngine(this))
        if (auto *sys = engine->singletonInstance<SystemControl *>("Droplet", "SystemControl"))
            sys->setDarkMode(dark);
}
