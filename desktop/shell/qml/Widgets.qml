// Desktop widgets — only live data: date/month, storage, battery (when there is one).
import QtQuick
import QtQuick.Window
import org.kde.layershell as LayerShell
import Droplet

Window {
    id: win
    // a margin around the widgets so their glass shadow is not cut by the surface edge
    readonly property int pad: 22          // = the widgets' distance from the screen edges
    width: flow.width + pad + 40
    height: flow.height + pad + 40
    color: "transparent"
    visible: true
    LayerShell.Window.scope: "droplet-widgets"
    LayerShell.Window.layer: LayerShell.Window.LayerBottom
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorLeft
    LayerShell.Window.margins.top: 0
    LayerShell.Window.margins.left: 0
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone

    property date now: new Date()
    // only the date is shown: refresh when the day changes, nothing in between
    Timer {
        interval: 60000; running: true; repeat: true
        onTriggered: { const d = new Date(); if (d.getDate() !== win.now.getDate()) win.now = d }
    }

    function updateRegions() {
        const rects = []
        for (const w of [cal, storage, battery]) {
            if (!w.visible) continue
            const p = w.mapToItem(win.contentItem, 0, 0)
            rects.push(Qt.rect(p.x, p.y, w.width, w.height))
        }
        Effects.glass(win, rects, Theme.rayonWidget)
    }
    Component.onCompleted: Qt.callLater(updateRegions)
    onVisibleChanged: Qt.callLater(updateRegions)

    component Caps: Text {
        font.family: Theme.texte; font.pixelSize: 11; font.weight: Font.Bold
        font.letterSpacing: 0.4
        font.capitalization: Font.AllUppercase
    }

    Column {
        id: flow
        x: win.pad; y: win.pad
        spacing: 16
        onHeightChanged: Qt.callLater(win.updateRegions)

        // ---- calendar (medium)
        Glass {
            id: cal
            width: 344; height: 164
            radius: Theme.rayonWidget
            tint: Theme.verreFlottant
            shadowOpacity: 0.22; shadowSize: 30; shadowOffset: 10
            readonly property var loc: Qt.locale("fr_FR")
            Column {
                x: 18; y: 16
                Caps { text: win.now.toLocaleDateString(cal.loc, "dddd"); color: Theme.goutte }
                Text {
                    text: win.now.getDate()
                    color: Theme.label
                    font.family: Theme.titres; font.pixelSize: 48; font.weight: Font.Light
                    font.letterSpacing: -1
                }
                Text {
                    text: win.now.toLocaleDateString(cal.loc, "MMMM yyyy")
                    color: Theme.label2
                    font.family: Theme.texte; font.pixelSize: 12; font.letterSpacing: Theme.tracking(12)
                }
            }
            // month grid
            Grid {
                id: grid
                x: 150; y: 16
                columns: 7
                columnSpacing: 0; rowSpacing: 1
                readonly property int cell: 25
                readonly property var first: new Date(win.now.getFullYear(), win.now.getMonth(), 1)
                readonly property int offset: (first.getDay() + 6) % 7    // weeks start on Monday
                readonly property int days: new Date(win.now.getFullYear(), win.now.getMonth() + 1, 0).getDate()
                Repeater {
                    model: ["L", "M", "M", "J", "V", "S", "D"]
                    Text {
                        required property string modelData
                        width: grid.cell; height: 17
                        horizontalAlignment: Text.AlignHCenter
                        text: modelData
                        color: Theme.label3
                        font.family: Theme.texte; font.pixelSize: 9; font.weight: Font.Bold
                    }
                }
                Repeater {
                    model: 42
                    Item {
                        required property int index
                        readonly property int day: index - grid.offset + 1
                        readonly property bool inMonth: day >= 1 && day <= grid.days
                        readonly property bool today: day === win.now.getDate()
                        visible: index < Math.ceil((grid.offset + grid.days) / 7) * 7
                        width: grid.cell; height: 20
                        Rectangle {
                            anchors.centerIn: parent
                            width: 20; height: 20; radius: 10
                            color: Theme.goutteRemplie
                            visible: parent.inMonth && parent.today
                        }
                        Text {
                            anchors.centerIn: parent
                            text: parent.inMonth ? parent.day : ""
                            color: parent.today ? Theme.surAccent : (index % 7 > 4 ? Theme.label2 : Theme.label)
                            font.family: Theme.texte; font.pixelSize: 10
                            font.weight: parent.today ? Font.Bold : Font.Medium
                        }
                    }
                }
            }
        }

        Row {
            spacing: 16
            // ---- storage (small)
            Glass {
                id: storage
                width: 164; height: 164
                radius: Theme.rayonWidget
                tint: Theme.verreFlottant
                shadowOpacity: 0.22; shadowSize: 30; shadowOffset: 10
                Caps { x: 18; y: 16; text: "Stockage"; color: Theme.label2 }
                Canvas {
                    id: ring
                    x: 18; y: 40; width: 62; height: 62
                    property real used: SystemControl.storageUsed
                    onUsedChanged: requestPaint()
                    Connections { target: Theme; function onDarkChanged() { ring.requestPaint() } }
                    onPaint: {
                        const c = getContext("2d"); c.reset()
                        c.lineWidth = 7; c.lineCap = "round"
                        c.strokeStyle = Theme.element
                        c.beginPath(); c.arc(31, 31, 26, 0, Math.PI * 2); c.stroke()
                        c.strokeStyle = Theme.goutte
                        c.beginPath(); c.arc(31, 31, 26, -Math.PI / 2, -Math.PI / 2 + Math.PI * 2 * Math.max(0.02, used)); c.stroke()
                    }
                    Text {
                        anchors.centerIn: parent
                        text: Math.round(SystemControl.storageUsed * 100) + "%"
                        color: Theme.label
                        font.family: Theme.texte; font.pixelSize: 13; font.weight: Font.DemiBold
                    }
                }
                Column {
                    x: 18; y: 112
                    Text { text: SystemControl.freeSpace; color: Theme.label
                           font.family: Theme.texte; font.pixelSize: 12; font.weight: Font.DemiBold
                           font.letterSpacing: Theme.tracking(12) }
                    Text { text: SystemControl.totalSpace; color: Theme.label2
                           font.family: Theme.texte; font.pixelSize: 11; font.letterSpacing: Theme.tracking(11) }
                }
            }
            // ---- battery (small, only with a battery)
            Glass {
                id: battery
                visible: SystemControl.batteryPresent
                onVisibleChanged: Qt.callLater(win.updateRegions)
                width: 164; height: 164
                radius: Theme.rayonWidget
                tint: Theme.verreFlottant
                shadowOpacity: 0.22; shadowSize: 30; shadowOffset: 10
                Caps { x: 18; y: 16; text: "Batterie"; color: Theme.label2 }
                Text {
                    x: 18; y: 40
                    text: SystemControl.battery + "%"
                    color: Theme.label
                    font.family: Theme.titres; font.pixelSize: 40; font.weight: Font.Light
                }
                Text {
                    x: 18; y: 112
                    text: SystemControl.charging ? "En charge" : "Sur batterie"
                    color: Theme.label2
                    font.family: Theme.texte; font.pixelSize: 12
                }
            }
        }
    }
}
