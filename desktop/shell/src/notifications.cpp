#include "notifications.h"

#include <QDBusConnection>
#include <QDBusConnectionInterface>
#include <QLocale>
#include <QUrl>

#include "apps.h"

NotificationServer::NotificationServer(QObject *parent)
    : QAbstractListModel(parent)
{
    new NotificationsAdaptor(this);
    auto bus = QDBusConnection::sessionBus();
    if (bus.registerService(QStringLiteral("org.freedesktop.Notifications")))
        m_registered = bus.registerObject(QStringLiteral("/org/freedesktop/Notifications"), this);
}

int NotificationServer::rowCount(const QModelIndex &parent) const { return parent.isValid() ? 0 : int(m_items.size()); }

QVariant NotificationServer::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() >= m_items.size()) return {};
    const Notification &n = m_items.at(index.row());
    switch (role) {
    case IdRole: return n.id;
    case AppNameRole: return n.appName;
    case AppIconRole: return n.appIcon;
    case SummaryRole: return n.summary;
    case BodyRole: return n.body;
    case TimeRole: return n.time;
    case ActionsRole: return n.actions;
    }
    return {};
}

QHash<int, QByteArray> NotificationServer::roleNames() const
{
    return {{IdRole, "nid"}, {AppNameRole, "appName"}, {AppIconRole, "appIcon"}, {SummaryRole, "summary"},
            {BodyRole, "body"}, {TimeRole, "time"}, {ActionsRole, "actions"}};
}

void NotificationServer::setDoNotDisturb(bool on)
{
    if (on == m_dnd) return;
    m_dnd = on;
    Q_EMIT doNotDisturbChanged();
}

NotificationsAdaptor::NotificationsAdaptor(NotificationServer *server)
    : QDBusAbstractAdaptor(server)
    , m_server(server)
{
    connect(server, &NotificationServer::closed, this, &NotificationsAdaptor::NotificationClosed);
    connect(server, &NotificationServer::actionInvoked, this, &NotificationsAdaptor::ActionInvoked);
}

uint NotificationsAdaptor::Notify(const QString &app_name, uint replaces_id, const QString &app_icon, const QString &summary,
                                  const QString &body, const QStringList &actions, const QVariantMap &hints, int expire_timeout)
{
    return m_server->notify(app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout);
}

void NotificationsAdaptor::CloseNotification(uint id) { m_server->close(id); }

QStringList NotificationsAdaptor::GetCapabilities()
{
    return {QStringLiteral("body"), QStringLiteral("actions"), QStringLiteral("icon-static"), QStringLiteral("persistence")};
}

uint NotificationServer::notify(const QString &app_name, uint replaces_id, const QString &app_icon, const QString &summary,
                                const QString &body, const QStringList &actions, const QVariantMap &hints, int expire_timeout)
{
    Notification n;
    n.id = replaces_id ? replaces_id : m_next++;
    n.appName = app_name.isEmpty() ? QStringLiteral("Système") : app_name;
    // icon: explicit path/name, then the image hints (libnotify >= 0.8 sends -i as "image-path"),
    // then the sender's desktop entry
    QString icon = app_icon;
    for (const char *key : {"image-path", "image_path", "desktop-entry"})
        if (icon.isEmpty()) icon = hints.value(QString::fromLatin1(key)).toString();
    if (icon.startsWith(QStringLiteral("file://"))) icon = QUrl(icon).toLocalFile();
    if (icon.startsWith(u'/')) n.appIcon = QStringLiteral("file://") + icon;
    else if (!icon.isEmpty()) n.appIcon = AppsModel::iconForDesktopId(icon);
    else n.appIcon = QStringLiteral("image://icon/preferences-desktop-notification");
    n.summary = summary;
    n.body = body;
    n.actions = actions;
    n.time = QDateTime::currentDateTime();

    for (int i = 0; i < m_items.size(); ++i) {
        if (m_items[i].id == n.id) { m_items[i] = n; Q_EMIT dataChanged(index(i), index(i)); return n.id; }
    }
    if (m_dnd) return n.id;  // accepted silently: no banner while "Ne pas déranger" is on
    beginInsertRows({}, 0, 0);
    m_items.prepend(n);
    endInsertRows();
    Q_EMIT countChanged();
    const int timeout = expire_timeout > 0 ? expire_timeout : 5000;
    const uint id = n.id;
    QTimer::singleShot(timeout, this, [this, id] { remove(id, 1); });
    return n.id;
}

void NotificationServer::remove(uint id, uint reason)
{
    for (int i = 0; i < m_items.size(); ++i) {
        if (m_items[i].id == id) {
            beginRemoveRows({}, i, i);
            m_items.removeAt(i);
            endRemoveRows();
            Q_EMIT countChanged();
            Q_EMIT closed(id, reason);
            return;
        }
    }
}

void NotificationServer::close(uint id) { remove(id, 3); }
void NotificationServer::dismiss(uint id) { remove(id, 2); }

void NotificationServer::invoke(uint id, const QString &actionKey)
{
    Q_EMIT actionInvoked(id, actionKey);
    remove(id, 2);
}

QString NotificationsAdaptor::GetServerInformation(QString &vendor, QString &version, QString &spec_version)
{
    vendor = QStringLiteral("Droplet");
    version = QStringLiteral("0.2");
    spec_version = QStringLiteral("1.2");
    return QStringLiteral("Droplet Shell");
}
