// Bouton — the macOS 27 push button, shared by every dialog of the shell.
// Kit (Buttons / Alerts): capsule, 28 pt in alerts (Large) or 24 pt (Medium, radius 6 then
// capsule from Large up), label Medium 13, horizontal padding 16.
//   role "primaire"   : accent fill, white label (the default action, Return)
//   role "destructif" : accent-red tint 23 % behind a red label
//   role "secondaire" : neutral fill (#E6E6E6 light, white 14 % dark), primary label
import QtQuick
import Droplet

Item {
    id: b
    property string text
    property string role: "secondaire"
    property bool grand: true              // 28 pt (alerts, sheets) — false: 24 pt
    property bool enabled_: true
    signal clicked()
    implicitWidth: Math.max(label.implicitWidth + 32, grand ? 80 : 64)
    implicitHeight: grand ? 28 : 24
    opacity: enabled_ ? 1 : 0.4

    Rectangle {
        id: bg
        anchors.fill: parent
        radius: b.grand ? height / 2 : Theme.rayonControle
        color: b.role === "primaire" ? Theme.goutteRemplie
               : b.role === "destructif" ? Qt.rgba(Theme.erreur.r, Theme.erreur.g, Theme.erreur.b, 0.23)
               : (Theme.dark ? "#24ffffff" : "#e6e6e6")
        Behavior on color { Teinte {} }
        // pressed: a darker veil (light) / lighter veil (dark), as on macOS
        Rectangle {
            anchors.fill: parent; radius: parent.radius
            color: Theme.dark || b.role === "primaire" ? "#ffffff" : "#000000"
            opacity: press.enfoncement * (b.role === "primaire" ? 0.16 : 0.10)
        }
    }
    Text {
        id: label
        anchors.centerIn: parent
        text: b.text
        color: b.role === "primaire" ? Theme.surAccent : b.role === "destructif" ? Theme.erreur : Theme.label
        font.family: Theme.texte; font.pixelSize: 13; font.weight: Font.Medium
        font.letterSpacing: Theme.tracking(13)
    }
    Pression { id: press; anchors.fill: parent; cible: b; echelle: 0.97; enabled: b.enabled_; onClicked: b.clicked() }
}
