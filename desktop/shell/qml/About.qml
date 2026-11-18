// "À propos de cet ordinateur" — real values read from /proc and os-release.
import QtQuick
import Droplet

Glass {
    id: about
    width: 300
    height: col.implicitHeight + 48
    radius: Theme.rayonDialogue
    tint: Theme.verreMenu
    veil: .15
    readonly property var info: SystemControl.about

    Column {
        id: col
        y: 30
        width: parent.width
        spacing: 0
        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            source: Theme.icon("assistant")
            width: 96; height: 96
            sourceSize: Qt.size(192, 192)
            smooth: true; mipmap: true
        }
        Item { width: 1; height: 16 }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Droplet OS"
            color: Theme.label
            font.family: Theme.titres; font.pixelSize: 26; font.weight: Font.Bold
            font.letterSpacing: Theme.tracking(26)
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Version " + (about.info.version || "0.2")
            color: Theme.label2
            font.family: Theme.texte; font.pixelSize: 12; font.letterSpacing: Theme.tracking(12)
        }
        Item { width: 1; height: 20 }
        Repeater {
            model: [["Nom", about.info.host], ["Processeur", about.info.cpu], ["Mémoire", about.info.memory],
                    ["Noyau", about.info.kernel]]
            delegate: Item {
                required property var modelData
                width: col.width; height: 20
                visible: !!modelData[1]
                Text {
                    anchors.right: parent.horizontalCenter; anchors.rightMargin: 5
                    text: modelData[0]
                    color: Theme.label
                    font.family: Theme.texte; font.pixelSize: 11; font.weight: Font.DemiBold
                    font.letterSpacing: Theme.tracking(11)
                }
                Text {
                    anchors.left: parent.horizontalCenter; anchors.leftMargin: 5
                    width: parent.width / 2 - 20
                    elide: Text.ElideRight
                    text: modelData[1] || ""
                    color: Theme.label2
                    font.family: Theme.texte; font.pixelSize: 11; font.letterSpacing: Theme.tracking(11)
                }
            }
        }
        Item { width: 1; height: 20 }
        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: moreText.implicitWidth + 28; height: 28; radius: 14
            color: moreMa.pressed ? Theme.elementSurvol : Theme.element
            border.width: 0.5; border.color: Theme.separateur
            Text {
                id: moreText
                anchors.centerIn: parent
                text: "Plus d'infos…"
                color: Theme.label
                font.family: Theme.texte; font.pixelSize: 13; font.letterSpacing: Theme.tracking(13)
            }
            Pression { id: moreMa; anchors.fill: parent; echelle: 0.95
                       onClicked: { Shell.CloseAll(); SystemControl.openSettings("kcm_about-distro") } }
        }
    }
    Rectangle {   // close button: the kit's traffic light (14 pt), glyph shown on hover
        id: closeLight
        x: 14; y: 14; width: 14; height: 14; radius: 7
        color: "#f06e6a"
        border.width: 0.5; border.color: "#33000000"
        Symbol { anchors.centerIn: parent; size: 8; weight: "bold"; name: "x"; color: "#4d0000"
                 opacity: closePress.containsMouse ? 1 : 0
                 Behavior on opacity { Ressort { caractere: "fondu"; mouvement: false } } }
        Pression { id: closePress; anchors.fill: parent; anchors.margins: -6; cible: closeLight; echelle: 0.88
                   onClicked: Shell.CloseAll() }
    }
}
