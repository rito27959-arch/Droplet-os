// Menu row, macOS 27 kit: 24 pt rows, text inset 12, hover platter of radius 8 that runs 7 pt
// past the text column (inset 5 from the menu edge), separator block 11 pt with a 1 pt line
import QtQuick
import Droplet

Item {
    id: it
    property string text
    property string shortcut
    property bool separator: false
    property bool enabled_: true
    property bool destructive: false
    signal triggered()
    // macOS confirms a chosen item by blinking its highlight once before the menu fades
    property bool _blink: false
    property bool _chosen: false
    width: parent ? parent.width : 220
    height: separator ? 11 : 24

    Rectangle {
        visible: it.separator
        anchors.verticalCenter: parent.verticalCenter
        x: 11; width: parent.width - 22; height: 1
        color: Theme.separateur
    }
    Rectangle {
        id: hl
        visible: !it.separator
        anchors.fill: parent
        anchors.leftMargin: 5; anchors.rightMargin: 5
        radius: Theme.rayonSelection
        color: Theme.elementSurvol
        // hover follows the pointer instantly, as in macOS menus (no fade)
        opacity: it._chosen ? (it._blink ? 0 : 1) : (ma.containsMouse && it.enabled_ ? 1 : 0)
    }
    Text {
        visible: !it.separator
        anchors.verticalCenter: parent.verticalCenter
        x: 12
        text: it.text
        font.family: Theme.texte; font.pixelSize: 13; font.letterSpacing: Theme.tracking(13)
        color: !it.enabled_ ? Theme.labelInactif : it.destructive ? Theme.erreur : Theme.label
    }
    Text {
        visible: !it.separator && it.shortcut.length > 0
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right; anchors.rightMargin: 12
        text: it.shortcut
        font.family: Theme.texte; font.pixelSize: 13; font.letterSpacing: Theme.tracking(13)
        color: Theme.label2
    }
    SequentialAnimation {
        id: blink
        PropertyAction { target: it; property: "_blink"; value: true }
        PauseAnimation { duration: 70 }
        PropertyAction { target: it; property: "_blink"; value: false }
        PauseAnimation { duration: 70 }
        ScriptAction { script: { Shell.CloseAll(); it.triggered(); it._chosen = false } }
    }
    MouseArea {
        id: ma
        anchors.fill: parent
        enabled: !it.separator
        hoverEnabled: true
        onClicked: if (it.enabled_ && !it._chosen) { it._chosen = true; blink.start() }
    }
}
