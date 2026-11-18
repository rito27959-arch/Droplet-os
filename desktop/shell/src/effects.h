// Droplet Shell — compositor effects (KWin blur / contrast behind Liquid Glass surfaces)
#pragma once

#include <QObject>
#include <QQmlEngine>
#include <QRectF>

#include <QQuickWindow>

class Effects : public QObject
{
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON
    // true when KWin runs the Droplet Liquid Glass effect: it then draws the glass (lens, light,
    // shadow) behind our surfaces, and the QML only adds content. Otherwise QML draws a fallback.
    Q_PROPERTY(bool compositorGlass READ compositorGlass NOTIFY compositorGlassChanged)

public:
    explicit Effects(QObject *parent = nullptr);
    bool compositorGlass() const { return m_compositorGlass; }

Q_SIGNALS:
    void compositorGlassChanged();

public:
    // Ask KWin to blur (and saturate) what lies behind `rect` (window coordinates)
    // with rounded corners of `radius`. Several rects can be passed as a list.
    Q_INVOKABLE void glass(QQuickWindow *window, const QVariantList &rects, qreal radius);
    Q_INVOKABLE void clear(QQuickWindow *window);
    // Restrict pointer input to `rects` (transparent parts of the surface let clicks through).
    Q_INVOKABLE void input(QQuickWindow *window, const QVariantList &rects);

private:
    void probe();
    bool m_compositorGlass = false;
};
