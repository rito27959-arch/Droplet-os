// Liquid Glass surface.
// With the Droplet KWin effect (Effects.compositorGlass) the compositor draws the real glass behind
// the region we declare (lens, dispersion, frost, light, shadow): here we only add an optional
// legibility veil. Without it (software compositing, other compositors) QML draws a fallback:
// tint + specular rim lit from the top-left + soft shadow.
import QtQuick
import QtQuick.Effects
import Droplet

Item {
    id: glass
    property real radius: Theme.rayonMenu
    property color tint: Theme.verreMenu
    property bool shadow: true
    property real shadowOpacity: 0.42
    property real shadowSize: 44
    property real shadowOffset: 14
    property real rim: Theme.dark ? 0.55 : 0.9
    // extra tint on top of the compositor glass for text-heavy surfaces (menus, notifications)
    property real veil: 0
    readonly property bool native_: Effects.compositorGlass
    default property alias content: inner.data

    RectangularShadow {
        visible: glass.shadow && !glass.native_
        anchors.fill: parent
        anchors.topMargin: glass.shadowOffset
        anchors.bottomMargin: -glass.shadowOffset * 0.4
        radius: glass.radius
        blur: glass.shadowSize
        spread: -glass.shadowSize * 0.25
        color: Qt.rgba(0, 0, 0, glass.shadowOpacity)
    }

    Rectangle {
        anchors.fill: parent
        radius: glass.radius
        color: glass.tint
        opacity: glass.native_ ? glass.veil : 1
        visible: opacity > 0
        // hairline that separates the glass from what is behind it
        border.width: glass.native_ ? 0 : 0.5
        border.color: Theme.lisereExterne
    }

    // specular rim: bright at the top-left, fading along the edge
    Canvas {
        id: rimCanvas
        anchors.fill: parent
        visible: !glass.native_
        antialiasing: true
        renderStrategy: Canvas.Cooperative
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        Connections { target: Theme; function onDarkChanged() { rimCanvas.requestPaint() } }
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const w = width, h = height, r = Math.min(glass.radius, w / 2, h / 2), i = 0.75
            const g = ctx.createLinearGradient(0, 0, w * 0.55, h)
            g.addColorStop(0.0, Qt.rgba(1, 1, 1, glass.rim))
            g.addColorStop(0.35, Qt.rgba(1, 1, 1, glass.rim * 0.22))
            g.addColorStop(0.7, Qt.rgba(1, 1, 1, glass.rim * 0.08))
            g.addColorStop(1.0, Qt.rgba(1, 1, 1, glass.rim * 0.30))
            ctx.strokeStyle = g
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(i + r, i)
            ctx.lineTo(w - i - r, i); ctx.arcTo(w - i, i, w - i, i + r, r)
            ctx.lineTo(w - i, h - i - r); ctx.arcTo(w - i, h - i, w - i - r, h - i, r)
            ctx.lineTo(i + r, h - i); ctx.arcTo(i, h - i, i, h - i - r, r)
            ctx.lineTo(i, i + r); ctx.arcTo(i, i, i + r, i, r)
            ctx.closePath()
            ctx.stroke()
        }
    }

    Item { id: inner; anchors.fill: parent }
}
