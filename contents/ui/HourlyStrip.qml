// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami

import "helpers.js" as Helpers

// The next hours: time, icon (hover for detail), temperature and rain
// chance for each upcoming hourly slot.
ColumnLayout {
    id: strip

    required property WeatherModel weather
    required property MinuteClock clock
    readonly property var slots: weather.upcomingHourly

    spacing: Kirigami.Units.smallSpacing

    PlainLabel {
        Layout.leftMargin: Kirigami.Units.smallSpacing
        text: i18np("Next Hour", "Next %1 Hours", strip.slots.length)
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
            model: strip.slots
            delegate: ColumnLayout {
                required property var modelData
                required property int index
                width: row.width / Math.max(strip.slots.length, 1)
                spacing: 1

                PlainLabel {
                    Layout.alignment: Qt.AlignHCenter
                    font.weight: index === 0 ? Font.Bold : Font.Normal
                    opacity: 0.65
                    text: {
                        var start = Date.parse(modelData.time)
                        if (Helpers.hourBucket(start) === strip.weather.currentHour)
                            return i18n("Now")
                        var d = new Date(start)
                        return Qt.formatTime(d, Helpers.slotTimeFormat(d, strip.clock.use24Hour))
                    }
                }
                Kirigami.Icon {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth:  Kirigami.Units.iconSizes.medium
                    Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                    source: Helpers.bomIcon(Helpers.iconDescriptor(modelData), modelData.is_night)

                    HoverHandler { id: hover }
                    PlasmaComponents.ToolTip {
                        visible: hover.hovered && text !== ""
                        textFormat: Text.PlainText
                        delay: Kirigami.Units.toolTipDelay
                        text: {
                            var lines = []
                            if (Helpers.hasValue(modelData.temp_feels_like))
                                lines.push(i18n("Feels like %1", Helpers.formatTemp(modelData.temp_feels_like)))
                            var w = modelData.wind || {}
                            if (Helpers.hasValue(w.speed_kilometre)) {
                                var ws = Helpers.windStr(w.speed_kilometre, w.direction)
                                lines.push(w.gust_speed_kilometre
                                    ? i18n("Wind %1 (gusts %2)", ws, Math.round(w.gust_speed_kilometre))
                                    : i18n("Wind %1", ws))
                            }
                            var hd = []
                            if (Helpers.hasValue(modelData.relative_humidity))
                                hd.push(i18n("Humidity %1%", Math.round(modelData.relative_humidity)))
                            if (Helpers.hasValue(modelData.dew_point))
                                hd.push(i18nc("abbreviated dew point", "Dew pt %1",
                                              Helpers.formatTemp(modelData.dew_point)))
                            if (hd.length) lines.push(hd.join("  ·  "))
                            if (modelData.uv)
                                lines.push(i18n("UV %1", modelData.uv))
                            var ra = modelData.rain && modelData.rain.amount
                            if (ra && ra.max)
                                lines.push(i18n("Rain %1–%2 mm", ra.min || 0, ra.max))
                            return lines.join("\n")
                        }
                    }
                }
                PlainLabel {
                    Layout.alignment: Qt.AlignHCenter
                    text: Helpers.formatTemp(modelData.temp)
                    font.weight: Font.DemiBold
                }
                RainChanceLabel {
                    Layout.alignment: Qt.AlignHCenter
                    entry: modelData
                }
            }
        }
    }
}
