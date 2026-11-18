// Pression — press feedback shared by every clickable surface of the shell.
// Pressing sinks the target a little with the "vif" spring; releasing lets it spring back with
// "rebond", so a quick click reads as a soft tap. Use it as the item's MouseArea.
import QtQuick
import Droplet

MouseArea {
    id: m
    property Item cible: parent
    property real echelle: 0.96          // 0.96 tiles and buttons, 0.92 small icons
    property bool assombrir: false       // icons: darken while pressed (macOS Dock)
    readonly property real enfoncement: _enf
    property real _enf: 0
    hoverEnabled: true

    onPressedChanged: {
        anim.stop()
        anim.caractere = pressed ? "vif" : "rebond"
        anim.from = cible.scale
        anim.to = pressed ? echelle : 1
        anim.start()
        dark.stop(); dark.to = pressed ? 1 : 0; dark.start()
    }
    onCanceled: { anim.stop(); anim.caractere = "rebond"; anim.from = cible.scale; anim.to = 1; anim.start() }

    Ressort { id: anim; target: m.cible; property: "scale" }
    Ressort { id: dark; target: m; property: "_enf"; caractere: "vif"; mouvement: false }
}
