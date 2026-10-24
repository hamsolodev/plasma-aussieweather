// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

import "helpers.js" as Helpers

// The weather now: icon, temperature, feels-like and condition, today's
// high, low and rain chance; then wind, humidity and rain since 9 am.
ColumnLayout {
    id: conditions

    required property WeatherModel weather
    readonly property var obs: weather.observations

    spacing: Kirigami.Units.smallSpacing

    // icon | big temp | description (fills) | today's high / low / rain
    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin:  Kirigami.Units.smallSpacing
        Layout.leftMargin: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing

        Kirigami.Icon {
            Layout.preferredWidth:  Kirigami.Units.iconSizes.large
            Layout.preferredHeight: Kirigami.Units.iconSizes.large
            source: conditions.weather.currentIcon
            visible: conditions.weather.hasData
        }

        PlainLabel {
            visible: conditions.weather.hasData
            text: conditions.obs ? Helpers.formatTemp(conditions.obs.temp) : "—"
            font.pointSize: Kirigami.Theme.defaultFont.pointSize * 3
            font.weight: Font.Bold
        }

        PlainLabel {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            visible: conditions.obs !== null
            opacity: 0.7
            wrapMode: Text.WordWrap
            text: {
                if (!conditions.obs) return ""
                var parts = []
                if (Helpers.hasValue(conditions.obs.temp_feels_like))
                    parts.push(i18n("Feels like %1", Helpers.formatTemp(conditions.obs.temp_feels_like)))
                if (conditions.weather.summaryText) parts.push(conditions.weather.summaryText)
                return parts.join("  ·  ")
            }
        }

        ColumnLayout {
            visible: conditions.weather.today !== null
            spacing: 0
            Layout.alignment: Qt.AlignVCenter
            Layout.rightMargin: Kirigami.Units.smallSpacing

            ToneLabel {
                readonly property var high: conditions.weather.today ? conditions.weather.today.temp_max : null
                Layout.alignment: Qt.AlignRight
                text: Helpers.formatTemp(high)
                tone: Helpers.tempTone(high)
                font.pointSize: Kirigami.Theme.defaultFont.pointSize + 1
                font.weight: Font.Bold
            }
            PlainLabel {
                Layout.alignment: Qt.AlignRight
                text: Helpers.formatTemp(conditions.weather.today ? conditions.weather.today.temp_min : null)
                opacity: 0.55
            }
            RainChanceLabel {
                Layout.alignment: Qt.AlignRight
                entry: conditions.weather.today
            }
        }
    }

    // wind (left) | humidity (right). BoM's observations carry no pressure,
    // dew point or cloud cover.
    RowLayout {
        visible: conditions.obs !== null
        Layout.fillWidth: true
        Layout.leftMargin:  Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing

        PlainLabel {
            text: {
                if (!conditions.obs) return ""
                var w = conditions.obs.wind || {}
                var g = conditions.obs.gust || {}
                var ws = Helpers.windStr(w.speed_kilometre, w.direction)
                return "💨  " + (g.speed_kilometre
                    ? i18n("%1  (gusts %2)", ws, Math.round(g.speed_kilometre))
                    : ws)
            }
        }
        Item { Layout.fillWidth: true }
        PlainLabel {
            visible: !!conditions.obs && Helpers.hasValue(conditions.obs.humidity)
            text: conditions.obs && Helpers.hasValue(conditions.obs.humidity)
                ? "💧  " + i18nc("relative humidity", "%1% RH", Math.round(conditions.obs.humidity))
                : ""
        }
    }

    PlainLabel {
        visible: conditions.obs !== null
                 && Helpers.hasValue(conditions.obs.rain_since_9am)
        Layout.leftMargin: Kirigami.Units.smallSpacing
        text: conditions.obs && Helpers.hasValue(conditions.obs.rain_since_9am)
            ? "🌧  " + i18n("%1 mm since 9 am", conditions.obs.rain_since_9am)
            : ""
    }
}
