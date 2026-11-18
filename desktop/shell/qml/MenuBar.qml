// Menu bar — 24 pt, transparent over the wallpaper. Metrics from the macOS 27 kit: items 24 pt
// with 9 pt side padding and no gap, labels Semibold 13, app name Heavy 13, the open item shown
// by a capsule that runs 4 pt past the item on each side.
import QtQuick
import QtQuick.Window
import org.kde.layershell as LayerShell
import org.kde.taskmanager as TaskManager
import Droplet

Window {
    id: bar
    property var tasks
    property string appName: ""
    // exported for the menus (overlay coordinates are the same as the bar's)
    // menus open under the item's selection capsule, which runs 4 pt past the item
    readonly property real dropletMenuX: leftRow.x + logoBtn.x - 4
    readonly property real appMenuX: leftRow.x + appBtn.x - 4
    readonly property real controlCenterRight: bar.width - (ccBtn.x + ccBtn.width)

    height: Theme.barreMenus
    color: "transparent"
    visible: true
    LayerShell.Window.scope: "droplet-menubar"
    LayerShell.Window.layer: LayerShell.Window.LayerTop
    LayerShell.Window.anchors: LayerShell.Window.AnchorTop | LayerShell.Window.AnchorLeft | LayerShell.Window.AnchorRight
    LayerShell.Window.exclusionZone: Theme.barreMenus
    LayerShell.Window.keyboardInteractivity: LayerShell.Window.KeyboardInteractivityNone

    // a whisper of shade so white text stays legible on any wallpaper
    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0; color: "#33000000" }
            GradientStop { position: 1; color: "#0d000000" }
        }
    }

    component BarButton: Item {
        id: b
        property bool active: false
        property alias contentItem: holder.data
        signal clicked()
        height: Theme.barreMenus
        anchors.verticalCenter: parent ? parent.verticalCenter : undefined
        Rectangle {
            anchors.fill: parent
            anchors.leftMargin: -4; anchors.rightMargin: -4
            radius: height / 2
            color: "#ffffff"
            // appears at once when an item opens (macOS), fades when its menu closes
            opacity: b.active ? 0.24 : (hover.pressed ? 0.16 : 0)
            Behavior on opacity { enabled: !b.active && !hover.pressed; Ressort { caractere: "fondu"; mouvement: false } }
        }
        Item { id: holder; anchors.fill: parent }
        MouseArea { id: hover; anchors.fill: parent; hoverEnabled: true; onClicked: b.clicked() }
    }
    component BarText: Text {
        anchors.centerIn: parent
        color: "#ffffff"
        font.family: Theme.texte
        font.pixelSize: 13
        font.letterSpacing: Theme.tracking(13)
        font.weight: Font.DemiBold
        style: Text.Raised; styleColor: "#26000000"
    }

    Row {
        id: leftRow
        anchors.left: parent.left; anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        spacing: 0
        BarButton {
            id: logoBtn
            width: 33
            active: Shell.openMenu === "droplet"
            onClicked: Shell.ShowMenu("droplet")
            Image {
                anchors.centerIn: parent
                source: "qrc:/qt/qml/Droplet/assets/eclipse.svg"
                sourceSize: Qt.size(32, 32)
                width: 16; height: 16
            }
        }
        BarButton {
            id: appBtn
            width: appLabel.implicitWidth + 20      // 11 + 9
            active: Shell.openMenu === "app"
            onClicked: Shell.ShowMenu("app")
            BarText { id: appLabel; x: 11; anchors.centerIn: undefined; anchors.verticalCenter: parent.verticalCenter
                      text: bar.appName || "Bureau"; font.weight: Font.ExtraBold }
        }
    }

    Row {
        anchors.right: parent.right; anchors.rightMargin: 20
        anchors.verticalCenter: parent.verticalCenter
        spacing: 0

        BarButton {
            visible: SystemControl.batteryPresent
            width: batRow.implicitWidth + 18
            Row {
                id: batRow
                anchors.centerIn: parent
                spacing: 5
                BarText { anchors.centerIn: undefined; anchors.verticalCenter: parent.verticalCenter
                          text: SystemControl.battery + " %"; font.pixelSize: 12 }
                Symbol {
                    anchors.verticalCenter: parent.verticalCenter
                    size: 22; color: "#ffffff"; weight: "fill"
                    name: SystemControl.charging ? "battery-charging"
                          : SystemControl.battery > 80 ? "battery-full" : SystemControl.battery > 55 ? "battery-high"
                          : SystemControl.battery > 25 ? "battery-medium" : "battery-low"
                }
            }
        }
        BarButton {
            width: 34
            onClicked: Shell.ToggleControlCenter()
            Symbol {
                anchors.centerIn: parent
                size: 16; color: "#ffffff"; weight: "bold"
                opacity: (SystemControl.wired || SystemControl.network.length > 0) ? 1 : 0.45
                name: SystemControl.wired ? "network"
                      : (SystemControl.wifiAvailable && !SystemControl.wifiEnabled) ? "wifi-slash" : "wifi-high"
            }
        }
        BarButton {
            width: 34
            active: Shell.launcherOpen
            onClicked: Shell.ToggleLauncher()
            Symbol { anchors.centerIn: parent; size: 15; color: "#ffffff"; weight: "bold"; name: "magnifying-glass" }
        }
        BarButton {
            id: ccBtn
            width: 34
            active: Shell.controlCenterOpen
            onClicked: Shell.ToggleControlCenter()
            Symbol { anchors.centerIn: parent; size: 17; color: "#ffffff"; weight: "fill"; name: "toggle-right" }
        }
        Item {   // clock: information only, not a button
            width: clockRow.implicitWidth + 9; height: Theme.barreMenus
            anchors.verticalCenter: parent.verticalCenter
            Row {
                id: clockRow
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                BarText { id: day; anchors.centerIn: undefined }
                BarText { id: clock; anchors.centerIn: undefined }
            }
            // the text only changes on the minute: wake then, not every second
            // (no triggeredOnStart: restart() inside the handler would fire it again at once)
            function refresh() {
                const now = new Date()
                day.text = now.toLocaleDateString(Qt.locale("fr_FR"), "ddd d MMM")
                clock.text = now.toLocaleTimeString(Qt.locale("fr_FR"), "HH:mm")
                tick.interval = 60000 - (now.getSeconds() * 1000 + now.getMilliseconds()) + 50
                tick.restart()
            }
            Component.onCompleted: refresh()
            Timer { id: tick; repeat: false; onTriggered: parent.refresh() }
        }
    }
}
