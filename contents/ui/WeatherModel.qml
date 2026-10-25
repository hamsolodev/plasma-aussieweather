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
    // Whether a poll has succeeded for this location (apply); the views show
    // nothing but the error or "Waiting" until one has.
    property bool   hasData: false
    // Why the last update failed or was incomplete; "" when it did not.
    property string errorText: ""
    property var    observations: null
    property var    forecast: []
    property var    hourlyForecast: []
    property var    warnings: []
    property string locationName: ""
    property real   lastSuccessMs: 0

    // Take in a successful poll (poll.py's output) made at atMs. A lookup
    // brings the place's name. A failed extra (warnings or the hourly
    // forecast: null) keeps what was shown, rather than claim there is none.
    function apply(d, atMs) {
        if (d.locationName) locationName = d.locationName
        observations = d.observations || null
        forecast     = d.forecast || []
        if (Array.isArray(d.warnings)) warnings       = d.warnings
        if (Array.isArray(d.hourly))   hourlyForecast = d.hourly
        lastSuccessMs = atMs
        hasData = true
    }

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
    // Tomorrow's entry, for its sunrise and sunset; null on the last day
    // BoM lists.
    readonly property var tomorrow: days.length > 1 ? days[1] : null

    // Today's UV category (Helpers.uvKey), "" when BoM gave none.
    readonly property string todayUvKey:
        today && today.uv ? Helpers.uvKey(today.uv.category) : ""

    // Night by today's sunrise and sunset, to the minute; without them, by
    // the current slot's is_night flag. That flag describes the slot's
    // start, so it moves the switch to the hour mark, up to 59 minutes after
    // sunset: the sun times come first.
    readonly property bool isNight: {
        var sun = Helpers.sunTimes(today)
        if (sun) return now < sun.sunrise || now >= sun.sunset
        return !!nowSlot && !!nowSlot.is_night
    }

    // The hour now falls in (Helpers.hourBucket). It changes once an hour,
    // so what depends on it is rebuilt hourly rather than every minute.
    readonly property int currentHour: Helpers.hourBucket(nowMs)
    // The hourly strip: from the current slot on, never past ones.
    readonly property var upcomingHourly:
        Helpers.upcomingSlots(hourlyForecast, currentHour * 3600000).slice(0, 8)
    // The hourly slot now falls in, or null (Helpers.currentSlot).
    readonly property var nowSlot: Helpers.currentSlot(hourlyForecast, currentHour * 3600000)

    readonly property string currentIcon:
        today ? Helpers.bomIcon(Helpers.iconDescriptor(nowSlot || today), isNight)
              : "weather-none-available"

    // What it is like now, for the popup and the panel tooltip: the current
    // slot's condition, worded for night after dark ("Clear", not "Sunny").
    // Without an hourly forecast (the external territories), today's text.
    readonly property string summaryText: {
        var descriptor = nowSlot ? Helpers.iconDescriptor(nowSlot) : ""
        if (descriptor)
            return Helpers.titleCase(Helpers.conditionKey(descriptor, isNight))
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
