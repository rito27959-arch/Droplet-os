// Recherche (Spotlight-like) — searches installed applications (.desktop) and launches them.
// Motion: the results panel grows with "doux"; rows arrive with a short staggered fade-rise
// ("vif", 12 ms apart); the selection glides between rows ("vif"); the placeholder fades.
import QtQuick
import Droplet

Item {
    id: launcher
    width: 660
    height: field.height + (results.visible ? results.height + 10 : 0)
    property alias query: input.text
    readonly property int rowH: 44
    readonly property int maxRows: 8

    function open() { input.text = ""; list.currentIndex = 0; input.forceActiveFocus() }
    function launchCurrent() {
        if (list.currentIndex >= 0 && list.currentIndex < apps.count) { apps.launch(list.currentIndex); Shell.CloseAll() }
    }

    AppsModel { id: apps; query: input.text }

    Glass {
        id: field
        width: parent.width; height: 54
        radius: 27
        tint: Theme.verreMenu; veil: .15
        Symbol { x: 20; anchors.verticalCenter: parent.verticalCenter; size: 20; name: "magnifying-glass"; weight: "bold"
                 color: Theme.label2 }
        TextInput {
            id: input
            x: 54; width: parent.width - 74
            anchors.verticalCenter: parent.verticalCenter
            color: Theme.label
            selectionColor: Theme.goutteVoile
            font.family: Theme.texte; font.pixelSize: 21; font.letterSpacing: Theme.tracking(21)
            clip: true
            onTextChanged: list.currentIndex = 0
            Keys.onDownPressed: list.currentIndex = Math.min(list.currentIndex + 1, apps.count - 1)
            Keys.onUpPressed: list.currentIndex = Math.max(list.currentIndex - 1, 0)
            Keys.onReturnPressed: launcher.launchCurrent()
            Keys.onEnterPressed: launcher.launchCurrent()
            Keys.onEscapePressed: Shell.CloseAll()
            Text {
                opacity: input.text.length ? 0 : 1
                Behavior on opacity { Ressort { caractere: "fondu"; mouvement: false } }
                anchors.verticalCenter: parent.verticalCenter
                text: "Rechercher une app"
                color: Theme.label3
                font: input.font
            }
        }
    }

    Glass {
        id: results
        visible: apps.count > 0
        y: field.height + 10
        opacity: visible ? 1 : 0
        Behavior on opacity { Ressort { caractere: "vif"; mouvement: false } }
        width: parent.width
        height: Math.min(apps.count, launcher.maxRows) * launcher.rowH + 16 + header.height
        radius: 22
        tint: Theme.verreMenu; veil: .15
        Behavior on height { Ressort { caractere: "doux" } }

        Text {
            id: header
            x: 20; y: 10; height: 22
            text: input.text.length ? "Meilleurs résultats" : "Apps"
            color: Theme.label2
            font.family: Theme.texte; font.pixelSize: 11; font.weight: Font.DemiBold
            font.letterSpacing: Theme.tracking(11)
        }
        ListView {
            id: list
            x: 8; y: header.y + header.height
            width: parent.width - 16
            height: parent.height - y - 8
            clip: true
            model: apps
            currentIndex: 0
            boundsBehavior: Flickable.StopAtBounds
            highlightFollowsCurrentItem: false
            highlight: Rectangle {
                width: list.width; height: launcher.rowH
                radius: 12; color: Theme.goutteRemplie
                y: list.currentItem ? list.currentItem.y : 0
                Behavior on y { Ressort { caractere: "vif" } }
            }
            populate: Transition {
                id: pop
                SequentialAnimation {
                    PropertyAction { property: "opacity"; value: 0 }
                    PauseAnimation { duration: Math.min(pop.ViewTransition.index, 8) * 12 }
                    ParallelAnimation {
                        Ressort { property: "opacity"; from: 0; to: 1; caractere: "vif"; mouvement: false }
                        Ressort { property: "y"; from: pop.ViewTransition.destination.y + 6; to: pop.ViewTransition.destination.y; caractere: "vif" }
                    }
                }
            }
            add: populate
            delegate: Item {
                id: row
                required property int index
                required property string name
                required property string iconSource
                required property string comment
                readonly property bool current: ListView.isCurrentItem
                width: list.width; height: launcher.rowH
                Image {
                    x: 10; anchors.verticalCenter: parent.verticalCenter
                    width: 32; height: 32
                    source: row.iconSource
                    sourceSize: Qt.size(64, 64)
                    smooth: true; mipmap: true
                }
                Column {
                    x: 54; anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 64
                    Text {
                        width: parent.width; elide: Text.ElideRight
                        text: row.name
                        color: row.current ? Theme.surAccent : Theme.label
                        Behavior on color { Teinte {} }
                        font.family: Theme.texte; font.pixelSize: 14; font.weight: Font.Medium
                        font.letterSpacing: Theme.tracking(14)
                    }
                    Text {
                        visible: text.length > 0
                        width: parent.width; elide: Text.ElideRight
                        text: row.comment
                        color: row.current ? "#d9ffffff" : Theme.label2
                        font.family: Theme.texte; font.pixelSize: 11; font.letterSpacing: Theme.tracking(11)
                    }
                }
                MouseArea {
                    anchors.fill: parent
                    hoverEnabled: true
                    onEntered: list.currentIndex = row.index
                    onClicked: launcher.launchCurrent()
                }
            }
        }
    }
}
