// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtTest

import "../contents/ui"

TestCase {
    id: testCase
    name: "AussieWeatherModel"

    Component {
        id: modelComponent
        WeatherModel {}
    }

    // Seaford, VIC, in daylight time: local midnight is 13:00Z the day
    // before; sunrise 06:20, sunset 19:42 local.
    function day(date, descriptor) {
        var midnight = Date.parse(date + "T13:00:00Z")
        return {
            date: date + "T13:00:00Z",
            icon_descriptor: descriptor,
            short_text: "Partly cloudy.",
            astronomical: {
                sunrise_time: new Date(midnight + (6 * 60 + 20) * 60000).toISOString(),
                sunset_time:  new Date(midnight + (19 * 60 + 42) * 60000).toISOString()
            }
        }
    }

    function hour(time, descriptor) {
        return { time: time, icon_descriptor: descriptor, is_night: false }
    }

    function model(props) {
        var defaults = {
            hasData: true,
            observations: { temp: 21.4 },
            forecast: [day("2026-10-23", "partly_cloudy"), day("2026-10-24", "rain")],
            hourlyForecast: [hour("2026-10-24T00:00:00Z", "shower"),
                             hour("2026-10-24T01:00:00Z", "sunny")],
            now: new Date("2026-10-24T00:30:00Z")
        }
        for (var key in props) defaults[key] = props[key]
        // Assigned in JS, not passed as initial properties: those cross into
        // C++ and come back as list wrappers, not arrays, where the widget
        // assigns JSON.parse's arrays.
        var m = createTemporaryObject(modelComponent, testCase)
        for (key in defaults) m[key] = defaults[key]
        return m
    }

    // Not test_…_data: QtTest takes a function named so for another test's
    // data, and never runs it.
    function test_temperature_needs_a_poll() {
        compare(model({}).temperatureText, "21°C")
        compare(model({ hasData: false }).temperatureText, "")
    }

    function test_icon_and_summary_come_from_the_current_slot() {
        var m = model({})
        compare(m.currentIcon, "weather-showers")
        compare(m.summaryText, "Shower")
    }

    // 22:00 local is after sunset: a "sunny" slot reads as clear, with the
    // night icon, even though the slot itself is not flagged as night.
    function test_night_after_sunset() {
        var m = model({ hourlyForecast: [hour("2026-10-24T11:00:00Z", "sunny")],
                        now: new Date("2026-10-24T11:10:00Z") })
        verify(m.isNight)
        compare(m.currentIcon, "weather-clear-night")
        compare(m.summaryText, "Clear")
    }

    // While polls fail the hourly list ages. A slot hours old is not "now":
    // today's forecast speaks instead.
    function test_an_old_slot_is_not_now() {
        var m = model({ now: new Date("2026-10-24T05:30:00Z") })
        compare(m.nowSlot, null)
        compare(m.currentIcon, "weather-few-clouds")
        compare(m.summaryText, "Partly Cloudy")
    }

    function test_upcoming_hours_drop_past_slots() {
        var m = model({ now: new Date("2026-10-24T01:20:00Z") })
        compare(m.upcomingHourly.length, 1)
        compare(m.upcomingHourly[0].time, "2026-10-24T01:00:00Z")
    }

    // Just after local midnight BoM can still list the day that ended.
    function test_today_skips_the_day_that_ended() {
        var m = model({ now: new Date("2026-10-24T13:05:00Z") })
        compare(m.today.date, "2026-10-24T13:00:00Z")
        compare(m.days.length, 1)
    }

    function test_stale_after_two_missed_polls() {
        var now = Date.parse("2026-10-24T00:30:00Z")
        var tenMinutes = 600000
        verify(!model({ interval: tenMinutes, lastSuccessMs: now - 15 * 60000 }).isStale)
        verify(model({ interval: tenMinutes, lastSuccessMs: now - 25 * 60000 }).isStale)
    }

    // Warnings kept through a failed fetch must still expire.
    function test_expired_warnings_are_dropped() {
        var m = model({ warnings: [
            { title: "Gone", expiry_time: "2026-10-24T00:20:00Z" },
            { title: "In force", expiry_time: "2026-10-24T05:00:00Z" },
            { title: "No expiry" }
        ] })
        compare(m.currentWarnings.map(function(w) { return w.title }), ["In force", "No expiry"])
        verify(m.hasWarnings)
        m.now = new Date("2026-10-24T06:00:00Z")
        compare(m.currentWarnings.map(function(w) { return w.title }), ["No expiry"])
    }

    // ── apply: a successful poll ───────────────────────────────────────────

    function test_apply_takes_in_a_poll() {
        var m = model({ hasData: false })
        m.apply({ ok: true, locationName: "Kimba, SA", observations: { temp: 30 },
                  forecast: [day("2026-10-23", "sunny")], hourly: [], warnings: [] },
                Date.parse("2026-10-24T00:30:00Z"))
        verify(m.hasData)
        compare(m.locationName, "Kimba, SA")
        compare(m.temperatureText, "30°C")
        compare(m.lastSuccessMs, Date.parse("2026-10-24T00:30:00Z"))
    }

    // poll.py reports a failed extra as null: keep what was shown rather
    // than claim there are no warnings or no hourly forecast.
    function test_apply_keeps_extras_that_failed() {
        var m = model({ warnings: [{ title: "In force", expiry_time: "2026-10-24T05:00:00Z" }] })
        m.apply({ ok: true, observations: { temp: 19 }, forecast: m.forecast,
                  hourly: null, warnings: null }, Date.parse("2026-10-24T00:31:00Z"))
        compare(m.currentWarnings.length, 1)
        compare(m.hourlyForecast.length, 2)
        compare(m.temperatureText, "19°C")
    }

    function test_apply_without_a_lookup_keeps_the_name() {
        var m = model({ locationName: "Seaford, VIC" })
        m.apply({ ok: true, observations: {}, forecast: [], hourly: [], warnings: [] }, 0)
        compare(m.locationName, "Seaford, VIC")
    }

    // Without sunrise and sunset, night falls back to the slot's own flag.
    function test_night_without_astronomical_times() {
        var night = hour("2026-10-24T11:00:00Z", "sunny")
        night.is_night = true
        var m = model({ forecast: [{ date: "2026-10-23T13:00:00Z", icon_descriptor: "sunny" }],
                        hourlyForecast: [night], now: new Date("2026-10-24T11:10:00Z") })
        verify(m.isNight)
        compare(m.currentIcon, "weather-clear-night")
    }

    function test_no_warnings() {
        verify(!model({ warnings: [] }).hasWarnings)
        verify(!model({ warnings: [{ title: "Gone", expiry_time: "2026-10-24T00:00:00Z" }] }).hasWarnings)
    }
}
