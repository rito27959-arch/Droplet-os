// Droplet Shell — root: one layer-shell surface per role.
import QtQuick
import QtQuick.Window
import org.kde.layershell as LayerShell
import org.kde.taskmanager as TaskManager
import Droplet

QtObject {
    id: root

    property TaskManager.TasksModel tasks: TaskManager.TasksModel {
        groupMode: TaskManager.TasksModel.GroupApplications
        sortMode: TaskManager.TasksModel.SortManual
        separateLaunchers: false
        launchInPlace: true
        filterByVirtualDesktop: false
        filterByActivity: false
        filterByScreen: false
        launcherList: Shell.launchers(["org.kde.dolphin.desktop", "org.kde.konsole.desktop", "org.kde.kate.desktop",
                                       "systemsettings.desktop", "org.kde.spectacle.desktop"])
    }

    // name of the focused application, for the menu bar
    property int _rev: 0
    property Connections _watch: Connections {
        target: root.tasks
        function onActiveTaskChanged() { root._rev++ }
        function onDataChanged() { root._rev++ }
        function onRowsRemoved() { root._rev++ }
    }
    // a maximised or full-screen window hides the desktop: the sky can rest
    readonly property bool desktopCovered: {
        _rev
        const i = tasks.activeTask
        return !!(i && i.valid && (tasks.data(i, TaskManager.AbstractTasksModel.IsMaximized)
                                   || tasks.data(i, TaskManager.AbstractTasksModel.IsFullScreen)))
    }
    // system status is read often only while the Control Centre shows it
    property Binding _poll: Binding { target: SystemControl; property: "fastPoll"; value: Shell.controlCenterOpen }
    readonly property string appName: {
        _rev
        const i = tasks.activeTask
        return i && i.valid ? (tasks.data(i, TaskManager.AbstractTasksModel.AppName) || "") : ""
    }

    property Window wallpaper: Wallpaper {}
    // created before the widgets: same layer, so the widgets stay above the sky
    property Window sky: Sky { wanted: root.wallpaper.skyVisible; covered: root.desktopCovered }
    property Window widgets: Widgets {}
    property Window dock: Dock { tasks: root.tasks }
    property Window menubar: MenuBar { tasks: root.tasks; appName: root.appName }
    property Window notifications: Notifications {}

    // ---- popups: one transparent overlay under the menu bar; a click outside closes
    property Window overlay: Window {
        id: ov
        property string confirmAction: ""
        readonly property bool wanted: Shell.openMenu !== "" || Shell.launcherOpen || Shell.controlCenterOpen
                                       || Shell.aboutOpen || confirmAction !== ""
        visible: wanted || dmenu.opacity > 0 || amenu.opacity > 0 || cc.opacity > 0 || launcher.opacity > 0
                 || about.opacity > 0 || confirm.opacity > 0
        color: "transparent"
        LayerShell.Window.scope: "droplet-overlay"
        LayerShell.Window.layer: LayerShell.Window.LayerOverlay
        LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorBottom
                                   | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
        LayerShell.Window.margins.top: Theme.barreMenus
        LayerShell.Window.exclusionZone: -1
        // only the search field takes the keyboard; menus leave the focused app focused
        LayerShell.Window.keyboardInteractivity: Shell.launcherOpen || ov.confirmAction !== ""
                                                 ? LayerShell.Window.KeyboardInteractivityExclusive
                                                                    : LayerShell.Window.KeyboardInteractivityNone

        // The glass follows each popup frame by frame while it springs open (scaled geometry), and
        // leaves the region as soon as the popup starts closing: the compositor then dissolves it
        // with the same timing as the content fades (Theme "sortie").
        function updateRegions() {
            const r = []
            const add = (it, rad) => {
                if (!it.shown) return
                const q = it.mapToItem(ov.contentItem, 0, 0, it.width, it.height)
                r.push({x: q.x, y: q.y, width: q.width, height: q.height, radius: rad * q.width / Math.max(1, it.width)})
            }
            add(dmenu, Theme.rayonMenu); add(amenu, Theme.rayonMenu)
            if (cc.shown) for (const s of c1.shapes(ov.contentItem)) r.push(s)
            add(confirm, 34)   // About is an opaque window: no glass
            if (launcher.shown) {
                const q = launcher.mapToItem(ov.contentItem, 0, 0, launcher.width, launcher.height)
                const k = q.width / Math.max(1, launcher.width)
                r.push({x: q.x, y: q.y, width: q.width, height: 54 * k, radius: 27 * k})
                if (launcher.resultsHeight > 0)
                    r.push({x: q.x, y: q.y + 64 * k, width: q.width, height: launcher.resultsHeight * k, radius: 22 * k})
            }
            Effects.glass(ov, r, 12)
        }
        onVisibleChanged: if (visible) Qt.callLater(updateRegions)
        onWantedChanged: if (!wanted) confirmAction = ""

        Connections {
            target: Shell
            function onLauncherOpenChanged() { if (Shell.launcherOpen) Qt.callLater(launcher.open) }
        }

        Item {
            anchors.fill: parent
            focus: true
            Keys.onEscapePressed: { ov.confirmAction = ""; Shell.CloseAll() }
            MouseArea { anchors.fill: parent; onClicked: { ov.confirmAction = ""; Shell.CloseAll() } }

            // Popovers open with the "rebond" spring (scale from `depart`, fade with "vif") from the
            // point they belong to, and leave with "sortie": faster than they came.
            component Pop: Item {
                id: pop
                property bool shown: false
                property real depart: 0.93
                opacity: 0
                scale: depart
                visible: opacity > 0
                transformOrigin: Item.Top
                onShownChanged: {
                    fade.stop(); grow.stop()
                    fade.caractere = shown ? "vif" : "sortie"; fade.to = shown ? 1 : 0
                    grow.caractere = shown ? "rebond" : "sortie"; grow.to = shown ? 1 : (1 + depart) / 2
                    if (shown && opacity === 0) scale = depart
                    fade.start(); grow.start()
                    if (Window.window) Qt.callLater(Window.window.updateRegions)
                }
                Ressort { id: fade; target: pop; property: "opacity"; mouvement: false }
                Ressort { id: grow; target: pop; property: "scale" }
                onScaleChanged: if (shown && Window.window) Qt.callLater(Window.window.updateRegions)
                onHeightChanged: if (shown && Window.window) Qt.callLater(Window.window.updateRegions)
                onWidthChanged: if (shown && Window.window) Qt.callLater(Window.window.updateRegions)
                MouseArea { anchors.fill: parent }   // clicks inside a popup do not close it
            }

            Pop {
                id: dmenu
                shown: Shell.openMenu === "droplet"
                depart: 0.97; transformOrigin: Item.TopLeft
                x: root.menubar.dropletMenuX; y: 3
                width: m1.width; height: m1.height
                DropletMenu { id: m1; onConfirm: (a) => { Shell.CloseAll(); ov.confirmAction = a } }
            }
            Pop {
                id: amenu
                shown: Shell.openMenu === "app"
                depart: 0.97; transformOrigin: Item.TopLeft
                x: root.menubar.appMenuX; y: 3
                width: m2.width; height: m2.height
                AppMenu { id: m2; tasks: root.tasks; appName: root.appName }
            }
            Pop {
                id: cc
                shown: Shell.controlCenterOpen
                transformOrigin: Item.TopRight
                x: ov.width - width - 8; y: 6
                width: c1.width; height: c1.height
                ControlCenter { id: c1 }
            }
            Pop {
                id: launcher
                shown: Shell.launcherOpen
                depart: 0.94; transformOrigin: Item.Center
                readonly property real resultsHeight: l1.height > 64 ? l1.height - 64 : 0
                x: (ov.width - width) / 2; y: Math.round(ov.height * 0.16)
                width: l1.width; height: l1.height
                function open() { l1.open() }
                Launcher { id: l1 }
            }
            Pop {
                id: about
                shown: Shell.aboutOpen
                depart: 0.9
                transformOrigin: Item.Center
                x: (ov.width - width) / 2; y: Math.round(ov.height * 0.2)
                width: a1.width; height: a1.height
                About { id: a1 }
            }
            Pop {
                id: confirm
                shown: ov.confirmAction !== ""
                depart: 0.9
                transformOrigin: Item.Center
                x: (ov.width - width) / 2; y: Math.round(ov.height * 0.24)
                width: 260; height: d1.height
                readonly property var texts: ({
                    "reboot": ["Voulez-vous redémarrer l'ordinateur maintenant ?", "Redémarrer",
                               "Les apps ouvertes seront fermées."],
                    "poweroff": ["Voulez-vous éteindre l'ordinateur maintenant ?", "Éteindre",
                                 "Les apps ouvertes seront fermées."],
                    "logout": ["Voulez-vous fermer la session ?", "Fermer la session",
                               "Les apps ouvertes seront fermées."] })
                Alerte {
                    id: d1
                    width: parent.width
                    onVisibleChanged: if (visible) Qt.callLater(forceActiveFocus)
                    titre: confirm.texts[ov.confirmAction] ? confirm.texts[ov.confirmAction][0] : ""
                    message: confirm.texts[ov.confirmAction] ? confirm.texts[ov.confirmAction][2] : ""
                    boutons: [{ text: confirm.texts[ov.confirmAction] ? confirm.texts[ov.confirmAction][1] : "", role: "primaire" },
                              { text: "Annuler", role: "secondaire" }]
                    onChoisi: (i) => {
                        const a = ov.confirmAction
                        ov.confirmAction = ""
                        if (i !== 0) return
                        if (a === "reboot") SystemControl.reboot()
                        else if (a === "poweroff") SystemControl.powerOff()
                        else if (a === "logout") SystemControl.logout()
                    }
                }
            }
        }
    }
}
