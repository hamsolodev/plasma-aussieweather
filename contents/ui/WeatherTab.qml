// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami

// The Weather tab: a warning banner, the conditions now, the hourly and
// daily forecasts, today's extended forecast, UV, sun and moon, and a
// footer naming the place, which switches between the saved places, and the
// station, with refresh and BoM buttons.
ColumnLayout {
    id: tab

    required property WeatherModel weather
    required property MinuteClock clock
    // The saved places, {search, radar} each (places.js), and the index of
    // the one shown.
    required property var places
    required property int currentPlace

    // The banner was clicked: show the Warnings tab.
    signal warningsRequested()
    // The refresh button was clicked.
    signal refreshRequested()
    // A place was picked from the place menu.
    signal placeChosen(int index)
    // "Add or Edit Places…" was picked.
    signal configureRequested()

    spacing: Kirigami.Units.smallSpacing

    WarningBanner {
        Layout.fillWidth: true
        weather: tab.weather
        onClicked: tab.warningsRequested()
    }

    CurrentConditions {
        Layout.fillWidth: true
        weather: tab.weather
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        visible: (tab.weather.upcomingHourly.length > 0 || tab.weather.today !== null)
        Layout.topMargin: Kirigami.Units.smallSpacing / 2
    }

    HourlyStrip {
        visible: tab.weather.upcomingHourly.length > 0
        Layout.fillWidth: true
        weather: tab.weather
        clock: tab.clock
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        visible: tab.weather.upcomingHourly.length > 0 && tab.weather.today !== null
    }

    DailyStrip {
        visible: tab.weather.today !== null
        Layout.fillWidth: true
        weather: tab.weather
    }

    // Error / loading state
    PlainLabel {
        visible: !tab.weather.hasData
        Layout.fillWidth: true
        Layout.margins: Kirigami.Units.largeSpacing
        wrapMode: Text.WordWrap
        horizontalAlignment: Text.AlignHCenter
        opacity: 0.7
        text: tab.weather.errorText || i18n("Waiting for data…")
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        visible: tab.weather.today !== null
        Layout.topMargin: Kirigami.Units.smallSpacing / 2
    }

    // Today's extended forecast
    PlainLabel {
        visible: tab.weather.today !== null
                 && (tab.weather.today.extended_text || "") !== ""
        Layout.fillWidth: true
        Layout.preferredHeight: implicitHeight
        Layout.leftMargin:  Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing
        Layout.topMargin:   Kirigami.Units.smallSpacing / 2
        wrapMode: Text.WordWrap
        opacity: 0.75
        text: tab.weather.today !== null ? (tab.weather.today.extended_text || "") : ""
    }

    SunMoonRow {
        visible: tab.weather.today !== null
        Layout.fillWidth: true
        Layout.leftMargin:  Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing
        weather: tab.weather
        clock: tab.clock
    }

    // Pins the footer to the bottom.
    Item { Layout.fillHeight: true }

    // A failed update while older data is still shown: say so, rather than
    // let the old data pass for current.
    PlainLabel {
        visible: tab.weather.hasData && tab.weather.errorText !== ""
        Layout.fillWidth: true
        Layout.leftMargin:  Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing
        wrapMode: Text.WordWrap
        color: Kirigami.Theme.neutralTextColor
        text: "⚠  " + tab.weather.errorText
    }

    Kirigami.Separator { Layout.fillWidth: true }

    // Footer: place ▾ | last update · station (distance) | refresh | BoM
    RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin:   Kirigami.Units.smallSpacing
        Layout.rightMargin:  Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing

        // The place, which opens a menu of the saved places. Names are drawn
        // by PlainLabels: a control's own label renders AutoText.
        PlasmaComponents.ToolButton {
            id: placeButton
            Layout.maximumWidth: Kirigami.Units.gridUnit * 9
            Accessible.name: tab.weather.locationName || i18n("Choose a place")
            Accessible.description: i18n("Switch to another saved place")
            onClicked: placeMenu.popup(placeButton, 0, placeButton.height)
            contentItem: RowLayout {
                spacing: Kirigami.Units.smallSpacing
                PlainLabel {
                    Layout.fillWidth: true
                    opacity: 0.7
                    elide: Text.ElideRight
                    text: tab.weather.locationName || i18n("Choose a place")
                }
                Kirigami.Icon {
                    source: "arrow-down"
                    Layout.preferredWidth: Kirigami.Units.iconSizes.small
                    Layout.preferredHeight: Kirigami.Units.iconSizes.small
                }
            }

            PlasmaComponents.Menu {
                id: placeMenu

                Instantiator {
                    model: tab.places
                    delegate: PlasmaComponents.MenuItem {
                        id: placeItem
                        required property int index
                        required property var modelData
                        objectName: "placeItem"
                        // One place is shown: picking the one shown keeps it
                        // checked, and the indicator is a radio button.
                        checkable: true
                        autoExclusive: true
                        checked: index === tab.currentPlace
                        Accessible.name: modelData.search
                        onTriggered: tab.placeChosen(index)
                        // As Plasma's MenuItem lays its label out.
                        contentItem: RowLayout {
                            Item { Layout.preferredWidth: placeItem.indicator.width }
                            PlainLabel {
                                Layout.fillWidth: true
                                text: placeItem.modelData.search
                            }
                        }
                    }
                    onObjectAdded: (index, object) => placeMenu.insertItem(index, object)
                    onObjectRemoved: (index, object) => placeMenu.removeItem(object)
                }

                PlasmaComponents.MenuSeparator {}

                PlasmaComponents.MenuItem {
                    icon.name: "configure"
                    text: i18n("Add or Edit Places…")
                    onTriggered: tab.configureRequested()
                }
            }
        }

        PlainLabel {
            Layout.fillWidth: true
            opacity: 0.5
            elide: Text.ElideRight
            // The update time first: it says how old the data is, and a long
            // station name is what eliding should cut.
            text: {
                var parts = []
                var updated = tab.clock.whenText(tab.weather.lastSuccessMs)
                if (updated) parts.push(updated)
                var obs = tab.weather.observations
                if (obs && obs.station) {
                    parts.push(obs.station.distance
                        ? i18nc("observation station and its distance", "%1 (%2 km)",
                                obs.station.name, (obs.station.distance / 1000).toFixed(1))
                        : obs.station.name)
                }
                return parts.join("  ·  ")
            }
        }
        PlasmaComponents.Button {
            icon.name: "view-refresh-symbolic"
            onClicked: tab.refreshRequested()
        }
        PlasmaComponents.Button {
            icon.name: "internet-web-browser-symbolic"
            text: i18nc("abbreviation of Bureau of Meteorology", "BoM")
            onClicked: Qt.openUrlExternally("https://www.bom.gov.au/location/australia")
        }
    }
}
