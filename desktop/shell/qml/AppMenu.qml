// Menu of the active application: window actions through the compositor (KWin tasks model).
import QtQuick
import org.kde.taskmanager as TaskManager
import Droplet

Glass {
    id: menu
    property var tasks
    property string appName
    readonly property bool hasWindow: tasks && tasks.activeTask && tasks.activeTask.valid
    width: 236
    height: col.implicitHeight + 10
    radius: Theme.rayonMenu
    tint: Theme.verreMenu
    veil: .15

    Column {
        id: col
        y: 5
        width: parent.width
        // with a window focused: act on it
        MenuItem { visible: menu.hasWindow; text: "Nouvelle fenêtre"
                   onTriggered: menu.tasks.requestNewInstance(menu.tasks.activeTask) }
        MenuItem { visible: menu.hasWindow; separator: true }
        MenuItem { visible: menu.hasWindow; text: "Réduire"
                   onTriggered: menu.tasks.requestToggleMinimized(menu.tasks.activeTask) }
        MenuItem { visible: menu.hasWindow; text: "Agrandir / restaurer"
                   onTriggered: menu.tasks.requestToggleMaximized(menu.tasks.activeTask) }
        MenuItem { visible: menu.hasWindow; text: "Plein écran"
                   onTriggered: menu.tasks.requestToggleFullScreen(menu.tasks.activeTask) }
        MenuItem { visible: menu.hasWindow; separator: true }
        MenuItem { visible: menu.hasWindow; text: "Fermer la fenêtre"
                   onTriggered: menu.tasks.requestClose(menu.tasks.activeTask) }
        // on the desktop
        MenuItem { visible: !menu.hasWindow; text: "Nouvelle fenêtre Fichiers"
                   onTriggered: Shell.launch("org.kde.dolphin.desktop") }
        MenuItem { visible: !menu.hasWindow; text: "Ouvrir le Terminal"
                   onTriggered: Shell.launch("org.kde.konsole.desktop") }
    }
}
