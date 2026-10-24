// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami

import "helpers.js" as Helpers

// The days ahead from today: weekday, icon (hover for the extended
// forecast), high, low and rain chance.
ColumnLayout {
    id: strip

    required property WeatherModel weather
    readonly property var days: weather.days

    spacing: Kirigami.Units.smallSpacing

    PlainLabel {
        Layout.leftMargin: Kirigami.Units.smallSpacing
        text: i18np("1-Day Forecast", "%1-Day Forecast", strip.days.length)
        font.weight: Font.Bold
        opacity: 0.55
    }

    // Row with explicit widths (1/N each): RowLayout + Repeater +
    // Layout.fillWidth is unreliable when the model populates after the
    // first layout.
    Row {
        id: row
        Layout.fillWidth: true
        Layout.leftMargin:  Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing

        Repeater {
            model: strip.days
            delegate: ColumnLayout {
                required property var modelData
                required property int index
                width: row.width / Math.max(strip.days.length, 1)
                spacing: 1

                PlainLabel {
                    Layout.alignment: Qt.AlignHCenter
                    text: {
                        if (index === 0) return i18n("Today")
                        var day = Helpers.forecastWeekday(modelData.date)
                        return day < 0 ? "—" : Qt.locale().dayName(day, Locale.ShortFormat)
                    }
                    font.weight: index === 0 ? Font.Bold : Font.Normal
                    opacity: 0.65
                }
                Kirigami.Icon {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth:  Kirigami.Units.iconSizes.large
                    Layout.preferredHeight: Kirigami.Units.iconSizes.large
                    source: Helpers.bomIcon(Helpers.iconDescriptor(modelData), false)

                    HoverHandler { id: hover }
                    PlasmaComponents.ToolTip {
                        visible: hover.hovered && text !== ""
                        textFormat: Text.PlainText
                        delay: Kirigami.Units.toolTipDelay
                        text: modelData.extended_text || modelData.short_text || ""
                    }
                }
                ToneLabel {
                    Layout.alignment: Qt.AlignHCenter
                    text: Helpers.formatTemp(modelData.temp_max)
                    tone: Helpers.tempTone(modelData.temp_max)
                    font.weight: Font.DemiBold
                }
                PlainLabel {
                    Layout.alignment: Qt.AlignHCenter
                    text: Helpers.formatTemp(modelData.temp_min)
                    opacity: 0.5
                }
                RainChanceLabel {
                    Layout.alignment: Qt.AlignHCenter
                    entry: modelData
                }
            }
        }
    }
}
