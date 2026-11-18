// Control Centre — every control talks to the system (NetworkManager, rfkill, PipeWire, backlight).
// Controls whose hardware is absent are shown as unavailable, never as working.
import QtQuick
import Droplet

// Tahoe-style: no panel behind, each module is its own piece of glass.
Item {
    id: cc
    width: 324
    height: col.implicitHeight

    // glass shapes for the compositor, in `target` coordinates
    function shapes(target) {
        const out = []
        const walk = (it) => {
            for (let i = 0; i < it.children.length; ++i) {
                const c = it.children[i]
                if (!c.visible) continue
                if (c.objectName === "glassTile") {
                    const q = c.mapToItem(target, 0, 0, c.width, c.height)   // includes the popup's scale
                    out.push({x: q.x, y: q.y, width: q.width, height: q.height, radius: c.radius * q.width / Math.max(1, c.width)})
                } else {
                    walk(c)
                }
            }
        }
        walk(cc)
        return out
    }

    component Tile: Glass {
        objectName: "glassTile"
        radius: 26
        // a pressed tile sinks: its glass follows it frame by frame
        onScaleChanged: if (Window.window && Window.window.updateRegions) Qt.callLater(Window.window.updateRegions)
        tint: Theme.verreMenu
        shadowSize: 22; shadowOffset: 8; shadowOpacity: .25
    }
    component RoundButton: Item {
        id: rb
        property bool on: false
        property bool available: true
        property string symbol
        signal clicked()
        width: 30; height: 30
        opacity: available ? 1 : 0.4
        Rectangle {
            id: disc
            anchors.fill: parent; radius: 15
            color: rb.on ? Theme.goutteRemplie : Theme.elementSurvol
            Behavior on color { Teinte {} }
            // pressed: a light veil over the disc, as on Tahoe's round buttons
            Rectangle { anchors.fill: parent; radius: 15; color: "#ffffff"; opacity: press.enfoncement * 0.18 }
        }
        Symbol {
            id: glyph
            anchors.centerIn: parent; size: 15; weight: "fill"; name: rb.symbol
            color: rb.on ? Theme.surAccent : Theme.label
            Behavior on color { Teinte {} }
        }
        // the pictogram answers a state change with a small bounce (SF Symbols "bounce")
        onOnChanged: { bounce.stop(); glyph.scale = 0.72; bounce.start() }
        Ressort { id: bounce; target: glyph; property: "scale"; to: 1; caractere: "rebond" }
        Pression { id: press; cible: disc; anchors.fill: parent; echelle: 0.88; enabled: rb.available
                   onClicked: rb.clicked() }
    }
    component Label2: Text {
        color: Theme.label
        font.family: Theme.texte; font.pixelSize: 13; font.weight: Font.DemiBold
        font.letterSpacing: Theme.tracking(13)
        elide: Text.ElideRight
    }
    component Sub: Text {
        color: Theme.label2
        font.family: Theme.texte; font.pixelSize: 11; font.letterSpacing: Theme.tracking(11)
        elide: Text.ElideRight
    }

    Column {
        id: col
        width: parent.width
        spacing: 10

        Row {
            spacing: 10
            // connectivity
            Tile {
                width: (col.width - 10) / 2; height: 140
                Column {
                    x: 12; y: 14; spacing: 16
                    width: parent.width - 24
                    Row {
                        spacing: 10; width: parent.width
                        RoundButton {
                            symbol: SystemControl.wired ? "network" : "wifi-high"
                            available: SystemControl.wifiAvailable
                            on: SystemControl.wired || (SystemControl.wifiAvailable && SystemControl.wifiEnabled)
                            onClicked: SystemControl.setWifi(!SystemControl.wifiEnabled)
                        }
                        Column {
                            width: parent.width - 40
                            anchors.verticalCenter: parent.verticalCenter
                            Label2 { width: parent.width; text: SystemControl.wired ? "Ethernet" : "Wi-Fi" }
                            Sub {
                                width: parent.width
                                text: SystemControl.network.length ? SystemControl.network
                                      : !SystemControl.wifiAvailable ? "Indisponible"
                                      : SystemControl.wifiEnabled ? "Non connecté" : "Désactivé"
                            }
                        }
                    }
                    Row {
                        spacing: 10; width: parent.width
                        RoundButton {
                            symbol: "bluetooth"
                            available: SystemControl.bluetoothAvailable
                            on: SystemControl.bluetoothEnabled
                            onClicked: SystemControl.setBluetooth(!SystemControl.bluetoothEnabled)
                        }
                        Column {
                            width: parent.width - 40
                            anchors.verticalCenter: parent.verticalCenter
                            Label2 { width: parent.width; text: "Bluetooth" }
                            Sub { width: parent.width
                                  text: !SystemControl.bluetoothAvailable ? "Indisponible"
                                        : SystemControl.bluetoothEnabled ? "Activé" : "Désactivé" }
                        }
                    }
                }
            }
            Column {
                spacing: 10
                width: (col.width - 10) / 2
                Tile {
                    width: parent.width; height: 65
                    Row {
                        x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                        RoundButton {
                            symbol: "moon"
                            on: NotificationServer.doNotDisturb
                            onClicked: NotificationServer.doNotDisturb = !NotificationServer.doNotDisturb
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            Label2 { text: "Concentration" }
                            Sub { text: NotificationServer.doNotDisturb ? "Ne pas déranger" : "Désactivée" }
                        }
                    }
                }
                Tile {
                    width: parent.width; height: 65
                    Row {
                        x: 12; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                        RoundButton {
                            symbol: SystemControl.darkMode ? "moon-stars" : "sun"
                            on: SystemControl.darkMode
                            onClicked: SystemControl.darkMode = !SystemControl.darkMode
                        }
                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            Label2 { text: "Apparence" }
                            Sub { text: SystemControl.darkMode ? "Sombre" : "Claire" }
                        }
                    }
                }
            }
        }

        Tile {
            visible: SystemControl.brightnessAvailable
            width: col.width; height: 68
            Label2 { x: 14; y: 11; text: "Écran" }
            Slider { x: 12; y: 32; width: parent.width - 24; symbol: "sun"
                     value: SystemControl.brightness; onMoved: (v) => SystemControl.setBrightness(v) }
        }
        Tile {
            width: col.width; height: 68
            Label2 { x: 14; y: 11; text: "Son" }
            Sub { anchors.right: parent.right; anchors.rightMargin: 14; y: 13
                  text: !SystemControl.audioAvailable ? "Aucune sortie audio"
                        : SystemControl.muted ? "Muet" : SystemControl.volume + " %" }
            Slider { x: 12; y: 32; width: parent.width - 24
                     symbol: SystemControl.muted || SystemControl.volume === 0 ? "speaker-x" : "speaker-high"
                     available: SystemControl.audioAvailable
                     value: SystemControl.volume; onMoved: (v) => SystemControl.setVolume(v) }
        }
        Tile {
            width: col.width; height: 44
            Row {
                x: 14; anchors.verticalCenter: parent.verticalCenter; spacing: 10
                Symbol { anchors.verticalCenter: parent.verticalCenter; size: 16; name: "gear"; weight: "fill"; color: Theme.label }
                Label2 { anchors.verticalCenter: parent.verticalCenter; text: "Réglages du système…"; font.weight: Font.Medium }
            }
            id: settingsTile
            Rectangle { anchors.fill: parent; radius: settingsTile.radius; color: Theme.label; opacity: tilePress.enfoncement * 0.06 }
            Pression { id: tilePress; anchors.fill: parent; cible: settingsTile; echelle: 0.97
                       onClicked: { Shell.CloseAll(); SystemControl.openSettings() } }
        }
    }
}
