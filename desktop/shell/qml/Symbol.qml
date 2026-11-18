// Phosphor pictogram (MIT), tinted. Source files are white SVGs in share/droplet/symbols.
import QtQuick
import QtQuick.Effects
import Droplet

Item {
    id: sym
    property string name
    property string weight: "regular"   // regular | fill | bold
    property color color: Theme.label
    property real size: 16
    implicitWidth: size
    implicitHeight: size

    Image {
        id: img
        anchors.fill: parent
        source: sym.name ? Theme.symbol(sym.weight === "regular" ? sym.name : sym.name + "-" + sym.weight) : ""
        sourceSize: Qt.size(sym.size * 2, sym.size * 2)
        smooth: true
        mipmap: true
        visible: false
    }
    MultiEffect {
        anchors.fill: parent
        source: img
        colorization: 1.0
        colorizationColor: Qt.rgba(sym.color.r, sym.color.g, sym.color.b, 1)
        brightness: 0
        opacity: sym.color.a
    }
}
