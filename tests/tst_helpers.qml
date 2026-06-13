// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtTest
import "../contents/ui/helpers.js" as Helpers

TestCase {
    name: "AussieWeatherHelpers"

    // ── formatTemp ────────────────────────────────────────────────────────

    function test_formatTemp_rounds() {
        compare(Helpers.formatTemp(17.4), "17°C")
        compare(Helpers.formatTemp(17.5), "18°C")
        compare(Helpers.formatTemp(-2.6), "-3°C")
        compare(Helpers.formatTemp(0), "0°C")
    }

    function test_formatTemp_invalid() {
        compare(Helpers.formatTemp(null), "—")
        compare(Helpers.formatTemp(undefined), "—")
        compare(Helpers.formatTemp("not a number"), "—")
    }

    // ── bomIcon ───────────────────────────────────────────────────────────

    function test_bomIcon_day() {
        compare(Helpers.bomIcon("sunny", false), "weather-clear")
        compare(Helpers.bomIcon("mostly_sunny", false), "weather-clear")
        compare(Helpers.bomIcon("shower", false), "weather-showers")
        compare(Helpers.bomIcon("thunderstorm", false), "weather-storm")
        compare(Helpers.bomIcon("cyclone", false), "weather-severe-alert")
    }

    function test_bomIcon_night_overrides() {
        compare(Helpers.bomIcon("sunny", true), "weather-clear-night")
        compare(Helpers.bomIcon("partly_cloudy", true), "weather-few-clouds-night")
        compare(Helpers.bomIcon("light_shower", true), "weather-showers-scattered-night")
        compare(Helpers.bomIcon("thunderstorm", true), "weather-storm-night")
    }

    function test_bomIcon_night_without_override_keeps_day_icon() {
        compare(Helpers.bomIcon("overcast", true), "weather-overcast")
        compare(Helpers.bomIcon("fog", true), "weather-fog")
    }

    function test_bomIcon_unknown_descriptor() {
        compare(Helpers.bomIcon("volcano", false), "weather-none-available")
        compare(Helpers.bomIcon("", false), "weather-none-available")
        compare(Helpers.bomIcon(null, true), "weather-none-available")
    }

    function test_bomIcon_case_insensitive() {
        compare(Helpers.bomIcon("Sunny", false), "weather-clear")
        compare(Helpers.bomIcon("THUNDERSTORM", false), "weather-storm")
    }

    // ── windStr ───────────────────────────────────────────────────────────

    function test_windStr_with_direction() {
        compare(Helpers.windStr(31.4, "NNE"), "NNE 31 km/h")
    }

    function test_windStr_without_direction() {
        compare(Helpers.windStr(15, null), "15 km/h")
        compare(Helpers.windStr(15, ""), "15 km/h")
    }

    function test_windStr_missing_speed() {
        compare(Helpers.windStr(null, "N"), "—")
        compare(Helpers.windStr(undefined, "N"), "—")
    }

    // ── pressureStr ───────────────────────────────────────────────────────

    function test_pressureStr_tendency_arrows() {
        compare(Helpers.pressureStr(1013.2, "rising"), "1013 hPa ↑")
        compare(Helpers.pressureStr(1013.2, "falling"), "1013 hPa ↓")
        compare(Helpers.pressureStr(1013.2, "steady"), "1013 hPa →")
        compare(Helpers.pressureStr(1013.2, "rising_slowly"), "1013 hPa ↗")
    }

    function test_pressureStr_no_tendency() {
        compare(Helpers.pressureStr(998.6, null), "999 hPa")
        compare(Helpers.pressureStr(998.6, "unknown"), "999 hPa")
    }

    function test_pressureStr_invalid() {
        compare(Helpers.pressureStr(null, "rising"), "—")
    }

    // ── shortDay / titleCase ──────────────────────────────────────────────

    function test_shortDay() {
        compare(Helpers.shortDay("2026-06-13"), "Sat")
        compare(Helpers.shortDay(null), "—")
        compare(Helpers.shortDay("garbage"), "—")
    }

    function test_titleCase() {
        compare(Helpers.titleCase("partly_cloudy"), "Partly Cloudy")
        compare(Helpers.titleCase("rain increasing."), "Rain Increasing.")
        compare(Helpers.titleCase(null), "")
    }

    // ── colour keys ───────────────────────────────────────────────────────

    function test_tempColorKey() {
        compare(Helpers.tempColorKey(36), "hot")
        compare(Helpers.tempColorKey(35), "hot")
        compare(Helpers.tempColorKey(30), "warm")
        compare(Helpers.tempColorKey(20), "normal")
        compare(Helpers.tempColorKey(null), "normal")
    }

    function test_rainColorKey() {
        compare(Helpers.rainColorKey(80), "heavy")
        compare(Helpers.rainColorKey(70), "heavy")
        compare(Helpers.rainColorKey(50), "moderate")
        compare(Helpers.rainColorKey(20), "low")
        compare(Helpers.rainColorKey(5), "none")
        compare(Helpers.rainColorKey(null), "none")
    }

    // ── moonPhase ─────────────────────────────────────────────────────────

    function test_moonPhase_known_new_moon() {
        // Reference epoch itself
        compare(Helpers.moonPhase(new Date("2000-01-06T18:14:00Z")).name, "New Moon")
        // One synodic month later
        compare(Helpers.moonPhase(new Date("2000-02-05T07:00:00Z")).name, "New Moon")
    }

    function test_moonPhase_known_full_moon() {
        // 2000-01-21 04:40 UTC was a full moon (and a lunar eclipse)
        compare(Helpers.moonPhase(new Date("2000-01-21T04:40:00Z")).name, "Full Moon")
    }

    function test_moonPhase_quarters() {
        compare(Helpers.moonPhase(new Date("2000-01-14T13:34:00Z")).name, "First Quarter")
        compare(Helpers.moonPhase(new Date("2000-01-28T07:57:00Z")).name, "Last Quarter")
    }

    function test_moonPhase_dates_before_epoch() {
        // Negative day deltas must still land in [0, synodicMonth)
        var mp = Helpers.moonPhase(new Date("1999-12-07T22:32:00Z"))  // new moon Dec 1999
        compare(mp.name, "New Moon")
    }
}
