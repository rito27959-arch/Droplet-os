// The Droplet menu (eclipse logo): system actions only — each one is real.
import QtQuick
import Droplet

Glass {
    id: menu
    signal confirm(string action)
    width: 276
    height: col.implicitHeight + 10
    radius: Theme.rayonMenu
    tint: Theme.verreMenu
    veil: .15   // the kit menu is glass only; a light veil keeps 13 pt text crisp

    Column {
        id: col
        y: 5
        width: parent.width
        MenuItem { text: "À propos de cet ordinateur"; onTriggered: Shell.ShowAbout() }
        MenuItem { separator: true }
        MenuItem { text: "Réglages du système…"; onTriggered: SystemControl.openSettings() }
        MenuItem { text: "Rechercher une app…"; shortcut: "Super Espace"; onTriggered: Shell.ToggleLauncher() }
        MenuItem { separator: true }
        MenuItem { text: "Suspendre l'activité"; onTriggered: SystemControl.suspend() }
        MenuItem { text: "Redémarrer…"; onTriggered: menu.confirm("reboot") }
        MenuItem { text: "Éteindre…"; onTriggered: menu.confirm("poweroff") }
        MenuItem { separator: true }
        MenuItem { text: "Fermer la session…"; onTriggered: menu.confirm("logout") }
    }
}
