// Alerte — the macOS 27 alert (kit "Alert", type Stacked): 260 pt wide Liquid Glass (Large,
// radius 34), padding 20 / 16, 14 pt between blocks; app icon 64 pt with a contact shadow;
// title Bold 13, message Regular 11, both centred in a 216 pt column; buttons stacked full
// width, 28 pt capsules 6 pt apart, the default action first.
import QtQuick
import Droplet

Glass {
    id: a
    property string icone: Theme.icon("assistant")
    property string titre
    property string message
    // [{text, role, action}] — role: primaire | destructif | secondaire
    property var boutons: []
    signal choisi(int index)
    width: 260
    height: col.implicitHeight + 36
    radius: 34
    tint: Theme.verreMenu
    veil: .15

    Column {
        id: col
        x: 16; y: 20
        width: parent.width - 32
        spacing: 14
        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            source: a.icone; width: 64; height: 64
            sourceSize: Qt.size(128, 128); smooth: true; mipmap: true
        }
        Column {
            x: 6; width: parent.width - 12
            spacing: 4
            Text {
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: a.titre
                color: Theme.label
                font.family: Theme.texte; font.pixelSize: 13; font.weight: Font.Bold
                font.letterSpacing: Theme.tracking(13)
            }
            Text {
                visible: text.length > 0
                width: parent.width
                horizontalAlignment: Text.AlignHCenter
                wrapMode: Text.Wrap
                text: a.message
                color: Theme.label
                font.family: Theme.texte; font.pixelSize: 11; font.letterSpacing: Theme.tracking(11)
            }
        }
        Column {
            width: parent.width
            spacing: 6
            Repeater {
                model: a.boutons
                Bouton {
                    required property var modelData
                    required property int index
                    width: parent.width
                    text: modelData.text
                    role: modelData.role || "secondaire"
                    onClicked: a.choisi(index)
                }
            }
        }
    }
    // Return triggers the default (first) action, Escape the last one (Cancel)
    Keys.onReturnPressed: if (boutons.length) choisi(0)
    Keys.onEscapePressed: if (boutons.length) choisi(boutons.length - 1)
}
