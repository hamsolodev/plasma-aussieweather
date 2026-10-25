// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami

import "helpers.js" as Helpers

// Today's UV (a moon at night, when UV is nil), sunrise and sunset (with
// tomorrow's on hover), and the moon's phase.
RowLayout {
    id: row

    required property WeatherModel weather
    required property MinuteClock clock

    spacing: Kirigami.Units.smallSpacing

    // At night UV is always 0, so a moon shows instead; the sun icon and
    // UV reading return at sunrise (isNight follows the clock).
    PlainLabel {
        visible: row.weather.isNight
        text: "🌛"
    }
    // Shown only for a category BoM actually gave: later days carry a uv
    // object whose fields are all null.
    Kirigami.Icon {
        visible: !row.weather.isNight && row.weather.todayUvKey !== ""
        Layout.preferredWidth:  Kirigami.Units.iconSizes.small
        Layout.preferredHeight: Kirigami.Units.iconSizes.small
        source: "weather-clear-symbolic"
    }
    ToneLabel {
        visible: !row.weather.isNight && row.weather.todayUvKey !== ""
        font.weight: Font.DemiBold
        tone: Helpers.uvTone(row.weather.todayUvKey)
        text: {
            if (row.weather.todayUvKey === "") return ""
            var label = {
                low:      i18nc("UV index category", "Low"),
                moderate: i18nc("UV index category", "Moderate"),
                high:     i18nc("UV index category", "High"),
                veryhigh: i18nc("UV index category", "Very High"),
                extreme:  i18nc("UV index category", "Extreme")
            }[row.weather.todayUvKey] || ""
            var idx = row.weather.today.uv.max_index
            return label + (Helpers.hasValue(idx) ? "  " + idx : "")
        }
    }

    Item { Layout.fillWidth: true }

    PlainLabel {
        visible: row.weather.today !== null && !!row.weather.today.astronomical
        opacity: 0.65
        text: {
            if (!row.weather.today || !row.weather.today.astronomical) return ""
            var a = row.weather.today.astronomical
            return "🌅 " + row.clock.timeText(new Date(a.sunrise_time))
                   + "  ·  🌇 " + row.clock.timeText(new Date(a.sunset_time))
        }

        // After sunset, the next sunrise is tomorrow's: hovering today's
        // times shows tomorrow's.
        HoverHandler { id: sunHover }
        PlasmaComponents.ToolTip {
            visible: sunHover.hovered && text !== ""
            textFormat: Text.PlainText
            delay: Kirigami.Units.toolTipDelay
            text: {
                var t = row.weather.tomorrow
                if (!t || !t.astronomical) return ""
                return i18nc("%1 and %2 are tomorrow's sunrise and sunset times",
                             "Tomorrow: sunrise %1, sunset %2",
                             row.clock.timeText(new Date(t.astronomical.sunrise_time)),
                             row.clock.timeText(new Date(t.astronomical.sunset_time)))
            }
        }
    }

    Item { Layout.fillWidth: true }

    PlainLabel {
        text: {
            var mp = Helpers.moonPhase(row.clock.now)
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
