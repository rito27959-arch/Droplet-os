#include "apps.h"

#include <KApplicationTrader>
#include <KIO/ApplicationLauncherJob>
#include <QFile>
#include <QIcon>
#include <algorithm>

namespace {
constexpr auto kIconDir = "/usr/share/droplet/icons/";

const QHash<QString, QString> &dropletIcons()
{
    static const QHash<QString, QString> map{
        {QStringLiteral("org.kde.dolphin"), QStringLiteral("fichiers")},
        {QStringLiteral("org.kde.konsole"), QStringLiteral("terminal")},
        {QStringLiteral("systemsettings"), QStringLiteral("reglages")},
        {QStringLiteral("org.kde.kate"), QStringLiteral("editeur")},
        {QStringLiteral("org.kde.spectacle"), QStringLiteral("capture")},
        {QStringLiteral("org.kde.falkon"), QStringLiteral("navigateur")},
        {QStringLiteral("org.kde.gwenview"), QStringLiteral("photos")},
        {QStringLiteral("org.kde.elisa"), QStringLiteral("musique")},
        {QStringLiteral("droplet-about"), QStringLiteral("assistant")},
    };
    return map;
}
} // namespace

QString dropletIconFor(const QString &desktopId, const QString &themeIcon)
{
    QString id = desktopId;
    id.remove(QStringLiteral(".desktop"));
    const auto it = dropletIcons().constFind(id);
    if (it != dropletIcons().cend()) {
        const QByteArray env = qgetenv("DROPLET_DATA_DIR");
        const QString dir = env.isEmpty() ? QString::fromLatin1(kIconDir) : QString::fromLocal8Bit(env) + QStringLiteral("/icons/");
        const QString path = dir + *it + QStringLiteral(".png");
        if (QFile::exists(path))
            return QStringLiteral("file://") + path;
    }
    return QStringLiteral("image://icon/") + themeIcon;
}

AppsModel::AppsModel(QObject *parent)
    : QAbstractListModel(parent)
{
    m_all = KApplicationTrader::query([](const KService::Ptr &s) {
        return !s->noDisplay() && s->isApplication() && !s->exec().isEmpty();
    });
    std::ranges::sort(m_all, [](const KService::Ptr &a, const KService::Ptr &b) {
        return QString::localeAwareCompare(a->name(), b->name()) < 0;
    });
    refilter();
}

int AppsModel::rowCount(const QModelIndex &parent) const
{
    return parent.isValid() ? 0 : int(m_shown.size());
}

QVariant AppsModel::data(const QModelIndex &index, int role) const
{
    if (!index.isValid() || index.row() >= m_shown.size())
        return {};
    const KService::Ptr &s = m_shown.at(index.row());
    switch (role) {
    case NameRole: return s->name();
    case IconRole: return dropletIconFor(s->desktopEntryName(), s->icon());
    case StorageIdRole: return s->storageId();
    case CommentRole: return s->genericName().isEmpty() ? s->comment() : s->genericName();
    }
    return {};
}

QHash<int, QByteArray> AppsModel::roleNames() const
{
    return {{NameRole, "name"}, {IconRole, "iconSource"}, {StorageIdRole, "storageId"}, {CommentRole, "comment"}};
}

void AppsModel::setQuery(const QString &q)
{
    if (q == m_query)
        return;
    m_query = q;
    refilter();
    Q_EMIT queryChanged();
}

void AppsModel::refilter()
{
    beginResetModel();
    m_shown.clear();
    const QString q = m_query.trimmed();
    if (q.isEmpty()) {
        m_shown = m_all;
    } else {
        // name prefix first, then name contains, then keywords / generic name
        QList<KService::Ptr> prefix, contains, other;
        for (const auto &s : m_all) {
            if (s->name().startsWith(q, Qt::CaseInsensitive)) prefix << s;
            else if (s->name().contains(q, Qt::CaseInsensitive)) contains << s;
            else if (s->genericName().contains(q, Qt::CaseInsensitive)
                     || s->keywords().join(u' ').contains(q, Qt::CaseInsensitive)) other << s;
        }
        m_shown = prefix + contains + other;
    }
    endResetModel();
    Q_EMIT countChanged();
}

bool AppsModel::launch(int row)
{
    if (row < 0 || row >= m_shown.size())
        return false;
    return launchId(m_shown.at(row)->storageId());
}

bool AppsModel::launchId(const QString &storageId)
{
    const KService::Ptr s = KService::serviceByStorageId(storageId);
    if (!s)
        return false;
    auto *job = new KIO::ApplicationLauncherJob(s);
    job->start();
    return true;
}

QString AppsModel::iconForDesktopId(const QString &desktopId)
{
    const KService::Ptr s = KService::serviceByDesktopName(QString(desktopId).remove(QStringLiteral(".desktop")));
    // not an application id: treat it as an icon-theme name (e.g. "dialog-information")
    return dropletIconFor(desktopId, s ? s->icon() : QString(desktopId));
}

ThemeIconProvider::ThemeIconProvider()
    : QQuickImageProvider(QQuickImageProvider::Pixmap)
{
}

QPixmap ThemeIconProvider::requestPixmap(const QString &id, QSize *size, const QSize &requestedSize)
{
    const QSize s = requestedSize.isValid() ? requestedSize : QSize(64, 64);
    const QIcon icon = QIcon::fromTheme(id, QIcon::fromTheme(QStringLiteral("application-x-executable")));
    QPixmap pm = icon.pixmap(s);
    if (size)
        *size = pm.size();
    return pm;
}
