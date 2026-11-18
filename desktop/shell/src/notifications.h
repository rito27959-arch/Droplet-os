// Droplet Shell — org.freedesktop.Notifications server (spec 1.2)
#pragma once

#include <QAbstractListModel>
#include <QDateTime>
#include <QDBusAbstractAdaptor>
#include <QQmlEngine>
#include <QTimer>

struct Notification {
    uint id = 0;
    QString appName, appIcon, summary, body;
    QStringList actions;
    QDateTime time;
};

class NotificationServer : public QAbstractListModel
{
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    Q_PROPERTY(bool doNotDisturb READ doNotDisturb WRITE setDoNotDisturb NOTIFY doNotDisturbChanged)
    Q_PROPERTY(bool registered MEMBER m_registered CONSTANT)
    Q_PROPERTY(int count READ count NOTIFY countChanged)

public:
    enum Roles { IdRole = Qt::UserRole + 1, AppNameRole, AppIconRole, SummaryRole, BodyRole, TimeRole, ActionsRole };
    explicit NotificationServer(QObject *parent = nullptr);

    int rowCount(const QModelIndex &parent = {}) const override;
    QVariant data(const QModelIndex &index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

    bool doNotDisturb() const { return m_dnd; }
    int count() const { return int(m_items.size()); }
    void setDoNotDisturb(bool on);

    Q_INVOKABLE void dismiss(uint id);
    Q_INVOKABLE void invoke(uint id, const QString &actionKey);

    // called by the D-Bus adaptor
    uint notify(const QString &app_name, uint replaces_id, const QString &app_icon, const QString &summary,
                const QString &body, const QStringList &actions, const QVariantMap &hints, int expire_timeout);
    void close(uint id);

Q_SIGNALS:
    void closed(uint id, uint reason);
    void actionInvoked(uint id, const QString &actionKey);
    void doNotDisturbChanged();
    void countChanged();

private:
    void remove(uint id, uint reason);
    QList<Notification> m_items;   // banners on screen
    uint m_next = 1;
    bool m_dnd = false;
    bool m_registered = false;
};

// org.freedesktop.Notifications on the session bus (spec 1.2)
class NotificationsAdaptor : public QDBusAbstractAdaptor
{
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface", "org.freedesktop.Notifications")
public:
    explicit NotificationsAdaptor(NotificationServer *server);

public Q_SLOTS:
    QStringList GetCapabilities();
    uint Notify(const QString &app_name, uint replaces_id, const QString &app_icon, const QString &summary,
                const QString &body, const QStringList &actions, const QVariantMap &hints, int expire_timeout);
    void CloseNotification(uint id);
    QString GetServerInformation(QString &vendor, QString &version, QString &spec_version);

Q_SIGNALS:
    void NotificationClosed(uint id, uint reason);
    void ActionInvoked(uint id, const QString &action_key);

private:
    NotificationServer *m_server;
};
