// Droplet Shell — shell-wide state, global shortcut and D-Bus control (org.droplet.Shell)
#pragma once

#include <QObject>
#include <QQmlEngine>

class Shell : public QObject
{
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    Q_CLASSINFO("D-Bus Interface", "org.droplet.Shell")
    Q_PROPERTY(bool launcherOpen MEMBER m_launcherOpen NOTIFY launcherOpenChanged)
    Q_PROPERTY(bool controlCenterOpen MEMBER m_ccOpen NOTIFY controlCenterOpenChanged)
    Q_PROPERTY(QString openMenu MEMBER m_openMenu NOTIFY openMenuChanged)
    Q_PROPERTY(bool aboutOpen MEMBER m_aboutOpen NOTIFY aboutOpenChanged)
    Q_PROPERTY(QString dataDir READ dataDir CONSTANT)

public:
    explicit Shell(QObject *parent = nullptr);
    // file:// URL of the shared data (icons, symbols, wallpapers); DROPLET_DATA_DIR overrides for development
    QString dataDir() const;
    Q_INVOKABLE QString iconFor(const QString &appId) const;
    Q_INVOKABLE void openUrl(const QString &url);
    Q_INVOKABLE void launch(const QString &storageId);
    // ["applications:x.desktop", ...] for the ids that are actually installed
    Q_INVOKABLE QStringList launchers(const QStringList &storageIds) const;
    // small data files shipped with the shell (QML's XMLHttpRequest may not read local files)
    Q_INVOKABLE QString readText(const QString &url) const;

public Q_SLOTS:  // also exported on D-Bus (used by tests and screenshots)
    void ToggleLauncher();
    void ToggleControlCenter();
    void ShowMenu(const QString &name);
    void ShowAbout();
    void CloseAll();
    void Launch(const QString &storageId) { launch(storageId); }
    void SetDarkMode(bool dark);

Q_SIGNALS:
    void launcherOpenChanged();
    void controlCenterOpenChanged();
    void openMenuChanged();
    void aboutOpenChanged();

private:
    bool m_launcherOpen = false;
    bool m_ccOpen = false;
    bool m_aboutOpen = false;
    QString m_openMenu;
};
