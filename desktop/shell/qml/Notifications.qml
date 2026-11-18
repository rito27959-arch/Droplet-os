// Notification banners (top-right), fed by the org.freedesktop.Notifications server.
// macOS 27 kit: 344 x 77, radius 20, padding 12/14/12/10, icon 32, title Bold 13, time 11.
import QtQuick
import QtQuick.Window
import org.kde.layershell as LayerShell
import Droplet

Window {
    id: win
    width: Theme.largeurNotification + 16
    height: Math.max(90, list.contentHeight + 24)
    color: "transparent"
    visible: NotificationServer.registered && NotificationServer.count > 0
    LayerShell.Window.scope: "droplet-notifications"
    LayerShell.Window.layer: LayerShell.Window.LayerOverlay
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorRight
    LayerShell.Window.margins.top: 4
    LayerShell.Window.margins.right: 4
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone

    // the glass follows every card frame by frame (arrival spring, swipe, dismissal)
    function updateRegions() {
        const rects = []
        for (let i = 0; i < list.count; ++i) {
            const it = list.itemAtIndex(i)
            if (!it || !it.card || it.leaving || it.opacity < 0.05) continue
            const q = it.card.mapToItem(win.contentItem, 0, 0, it.card.width, it.card.height)
            rects.push({x: q.x, y: q.y, width: q.width, height: q.height,
                        radius: Theme.rayonNotification * q.width / Math.max(1, it.card.width)})
        }
        Effects.glass(win, rects, Theme.rayonNotification)
    }

    ListView {
        id: list
        x: 0; y: 8
        width: parent.width; height: contentHeight
        interactive: false
        spacing: 0
        model: NotificationServer
        onContentHeightChanged: Qt.callLater(win.updateRegions)
        // a banner slides in from the right edge on the "rebond" spring; the others make room
        add: Transition {
            ParallelAnimation {
                Ressort { property: "opacity"; from: 0; to: 1; caractere: "vif"; mouvement: false }
                Ressort { property: "x"; from: 56; to: 0; caractere: "rebond" }
            }
        }
        remove: Transition {
            ParallelAnimation {
                Ressort { property: "opacity"; to: 0; caractere: "sortie"; mouvement: false }
                Ressort { property: "scale"; to: 0.94; caractere: "sortie" }
            }
        }
        displaced: Transition { Ressort { properties: "y"; caractere: "doux" } }
        delegate: Item {
            id: n
            required property int nid
            required property string appName
            required property string appIcon
            required property string summary
            required property string body
            required property var time
            property alias card: card
            property bool leaving: false
            width: list.width
            height: card.height + 10
            onXChanged: Qt.callLater(win.updateRegions)
            onOpacityChanged: Qt.callLater(win.updateRegions)
            onScaleChanged: Qt.callLater(win.updateRegions)
            ListView.onRemove: leaving = true
            Glass {
                id: card
                property real home: 8
                x: home; width: parent.width - 16
                onXChanged: Qt.callLater(win.updateRegions)
                onScaleChanged: Qt.callLater(win.updateRegions)
                Ressort { id: homeAnim; target: card; property: "x"; to: card.home; caractere: "rebond" }
                Ressort { id: fling; target: card; property: "x"; caractere: "sortie"
                          onFinished: NotificationServer.dismiss(n.nid) }
                opacity: 1 - Math.max(0, card.x - card.home) / (win.width * 0.9)
                height: Math.max(77, textCol.implicitHeight + 24)
                radius: Theme.rayonNotification
                tint: Theme.verreMenu; veil: .15
                shadowSize: 30; shadowOffset: 8; shadowOpacity: 0.3
                Image {
                    x: 14; anchors.verticalCenter: parent.verticalCenter
                    width: 32; height: 32
                    source: n.appIcon
                    sourceSize: Qt.size(64, 64)
                    smooth: true; mipmap: true
                }
                Column {
                    id: textCol
                    x: 58; anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 58 - 14
                    spacing: 0
                    Item {
                        width: parent.width; height: title.implicitHeight
                        Text {
                            id: title
                            width: parent.width - when.implicitWidth - 8
                            elide: Text.ElideRight
                            text: n.summary.length ? n.summary : n.appName
                            color: Theme.label
                            font.family: Theme.texte; font.pixelSize: 13; font.weight: Font.Bold
                            font.letterSpacing: Theme.tracking(13)
                        }
                        Text {
                            id: when
                            anchors.right: parent.right
                            text: "maintenant"
                            color: Theme.label2
                            font.family: Theme.texte; font.pixelSize: 11; font.letterSpacing: Theme.tracking(11)
                        }
                    }
                    Text {
                        visible: text.length > 0
                        width: parent.width
                        wrapMode: Text.Wrap
                        maximumLineCount: 3
                        elide: Text.ElideRight
                        textFormat: Text.PlainText
                        text: n.body
                        color: Theme.label
                        font.family: Theme.texte; font.pixelSize: 13; font.letterSpacing: Theme.tracking(13)
                    }
                }
                // tap: open; swipe right: the card follows the pointer, then flies off past 70 pt
                // or springs home
                Pression {
                    id: cardPress; anchors.fill: parent; cible: card; echelle: 0.98
                    drag.target: card; drag.axis: Drag.XAxis
                    drag.minimumX: card.home - 12; drag.maximumX: card.home + win.width
                    drag.threshold: 6
                    onClicked: if (!drag.active && Math.abs(card.x - card.home) < 2) NotificationServer.invoke(n.nid, "default")
                    onReleased: {
                        if (card.x - card.home > 70) { fling.to = card.home + win.width; fling.start() }
                        else if (card.x !== card.home) homeAnim.start()
                    }
                }
                // close button: appears on hover at the top-left corner, as on macOS
                Rectangle {
                    id: closeBtn
                    readonly property bool wanted: cardPress.containsMouse || closeArea.containsMouse
                    x: -6; y: -6; width: 20; height: 20; radius: 10
                    color: Theme.dark ? "#3a3a3c" : "#f2f2f2"
                    border.width: 0.5; border.color: Theme.separateur
                    opacity: wanted ? 1 : 0
                    scale: wanted ? 1 : 0.6
                    visible: opacity > 0
                    Behavior on opacity { Ressort { caractere: closeBtn.wanted ? "vif" : "sortie"; mouvement: false } }
                    Behavior on scale { Ressort { caractere: closeBtn.wanted ? "rebond" : "sortie" } }
                    Symbol { anchors.centerIn: parent; size: 10; weight: "bold"; name: "x"; color: Theme.label2 }
                    MouseArea { id: closeArea; anchors.fill: parent; anchors.margins: -4; hoverEnabled: true
                                onClicked: NotificationServer.dismiss(n.nid) }
                }
            }
        }
    }
}
