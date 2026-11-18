// Droplet Shell — real system controls (no fake buttons: every action changes the system)
#pragma once

#include <QObject>
#include <QQmlEngine>
#include <QTimer>
#include <KConfigWatcher>

class SystemControl : public QObject
{
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON

    Q_PROPERTY(bool wifiAvailable MEMBER m_wifiAvailable NOTIFY changed)
    Q_PROPERTY(bool wifiEnabled MEMBER m_wifiEnabled NOTIFY changed)
    Q_PROPERTY(QString network MEMBER m_network NOTIFY changed)
    Q_PROPERTY(bool wired MEMBER m_wired NOTIFY changed)
    Q_PROPERTY(bool bluetoothAvailable MEMBER m_btAvailable NOTIFY changed)
    Q_PROPERTY(bool bluetoothEnabled MEMBER m_btEnabled NOTIFY changed)
    Q_PROPERTY(bool audioAvailable MEMBER m_audioAvailable NOTIFY changed)
    Q_PROPERTY(int volume MEMBER m_volume NOTIFY changed)
    Q_PROPERTY(bool muted MEMBER m_muted NOTIFY changed)
    Q_PROPERTY(bool brightnessAvailable MEMBER m_brightnessAvailable NOTIFY changed)
    Q_PROPERTY(int brightness MEMBER m_brightness NOTIFY changed)
    Q_PROPERTY(bool batteryPresent MEMBER m_batteryPresent NOTIFY changed)
    Q_PROPERTY(int battery MEMBER m_battery NOTIFY changed)
    Q_PROPERTY(bool charging MEMBER m_charging NOTIFY changed)
    Q_PROPERTY(bool darkMode READ darkMode WRITE setDarkMode NOTIFY darkModeChanged)
    Q_PROPERTY(QString freeSpace MEMBER m_freeSpace NOTIFY changed)
    Q_PROPERTY(QString totalSpace MEMBER m_totalSpace NOTIFY changed)
    Q_PROPERTY(qreal storageUsed MEMBER m_storageUsed NOTIFY changed)
    Q_PROPERTY(QVariantMap about READ about CONSTANT)
    // poll the network/audio/backlight tools every 2 s while shown, every 30 s otherwise
    Q_PROPERTY(bool fastPoll READ fastPoll WRITE setFastPoll NOTIFY fastPollChanged)
    // KDE's "Animation speed: instant" (kdeglobals [KDE] AnimationDurationFactor=0)
    Q_PROPERTY(bool reduceMotion READ reduceMotion NOTIFY reduceMotionChanged)

public:
    explicit SystemControl(QObject *parent = nullptr);

    bool darkMode() const { return m_dark; }
    bool fastPoll() const { return m_fastPoll; }
    void setFastPoll(bool fast);
    bool reduceMotion() const { return m_reduceMotion; }
    void setDarkMode(bool dark);
    QVariantMap about() const;

    Q_INVOKABLE void setWifi(bool on);
    Q_INVOKABLE void setBluetooth(bool on);
    Q_INVOKABLE void setVolume(int percent);
    Q_INVOKABLE void toggleMute();
    Q_INVOKABLE void setBrightness(int percent);
    Q_INVOKABLE void suspend();
    Q_INVOKABLE void reboot();
    Q_INVOKABLE void powerOff();
    Q_INVOKABLE void lock();
    Q_INVOKABLE void logout();
    Q_INVOKABLE void openSettings(const QString &module = {});
    Q_INVOKABLE void refresh();

Q_SIGNALS:
    void changed();
    void darkModeChanged();
    void fastPollChanged();
    void reduceMotionChanged();

private:
    void run(const QString &program, const QStringList &args, std::function<void(int, const QString &)> done = {});
    void readBattery();
    void readStorage();

    QTimer m_poll;
    bool m_wifiAvailable = false, m_wifiEnabled = false, m_wired = false;
    QString m_network;
    bool m_btAvailable = false, m_btEnabled = false;
    bool m_audioAvailable = false, m_muted = false;
    int m_volume = 0;
    bool m_brightnessAvailable = false;
    int m_brightness = 0;
    bool m_batteryPresent = false, m_charging = false;
    int m_battery = 0;
    bool m_dark = true;
    bool m_fastPoll = false;
    bool m_reduceMotion = false;
    KConfigWatcher::Ptr m_watcher;
    QString m_freeSpace, m_totalSpace;
    qreal m_storageUsed = 0;
};
