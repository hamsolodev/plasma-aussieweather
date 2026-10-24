// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick

import "helpers.js" as Helpers

// The weather the widget shows, and what follows from it at a given moment:
// today's forecast, the current hourly slot, the icon, whether it is out of
// date. It does no I/O: WeatherSource fills it from BoM, and the tests from
// fixtures.
QtObject {
    id: model

    // The moment the derived properties describe (MinuteClock.now).
    property var now: new Date()
    // Milliseconds between polls; data that has missed two is out of date.
    property int interval: 600000

    // ── As poll.py reports it ─────────────────────────────────────────────
    // Whether a poll has succeeded for this location; the views show nothing
    // but the error or "Waiting" until one has.
    property bool   hasData: false
    // Why the last update failed or was incomplete; "" when it did not.
    property string errorText: ""
    property var    observations: null
    property var    forecast: []
    property var    hourlyForecast: []
    property var    warnings: []
    property string locationName: ""
    property real   lastSuccessMs: 0

    // Forget everything shown, for a new location.
    function clear() {
        hasData        = false
        errorText      = ""
        observations   = null
        forecast       = []
        hourlyForecast = []
        warnings       = []
        lastSuccessMs  = 0
    }

    // ── Derived ───────────────────────────────────────────────────────────
    readonly property real nowMs: now.getTime()

    // The current temperature as the panel shows it; "" before any data.
    readonly property string temperatureText:
        hasData ? Helpers.formatTemp(observations ? observations.temp : null) : ""

    // Data that has missed two polls in a row is out of date.
    readonly property bool isStale: Helpers.isStale(lastSuccessMs, nowMs, interval)

    // The daily forecast from today on (Helpers.todayIndex), at most 7 days,
    // and today's entry, null before the first poll. todayIdx changes once a
    // day, so the strip is not rebuilt every minute.
    readonly property int todayIdx: Helpers.todayIndex(forecast, nowMs)
    readonly property var days: forecast.slice(todayIdx, todayIdx + 7)
    readonly property var today: days.length > 0 ? days[0] : null

    // Today's UV category (Helpers.uvKey), "" when BoM gave none.
    readonly property string todayUvKey:
        today && today.uv ? Helpers.uvKey(today.uv.category) : ""

    // Night by today's sunrise and sunset, to the minute. The hourly is_night
    // flag describes the slot's start, so using it for "now" would move the
    // switch to the hour mark, up to 59 minutes after sunset.
    readonly property bool hasAstro: hasData && today !== null && !!today.astronomical
    readonly property bool isNight: {
        if (!hasAstro) return false
        var sunrise = new Date(today.astronomical.sunrise_time)
        var sunset  = new Date(today.astronomical.sunset_time)
        return now < sunrise || now >= sunset
    }

    // The hour now falls in (Helpers.hourBucket). It changes once an hour,
    // so what depends on it is rebuilt hourly rather than every minute.
    readonly property int currentHour: Helpers.hourBucket(nowMs)
    // The hourly strip: from the current slot on, never past ones.
    readonly property var upcomingHourly:
        Helpers.upcomingSlots(hourlyForecast, currentHour * 3600000).slice(0, 8)
    // The hourly slot now falls in, null without an hourly forecast. Its
    // is_night is hourly-quantised, so slotIsNight prefers sunrise/sunset.
    readonly property var nowSlot: Helpers.currentSlot(hourlyForecast, currentHour * 3600000)
    readonly property bool slotIsNight: hasAstro ? isNight : (!!nowSlot && !!nowSlot.is_night)

    readonly property string currentIcon: {
        if (!hasData || !today)
            return "weather-none-available"
        if (nowSlot)
            return Helpers.bomIcon(Helpers.iconDescriptor(nowSlot), slotIsNight)
        return Helpers.bomIcon(Helpers.iconDescriptor(today), isNight)
    }

    // What it is like now, for the popup and the panel tooltip: the current
    // slot's condition, worded for night after dark ("Clear", not "Sunny").
    // Without an hourly forecast (the external territories), today's text.
    readonly property string summaryText: {
        var descriptor = nowSlot ? Helpers.iconDescriptor(nowSlot) : ""
        if (descriptor)
            return Helpers.titleCase(Helpers.conditionKey(descriptor, slotIsNight))
        if (today !== null)
            return Helpers.titleCase(today.short_text || "").replace(/\.$/, "")
        return ""
    }

    // The warnings still in force (Helpers.unexpired). The list is replaced
    // when new warnings arrive or one expires, not every minute, so the
    // Warnings tab is not rebuilt as the clock ticks.
    property var currentWarnings: []
    onWarningsChanged: currentWarnings = Helpers.unexpired(warnings, nowMs)
    onNowMsChanged: {
        var inForce = Helpers.unexpired(warnings, nowMs)
        if (inForce.length !== currentWarnings.length) currentWarnings = inForce
    }

    readonly property bool hasWarnings: currentWarnings.length > 0
}
