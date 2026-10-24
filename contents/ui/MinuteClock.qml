// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick

import "helpers.js" as Helpers

// The time of day to the minute, for everything that depends on it (the
// day/night switch, "Now", staleness), and how to write a clock time on
// the locale's 12- or 24-hour clock.
QtObject {
    id: clock

    // Ticks just past each wall-clock minute.
    property var now: new Date()

    readonly property bool use24Hour:
        Qt.locale().timeFormat(Locale.ShortFormat).toLowerCase().indexOf("ap") < 0

    function timeText(date) {
        return Qt.formatTime(date, Helpers.clockFormat(use24Hour))
    }

    function dateTimeText(date) {
        return Qt.formatDateTime(date, "d MMM " + Helpers.clockFormat(use24Hour))
    }

    // When something done at ms (0: never) happened: the time if today,
    // else the date and time; "" for never.
    function whenText(ms) {
        if (!ms) return ""
        var at = new Date(ms)
        return Helpers.isSameDay(ms, now.getTime()) ? timeText(at) : dateTimeText(at)
    }

    property Timer _tick: Timer {
        interval: Helpers.msToNextMinute(Date.now())
        running: true
        onTriggered: {
            clock.now = new Date()
            interval = Helpers.msToNextMinute(Date.now())
            start()
        }
    }
}
