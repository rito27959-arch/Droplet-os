// Aura slider (Curseur) as in Control Centre: thick track, pictogram inside, knob-less fill.
// Micro-interactions: the track swells a little while held (vif), a click glides the fill to the
// new value (doux) while a drag follows the finger exactly, and the pictogram bounces when the
// value leaves or reaches zero.
import QtQuick
import Droplet

Item {
    id: s
    property real value: 0      // 0..100
    property string symbol
    property bool available: true
    signal moved(real value)
    implicitHeight: 28
    opacity: available ? 1 : 0.4

    Item {
        id: body
        anchors.fill: parent
        transformOrigin: Item.Center
        scale: 1
        Rectangle {
            id: track
            anchors.fill: parent
            radius: height / 2
            color: Theme.element
            border.width: 0.5; border.color: Theme.separateur
            clip: true
            Rectangle {
                visible: s.available
                width: Math.max(track.height, track.width * s.value / 100)
                height: track.height
                radius: track.radius
                color: Theme.dark ? "#f5f5f7" : "#ffffff"
                Behavior on width { enabled: !drag.dragging; Ressort { caractere: "doux" } }
            }
        }
        Symbol {
            id: glyph
            anchors.verticalCenter: parent.verticalCenter
            x: 8
            size: 14
            name: s.symbol
            weight: "fill"
            color: "#8a8a90"
        }
    }
    onSymbolChanged: { bounce.stop(); glyph.scale = 0.7; bounce.start() }
    Ressort { id: bounce; target: glyph; property: "scale"; to: 1; caractere: "rebond" }

    // held: the whole control swells by 2 pt in height, like Tahoe's sliders
    states: State { when: drag.pressed; PropertyChanges { body.scale: 1 + 4 / Math.max(1, s.width) ; body.anchors.topMargin: -2; body.anchors.bottomMargin: -2 } }
    transitions: Transition { Ressort { properties: "scale,anchors.topMargin,anchors.bottomMargin"; caractere: drag.pressed ? "vif" : "rebond" } }

    MouseArea {
        id: drag
        anchors.fill: parent
        enabled: s.available
        property bool dragging: false
        property real pressX: 0
        function set(mx) { s.moved(Math.round(Math.max(0, Math.min(1, mx / width)) * 100)) }
        onPressed: (m) => { pressX = m.x; dragging = false; set(m.x) }
        onPositionChanged: (m) => { if (pressed) { if (Math.abs(m.x - pressX) > 3) dragging = true; set(m.x) } }
        onReleased: dragging = false
    }
}
