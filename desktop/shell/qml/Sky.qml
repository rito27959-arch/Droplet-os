// The day sky, alive: clouds drift with the wind and slowly billow, flocks of birds cross it.
// Performance rules (software rendering included):
//  * its own layer-shell surface covering only the band of sky (not the whole screen), so the
//    compositor only re-composites that band, and the static wallpaper is never repainted;
//  * a fixed, low tick rate (12 Hz) instead of a 60 Hz animation: clouds move a few points per
//    second, birds flap at 3 Hz — 12 Hz is smooth for both;
//  * birds are pre-rendered sprites (12 wing poses), moved and swapped, never painted;
//  * it stops completely when it cannot be seen: night, transition film, maximised or
//    full-screen window, or when "Réduire les animations" is on.
import QtQuick
import QtQuick.Window
import org.kde.layershell as LayerShell
import Droplet

Window {
    id: sky
    property bool wanted: false          // day still shown (from Wallpaper)
    property bool covered: false         // a maximised / full-screen window hides the desktop
    readonly property bool running: wanted && !covered && !SystemControl.reduceMotion
    readonly property string base: Shell.dataDir + "/wallpapers/jour/"
    readonly property int band: 460      // design points: the clouds and the birds live up there
    // same picture geometry as the wallpaper (16:10, cropped to cover the screen)
    readonly property real s: Math.max(Screen.width / 1440, Screen.height / 900)
    readonly property real offX: (Screen.width - 1440 * s) / 2
    readonly property real offY: (Screen.height - 900 * s) / 2

    visible: wanted
    color: "transparent"
    height: Math.ceil(band * s + offY)
    LayerShell.Window.scope: "droplet-sky"
    LayerShell.Window.layer: LayerShell.Window.LayerBackground   // above the wallpaper (mapped after it), under the widgets
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone
    // purely decorative: clicks go through to the desktop below
    onVisibleChanged: if (visible) Effects.input(sky, [Qt.rect(-2, -2, 1, 1)])

    property real t: 0                   // seconds of sky time (only advances while running)
    property double last: 0
    Timer {
        interval: 83; repeat: true; running: sky.running
        onRunningChanged: sky.last = 0
        onTriggered: {
            const now = Date.now()
            if (sky.last > 0) sky.t += Math.min(0.5, (now - sky.last) / 1000)
            sky.last = now
        }
    }

    Item {
        id: stage
        width: 1440; height: sky.band
        x: sky.offX; y: sky.offY
        transformOrigin: Item.TopLeft
        scale: sky.s

        Repeater {
            model: clouds.items
            delegate: Item {
                required property var modelData
                required property int index
                readonly property real span: 1440 + 2 * modelData.halfWidth + 200
                readonly property real cx: ((modelData.centre + modelData.speed * sky.t + modelData.halfWidth + 100) % span)
                                           - modelData.halfWidth - 100
                x: Math.round((modelData.x + (cx - modelData.centre)) * 2) / 2
                y: modelData.y
                width: modelData.width; height: modelData.height
                // three moments of the cloud, cross-faded: its shape billows slowly
                readonly property real ph: ((sky.t / 75) + index * .37) % 1
                Repeater {
                    model: ["a", "b", "c"]
                    Image {
                        required property string modelData
                        required property int index
                        anchors.fill: parent
                        source: sky.base + "nuage-" + parent.index + "-" + modelData + ".png"
                        asynchronous: true
                        readonly property real w: {
                            const d = Math.abs(((parent.ph * 3 - index) % 3 + 3) % 3)
                            return Math.max(0, 1 - Math.min(d, 3 - d))
                        }
                        opacity: w
                        visible: w > 0.003
                    }
                }
            }
        }

        // birds: two flocks; each enters beyond the left edge, leaves beyond the right edge, rests
        Repeater {
            model: [
                {alt: 232, dist: .25, speed: 58, n: 5, t0: 0, rest: 6},
                {alt: 150, dist: .7, speed: 36, n: 3, t0: 9, rest: 10}]
            delegate: Item {
                id: flock
                required property var modelData
                readonly property real flight: (1440 + 360) / modelData.speed
                readonly property real period: flight + modelData.rest
                readonly property real tt: ((sky.t - modelData.t0) % period + period) % period
                readonly property bool flying: tt <= flight
                readonly property real sc: 1 - .45 * modelData.dist
                readonly property real lead: -180 + tt * modelData.speed
                readonly property real by: modelData.alt + 22 * Math.sin(tt * .25) - tt * 1.2
                visible: flying
                Repeater {
                    model: flock.modelData.n
                    Image {
                        required property int index
                        readonly property var m: [[0, 0, 12, 0], [30, 15, 10, .31], [56, -5, 8.5, .62],
                                                  [82, 20, 9, .17], [-28, 23, 7.5, .85]][index]
                        readonly property real sz: m[2] * flock.sc
                        readonly property real cyc: (flock.tt * .22 + m[3]) % 1
                        readonly property real flap: {
                            let f = cyc < .65 ? 1 : Math.max(0, Math.min(1, (.8 - cyc) / .15))
                            return f * f * (3 - 2 * f)
                        }
                        readonly property real wing: Math.sin(2 * Math.PI * 3 * flock.tt + m[3] * 6.28) * flap + (1 - flap) * .25
                        // sprite: 30 x 30 pt drawn for a 12 pt half-span, centred on the body
                        width: 30 * sz / 12; height: width
                        x: flock.lead - m[0] * 1.1 * flock.sc - width / 2
                        y: flock.by + m[1] * flock.sc + 4 * flock.sc * Math.sin(flock.tt * 1.1 + index) - height / 2
                        rotation: Math.sin(flock.tt * .5 + index) * 4
                        source: sky.base + "oiseau-" + (flock.modelData.dist > .5 ? "far" : "near") + "-"
                                + Math.max(0, Math.min(11, Math.round((wing + 1) / 2 * 11))) + ".png"
                        smooth: true
                    }
                }
            }
        }
    }

    QtObject {
        id: clouds
        property var items: []
        Component.onCompleted: {
            try { items = JSON.parse(Shell.readText(sky.base + "nuages.json")).clouds } catch (e) { items = [] }
        }
    }
}
