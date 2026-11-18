#include "effects.h"

#include <KWindowEffects>
#include <QQuickWindow>
#include <QRegion>
#include <QDebug>
#include <QVariantMap>
#include <QDBusConnection>
#include <QDBusMessage>
#include <QDBusPendingCallWatcher>
#include <QDBusPendingReply>
#include <QTimer>

namespace {
// A rounded rectangle as a QRegion: four corner discs + two crossing bands.
QRegion roundedRegion(const QRect &r, int radius)
{
    radius = std::min({radius, r.width() / 2, r.height() / 2});
    if (radius <= 0)
        return QRegion(r);
    const int d = 2 * radius;
    QRegion region(r.adjusted(radius, 0, -radius, 0));
    region += QRegion(r.adjusted(0, radius, 0, -radius));
    region += QRegion(QRect(r.left(), r.top(), d, d), QRegion::Ellipse);
    region += QRegion(QRect(r.right() - d + 1, r.top(), d, d), QRegion::Ellipse);
    region += QRegion(QRect(r.left(), r.bottom() - d + 1, d, d), QRegion::Ellipse);
    region += QRegion(QRect(r.right() - d + 1, r.bottom() - d + 1, d, d), QRegion::Ellipse);
    return region;
}
} // namespace

Effects::Effects(QObject *parent)
    : QObject(parent)
{
    // KWin may load its effects a moment after the shell starts: ask a few times
    for (int ms : {0, 1500, 5000, 15000})
        QTimer::singleShot(ms, this, &Effects::probe);
}

void Effects::probe()
{
    auto msg = QDBusMessage::createMethodCall(QStringLiteral("org.kde.KWin"), QStringLiteral("/Effects"),
                                              QStringLiteral("org.kde.kwin.Effects"), QStringLiteral("isEffectLoaded"));
    msg << QStringLiteral("dropletglass");
    auto *w = new QDBusPendingCallWatcher(QDBusConnection::sessionBus().asyncCall(msg), this);
    connect(w, &QDBusPendingCallWatcher::finished, this, [this, w] {
        QDBusPendingReply<bool> r = *w;
        const bool on = r.isValid() && r.value();
        if (on != m_compositorGlass) {
            m_compositorGlass = on;
            Q_EMIT compositorGlassChanged();
        }
        w->deleteLater();
    });
}

void Effects::glass(QQuickWindow *window, const QVariantList &rects, qreal radius)
{
    if (!window)
        return;
    QRegion region;
    for (const QVariant &v : rects) {
        // either a rect (uses `radius`) or {x, y, width, height, radius}
        if (v.typeId() == QMetaType::QVariantMap) {
            const QVariantMap m = v.toMap();
            const QRectF r(m.value(QStringLiteral("x")).toReal(), m.value(QStringLiteral("y")).toReal(),
                           m.value(QStringLiteral("width")).toReal(), m.value(QStringLiteral("height")).toReal());
            region += roundedRegion(r.toAlignedRect(), qRound(m.value(QStringLiteral("radius"), radius).toReal()));
        } else {
            region += roundedRegion(v.toRectF().toAlignedRect(), qRound(radius));
        }
    }
    if (region.isEmpty()) {
        // an empty blur region means "the whole surface" to the compositor: drop the glass instead
        // (the Droplet effect then lets the last shapes dissolve)
        clear(window);
        window->update();
        return;
    }
    if (qEnvironmentVariableIsSet("DROPLET_DEBUG_GLASS"))
        qWarning() << "glass" << window->objectName() << window->title() << region;
    KWindowEffects::enableBlurBehind(window, true, region);
    // contrast 1.0, intensity 1.0, saturation 1.8: the "vibrancy" of the Aura glass
    KWindowEffects::enableBackgroundContrast(window, true, 1.0, 1.0, 1.8, region);
    // the region is double-buffered state of the wl_surface: it only reaches the compositor with
    // the next commit. Render one more frame so it is committed even when nothing else changes.
    window->update();
}

void Effects::clear(QQuickWindow *window)
{
    if (!window)
        return;
    KWindowEffects::enableBlurBehind(window, false);
    KWindowEffects::enableBackgroundContrast(window, false);
}

void Effects::input(QQuickWindow *window, const QVariantList &rects)
{
    if (!window)
        return;
    QRegion region;
    for (const QVariant &v : rects)
        region += v.toRectF().toAlignedRect();
    window->setMask(region);   // QtWayland maps the mask to wl_surface.set_input_region
}
