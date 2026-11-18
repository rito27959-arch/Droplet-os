// Dock — pinned apps (real .desktop launchers) + running windows, from the Plasma tasks model.
import QtQuick
import QtQuick.Window
import org.kde.layershell as LayerShell
import org.kde.taskmanager as TaskManager
import org.kde.kirigami as Kirigami
import QtQuick.Effects
import Droplet

Window {
    id: dock
    property var tasks
    readonly property int icon: Theme.iconeDock
    // macOS 27 kit (36 pt icons): padding 8 top/sides, gap 9, icon cell 36 + 3 + dot 4 + 4;
    // scaled by icon / 36 for Droplet's 52 pt icons
    readonly property real k: icon / 36
    readonly property int pad: Math.round(8 * k)
    readonly property int gap: Math.round(9 * k)
    readonly property int dotGap: Math.round(3 * k)
    readonly property int dotSize: 5
    readonly property int bottomPad: Math.round(4 * k)
    readonly property int bottomGap: 6
    readonly property int tooltipSpace: 44
    readonly property real barWidth: row.width + pad * 2
    readonly property real barHeight: pad + icon + dotGap + dotSize + bottomPad
    // items created after start-up (pinned or opened apps) grow into place; not the first ones
    property bool ready: false
    function pinned(appId) {
        if (!appId) return true
        const l = dock.tasks.launcherList
        for (let i = 0; i < l.length; ++i) if (String(l[i]).indexOf(appId) >= 0) return true
        return false
    }
    Timer { interval: 1500; running: true; onTriggered: dock.ready = true }

    width: Math.max(200, barWidth + 80)
    height: barHeight + bottomGap + tooltipSpace
    color: "transparent"
    visible: true
    LayerShell.Window.scope: "droplet-dock"
    LayerShell.Window.layer: LayerShell.Window.LayerTop
    LayerShell.Window.anchors: LayerShell.Window.AnchorBottom
    LayerShell.Window.exclusionZone: barHeight + bottomGap + 4
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone

    function updateRegions() {
        const r = Qt.rect(bar.x, bar.y, bar.width, bar.height)
        Effects.glass(dock, [r], Theme.rayonDock)
        Effects.input(dock, [Qt.rect(0, bar.y - 2, dock.width, dock.height - bar.y + 2)])
    }
    onWidthChanged: updateRegions()
    onHeightChanged: updateRegions()
    Component.onCompleted: updateRegions()

    Glass {
        id: bar
        width: dock.barWidth
        height: dock.barHeight
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: dock.bottomGap
        radius: Theme.rayonDock
        tint: Theme.verreDock
        shadowOpacity: 0.30; shadowSize: 30; shadowOffset: 10
        onWidthChanged: dock.updateRegions()
        Behavior on width { Ressort { caractere: "doux" } }

        Row {
            id: row
            x: dock.pad
            y: dock.pad
            spacing: dock.gap

            Repeater {
                model: dock.tasks
                delegate: DockItem {
                    id: dItem
                    required property var model
                    required property int index
                    readonly property var tm: dock.tasks   // kept: delayed calls may outlive the context
                    name: model.AppName || model.display || ""
                    appId: model.AppId || ""
                    decoration: model.decoration
                    running: !model.IsLauncher || model.IsStartup === true
                    active: model.IsActive === true
                    launched: !model.IsLauncher
                    // tell the compositor where this app lives: windows minimise into it (genie)
                    function publish() {
                        if (!dItem.tm || !dItem.Window.window || model.IsLauncher) return
                        // Wayland (plasma-window-management set_minimized_geometry): relative to
                        // the surface that holds the delegate, i.e. the Dock window
                        const p = dItem.mapToItem(null, 0, 0)
                        dItem.tm.requestPublishDelegateGeometry(dItem.tm.makeModelIndex(dItem.index),
                                                                Qt.rect(p.x, p.y, dItem.width, dItem.height), dItem)
                    }
                    onXChanged: Qt.callLater(publish)
                    onLaunchedChanged: Qt.callLater(publish)
                    Component.onCompleted: Qt.callLater(publish)
                    Connections { target: dock; function onWidthChanged() { Qt.callLater(publish) } }
                    onActivated: {
                        const idx = dock.tasks.makeModelIndex(index)
                        if (model.IsLauncher) {
                            bounce()
                            dock.tasks.requestActivate(idx)
                        } else if (model.IsGroupParent) {
                            dock.tasks.requestActivate(dock.tasks.makeModelIndex(index, 0))
                        } else if (model.IsActive) {
                            dock.tasks.requestToggleMinimized(idx)
                        } else {
                            dock.tasks.requestActivate(idx)
                        }
                    }
                }
            }

            Rectangle {   // divider before the trash, as on macOS
                width: 1; height: dock.icon - 8
                y: 4
                color: Theme.separateur
            }
            DockItem {
                name: "Corbeille"
                source: Theme.icon("corbeille")
                onActivated: Shell.openUrl("trash:/")
            }
        }
    }

    // Dock icon. Micro-interactions, all on the Droplet springs:
    //  * press: the icon darkens (macOS) and sinks slightly; release springs back
    //  * launch: bounces until the app's window appears (up ease-out, down ease-in, like gravity),
    //    then settles with a last small rebound; stops after 10 s if nothing comes
    //  * running dot fades and grows in; the name capsule rises 4 pt as it fades in
    //  * an app pinned or opened while the session runs grows into place
    component DockItem: Item {
        id: di
        property string name
        property string appId
        property var decoration
        property string source: appId ? Shell.iconFor(appId) : ""
        property bool running: false
        property bool active: false
        property bool launched: true
        property bool _bouncing: false
        signal activated()
        function bounce() { if (!SystemControl.reduceMotion) { _bouncing = true; giveUp.restart(); hop.restart() } }
        onLaunchedChanged: if (launched) _bouncing = false
        onRunningChanged: if (running && launched) _bouncing = false
        Timer { id: giveUp; interval: 10000; onTriggered: di._bouncing = false }
        width: Theme.iconeDock
        height: Theme.iconeDock
        scale: 1
        // only an app that was not already in the Dock grows in: a pinned launcher turning into its
        // running window (launch in place) keeps its spot without a flicker
        Component.onCompleted: if (dock.ready && !SystemControl.reduceMotion && !dock.pinned(appId)) { scale = 0.2; grow.start() }
        Ressort { id: grow; target: di; property: "scale"; to: 1; caractere: "rebond" }

        Item {
            id: art
            width: Theme.iconeDock; height: Theme.iconeDock
            transformOrigin: Item.Bottom
            Image {
                id: img
                anchors.fill: parent
                visible: di.source.startsWith("file:")
                source: visible ? di.source : ""
                sourceSize: Qt.size(Theme.iconeDock * 2, Theme.iconeDock * 2)
                smooth: true; mipmap: true
            }
            Kirigami.Icon {   // theme icon for apps without a Droplet icon
                anchors.fill: parent
                anchors.margins: 2
                visible: !img.visible
                source: di.decoration ? di.decoration : "application-x-executable"
            }
            // pressed: darken the icon itself (not its transparent corners)
            layer.enabled: press.enfoncement > 0.01
            layer.effect: MultiEffect { brightness: -0.32 * press.enfoncement }
        }
        // launch bounce: a ballistic hop, repeated while the app starts
        SequentialAnimation {
            id: hop
            NumberAnimation { target: art; property: "y"; to: -dock.icon * 0.42; duration: 270; easing.type: Easing.OutQuad }
            NumberAnimation { target: art; property: "y"; to: 0; duration: 270; easing.type: Easing.InQuad }
            onFinished: {
                if (di._bouncing) { hop.restart(); return }
                settle.restart()
            }
        }
        SequentialAnimation {
            id: settle      // a last, smaller hop as the app arrives
            NumberAnimation { target: art; property: "y"; to: -dock.icon * 0.08; duration: 120; easing.type: Easing.OutQuad }
            NumberAnimation { target: art; property: "y"; to: 0; duration: 120; easing.type: Easing.InQuad }
        }
        Rectangle {   // running dot
            id: dot
            width: dock.dotSize; height: dock.dotSize; radius: dock.dotSize / 2
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.top: parent.bottom; anchors.topMargin: dock.dotGap
            color: Theme.label
            opacity: di.running ? 0.6 : 0     // kit: #707070, Linear Dodge
            scale: di.running ? 1 : 0.3
            Behavior on opacity { Ressort { caractere: "fondu"; mouvement: false } }
            Behavior on scale { Ressort { caractere: "rebond" } }
        }
        // name capsule above the icon on hover
        Glass {
            id: tipBox
            readonly property bool wanted: press.containsMouse && !press.pressed && di.name.length > 0
            visible: opacity > 0
            opacity: wanted ? 1 : 0
            Behavior on opacity { Ressort { caractere: tipBox.wanted ? "vif" : "sortie"; mouvement: false } }
            width: tip.implicitWidth + 22; height: 26
            radius: 13
            tint: Theme.verreMenu
            veil: 1        // not a compositor-glass region: keep an opaque capsule
            shadowSize: 16; shadowOffset: 4; shadowOpacity: 0.3
            anchors.horizontalCenter: parent.horizontalCenter
            anchors.bottom: parent.top
            anchors.bottomMargin: wanted ? 14 : 10
            Behavior on anchors.bottomMargin { Ressort { caractere: "vif" } }
            Text {
                id: tip
                anchors.centerIn: parent
                text: di.name
                color: Theme.label
                font.family: Theme.texte; font.pixelSize: 13; font.letterSpacing: Theme.tracking(13)
            }
        }
        Pression {
            id: press
            anchors.fill: parent
            cible: art
            echelle: 0.94
            onClicked: di.activated()
        }
    }
}
