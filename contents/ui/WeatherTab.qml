// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami

import "helpers.js" as Helpers

// The Weather tab: a warning banner, the conditions now, the hourly and
// daily forecasts, today's extended forecast, UV, sun and moon, and a
// footer naming the location and station with refresh and BoM buttons.
ColumnLayout {
    id: tab

    required property WeatherModel weather
    required property MinuteClock clock

    // The banner was clicked: show the Warnings tab.
    signal warningsRequested()
    // The refresh button was clicked.
    signal refreshRequested()

    spacing: Kirigami.Units.smallSpacing

    // Severe weather warning banner: click to open the Warnings tab.
    Item {
        visible: tab.weather.hasWarnings
        Layout.fillWidth: true
        implicitHeight: bannerRow.implicitHeight + Kirigami.Units.smallSpacing * 2

        Rectangle {
            anchors.fill: parent
            color: Kirigami.Theme.neutralTextColor
            opacity: 0.18
            radius: 3
        }
        RowLayout {
            id: bannerRow
            anchors {
                left: parent.left; right: parent.right
                verticalCenter: parent.verticalCenter
                leftMargin:  Kirigami.Units.smallSpacing
                rightMargin: Kirigami.Units.smallSpacing
            }
            spacing: Kirigami.Units.smallSpacing
            PlainLabel {
                Layout.fillWidth: true
                wrapMode: Text.WordWrap
                color: Kirigami.Theme.neutralTextColor
                text: {
                    if (!tab.weather.hasWarnings) return ""
                    return "⚠  " + tab.weather.currentWarnings.map(function(w) {
                        return w.title || i18n("Warning")
                    }).join("  ·  ")
                }
            }
            Kirigami.Icon {
                Layout.preferredWidth:  Kirigami.Units.iconSizes.small
                Layout.preferredHeight: Kirigami.Units.iconSizes.small
                color: Kirigami.Theme.neutralTextColor
                source: "go-next-symbolic"
            }
        }
        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: tab.warningsRequested()
        }
    }

    CurrentConditions {
        Layout.fillWidth: true
        weather: tab.weather
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        visible: tab.weather.hasData && (tab.weather.upcomingHourly.length > 0 || tab.weather.today !== null)
        Layout.topMargin: Kirigami.Units.smallSpacing / 2
    }

    HourlyStrip {
        visible: tab.weather.hasData && tab.weather.upcomingHourly.length > 0
        Layout.fillWidth: true
        weather: tab.weather
        clock: tab.clock
    }

    Kirigami.Separator {
        Layout.fillWidth: true
        visible: tab.weather.hasData && tab.weather.upcomingHourly.length > 0 && tab.weather.today !== null
    }

    DailyStrip {
        visible: tab.weather.hasData && tab.weather.today !== null
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
        visible: tab.weather.hasData && tab.weather.today !== null
        Layout.topMargin: Kirigami.Units.smallSpacing / 2
    }

    // Today's extended forecast
    PlainLabel {
        visible: tab.weather.hasData && tab.weather.today !== null
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

    // UV · sunrise and sunset · moon phase
    RowLayout {
        visible: tab.weather.hasData && tab.weather.today !== null
        Layout.fillWidth: true
        Layout.leftMargin:  Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing

        // At night UV is always 0, so a moon shows instead; the sun icon and
        // UV reading return at sunrise (isNight follows the clock).
        PlainLabel {
            visible: tab.weather.isNight
            text: "🌛"
        }
        // Shown only for a category BoM actually gave: later days carry a uv
        // object whose fields are all null.
        Kirigami.Icon {
            visible: !tab.weather.isNight && tab.weather.todayUvKey !== ""
            Layout.preferredWidth:  Kirigami.Units.iconSizes.small
            Layout.preferredHeight: Kirigami.Units.iconSizes.small
            source: "weather-clear-symbolic"
        }
        PlainLabel {
            visible: !tab.weather.isNight && tab.weather.todayUvKey !== ""
            font.weight: Font.DemiBold
            text: {
                if (tab.weather.todayUvKey === "") return ""
                var label = {
                    low:      i18nc("UV index category", "Low"),
                    moderate: i18nc("UV index category", "Moderate"),
                    high:     i18nc("UV index category", "High"),
                    veryhigh: i18nc("UV index category", "Very High"),
                    extreme:  i18nc("UV index category", "Extreme")
                }[tab.weather.todayUvKey] || ""
                var idx = tab.weather.today.uv.max_index
                return label + (Helpers.hasValue(idx) ? "  " + idx : "")
            }
            color: {
                switch (tab.weather.todayUvKey) {
                    case "extreme":
                    case "veryhigh": return Kirigami.Theme.negativeTextColor
                    case "high":     return Kirigami.Theme.neutralTextColor
                    case "low":      return Kirigami.Theme.positiveTextColor
                    default:         return Kirigami.Theme.textColor
                }
            }
        }

        Item { Layout.fillWidth: true }

        PlainLabel {
            visible: tab.weather.today !== null && !!tab.weather.today.astronomical
            opacity: 0.65
            text: {
                if (!tab.weather.today || !tab.weather.today.astronomical) return ""
                var a = tab.weather.today.astronomical
                return "🌅 " + tab.clock.timeText(new Date(a.sunrise_time))
                       + "  ·  🌇 " + tab.clock.timeText(new Date(a.sunset_time))
            }
        }

        Item { Layout.fillWidth: true }

        PlainLabel {
            text: {
                var mp = Helpers.moonPhase(tab.clock.now)
                var name = {
                    new:             i18nc("moon phase", "New Moon"),
                    waxing_crescent: i18nc("moon phase", "Waxing Crescent"),
                    first_quarter:   i18nc("moon phase", "First Quarter"),
                    waxing_gibbous:  i18nc("moon phase", "Waxing Gibbous"),
                    full:            i18nc("moon phase", "Full Moon"),
                    waning_gibbous:  i18nc("moon phase", "Waning Gibbous"),
                    last_quarter:    i18nc("moon phase", "Last Quarter"),
                    waning_crescent: i18nc("moon phase", "Waning Crescent")
                }[mp.key]
                return mp.emoji + "  " + name
            }
        }
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

    // Footer: location · station (distance) · last update | refresh | BoM
    RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin:   Kirigami.Units.smallSpacing
        Layout.rightMargin:  Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing

        PlainLabel {
            Layout.fillWidth: true
            opacity: 0.5
            elide: Text.ElideRight
            text: {
                var parts = [tab.weather.locationName]
                var obs = tab.weather.observations
                if (tab.weather.hasData && obs && obs.station) {
                    parts.push(obs.station.distance
                        ? i18nc("observation station and its distance", "%1 (%2 km)",
                                obs.station.name, (obs.station.distance / 1000).toFixed(1))
                        : obs.station.name)
                }
                var updated = tab.clock.whenText(tab.weather.lastSuccessMs)
                if (updated) parts.push(updated)
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
