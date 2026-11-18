// Droplet Shell — installed applications (search + launch)
#pragma once

#include <QAbstractListModel>
#include <QQmlEngine>
#include <QQuickImageProvider>
#include <KService>

// Droplet's own icons for system apps; everything else uses the icon theme.
QString dropletIconFor(const QString &desktopId, const QString &themeIcon);

class AppsModel : public QAbstractListModel
{
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(QString query READ query WRITE setQuery NOTIFY queryChanged)
    Q_PROPERTY(int count READ rowCount NOTIFY countChanged)

public:
    enum Roles { NameRole = Qt::UserRole + 1, IconRole, StorageIdRole, CommentRole };

    explicit AppsModel(QObject *parent = nullptr);

    int rowCount(const QModelIndex &parent = {}) const override;
    QVariant data(const QModelIndex &index, int role) const override;
    QHash<int, QByteArray> roleNames() const override;

    QString query() const { return m_query; }
    void setQuery(const QString &q);

    Q_INVOKABLE bool launch(int row);
    Q_INVOKABLE static bool launchId(const QString &storageId);
    Q_INVOKABLE static QString iconForDesktopId(const QString &desktopId);

Q_SIGNALS:
    void queryChanged();
    void countChanged();

private:
    void refilter();
    QList<KService::Ptr> m_all;
    QList<KService::Ptr> m_shown;
    QString m_query;
};

class ThemeIconProvider : public QQuickImageProvider
{
public:
    ThemeIconProvider();
    QPixmap requestPixmap(const QString &id, QSize *size, const QSize &requestedSize) override;
};
