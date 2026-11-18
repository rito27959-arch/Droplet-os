// Living wallpaper (layer-shell "background"): the still picture and the transition films.
// It never animates on its own (no repaint, no compositor damage); the moving sky of the day
// (clouds, birds) lives on its own small surface, Sky.qml.
//  Day   : the garden.
//  Night : the eclipse and the eight planets; the body changes every hour, always through the eclipse.
//  Switching appearance plays the drawn transition (the artist draws the garden / night falls).
// Assets: share/droplet/wallpapers (rendered by aura/render/export_wallpapers.py).
import QtQuick
import QtQuick.Window
import QtMultimedia
import org.kde.layershell as LayerShell
import Droplet

Window {
    id: win
    color: "#05070c"
    visible: true
    LayerShell.Window.scope: "droplet-wallpaper"
    LayerShell.Window.layer: LayerShell.Window.LayerBackground
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorBottom
                               | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: -1
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone

    readonly property string base: Shell.dataDir + "/wallpapers/"
    readonly property var bodies: ["eclipse", "mercure", "venus", "terre", "mars", "jupiter", "saturne", "uranus", "neptune"]
    // the same rule on the login screen: one body per hour, in order
    function bodyForNow() { return bodies[Math.floor(Date.now() / 3600000) % bodies.length] }

    property bool day: !SystemControl.darkMode
    property string body: bodyForNow()
    property string shown: day ? "jour" : body          // what the still layer shows
    property var queue: []                              // [{video, end}] steps still to play
    property bool playing: false

    function stillFor(name) { return name === "jour" ? base + "jour/fond.jpg" : base + "nuit/" + name + ".jpg" }

    function enqueue(steps) {
        queue = queue.concat(steps)
        if (!playing) next()
    }
    function next() {
        if (queue.length === 0) { playing = false; return }
        const step = queue[0]
        queue = queue.slice(1)
        playing = true
        player.endState = step.end
        player.source = base + step.video
        player.play()
    }

    onDayChanged: {
        if (day) {
            const steps = []
            if (body !== "eclipse") steps.push({video: "nuit/" + body + "-sortie.mp4", end: "eclipse"})
            steps.push({video: "transition/nuit-jour.mp4", end: "jour"})
            enqueue(steps)
        } else {
            const steps = [{video: "transition/jour-nuit.mp4", end: "eclipse"}]
            if (body !== "eclipse") steps.push({video: "nuit/" + body + "-entree.mp4", end: body})
            enqueue(steps)
        }
    }
    Timer {   // hourly: the next body of the night cycle
        interval: 60000; running: true; repeat: true
        onTriggered: {
            const b = win.bodyForNow()
            if (b === win.body) return
            const prev = win.body
            win.body = b
            if (win.day) return
            const steps = []
            if (prev !== "eclipse") steps.push({video: "nuit/" + prev + "-sortie.mp4", end: "eclipse"})
            if (b !== "eclipse") steps.push({video: "nuit/" + b + "-entree.mp4", end: b})
            win.enqueue(steps)
        }
    }

    // the picture is 16:10; it covers the screen and the sky items follow it (design units 1440 x 900)
    readonly property real s: Math.max(width / 1440, height / 900)
    // the sky surface animates only while the still garden is shown (not during a film)
    readonly property bool skyVisible: shown === "jour" && !player.covering

    Image {
        id: still
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        source: win.stillFor(win.shown)
        sourceSize: Qt.size(1920, 1200)
        asynchronous: false
        cache: true
    }

    // ---- transitions: pre-rendered films, played over the still layer
    MediaPlayer {
        id: player
        property string endState
        property bool covering: false     // a frame of the film is on screen
        videoOutput: video
        onMediaStatusChanged: {
            if (mediaStatus === MediaPlayer.BufferedMedia || mediaStatus === MediaPlayer.BufferingMedia) covering = true
            if (mediaStatus === MediaPlayer.EndOfMedia || mediaStatus === MediaPlayer.InvalidMedia) {
                win.shown = endState         // the still now shows the film's last picture
                hideTimer.restart()
            }
        }
        onErrorOccurred: { win.shown = endState; covering = false; win.next() }
    }
    Timer { id: hideTimer; interval: 120; onTriggered: { player.covering = false; win.next() } }
    VideoOutput {
        id: video
        anchors.fill: parent
        fillMode: VideoOutput.PreserveAspectCrop
        visible: player.covering
    }

    // a click on the desktop closes whatever is open
    MouseArea { anchors.fill: parent; onClicked: Shell.CloseAll() }
}
