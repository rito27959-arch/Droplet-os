// Aura switch (Interrupteur), macOS 27 metrics: track 54 x 24, capsule knob 32 x 20.
// While held, the knob lifts into a larger, lighter liquid capsule (kit "Clicked": 40 x 28 here)
// and stretches toward where it will go; released, it springs across with "rebond".
import QtQuick
import Droplet

Item {
    id: t
    property bool checked: false
    property bool enabled_: true
    signal toggled(bool value)
    implicitWidth: 54; implicitHeight: 24
    opacity: enabled_ ? 1 : 0.4

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: t.checked ? Theme.goutte : Theme.element
        border.width: t.checked ? 0 : 0.5
        border.color: Theme.separateur
        Behavior on color { Teinte {} }
    }
    Rectangle {
        id: knob
        readonly property bool held: area.pressed
        width: held ? 40 : 32
        height: held ? 28 : 20
        radius: height / 2
        y: (t.height - height) / 2
        x: t.checked ? t.width - width - 2 : 2
        color: held ? Qt.rgba(1, 1, 1, 0.82) : "#ffffff"
        border.width: 0.5; border.color: held ? "#33ffffff" : "#1a000000"
        Behavior on x { Ressort { caractere: "rebond" } }
        Behavior on width { Ressort { caractere: knob.held ? "vif" : "rebond" } }
        Behavior on height { Ressort { caractere: knob.held ? "vif" : "rebond" } }
        Behavior on color { Teinte {} }
    }
    MouseArea {
        id: area
        anchors.fill: parent
        anchors.margins: -4
        enabled: t.enabled_
        cursorShape: Qt.PointingHandCursor
        onClicked: t.toggled(!t.checked)
    }
}
