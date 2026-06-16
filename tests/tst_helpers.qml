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

    // ── escapeHtml ────────────────────────────────────────────────────────

    function test_escapeHtml_metachars() {
        compare(Helpers.escapeHtml("a < b & c > d \"e\""),
                "a &lt; b &amp; c &gt; d &quot;e&quot;")
        compare(Helpers.escapeHtml(null), "")
        compare(Helpers.escapeHtml(undefined), "")
    }

    // ── isSafeUrl ─────────────────────────────────────────────────────────

    function test_isSafeUrl_allows_http_https() {
        verify(Helpers.isSafeUrl("http://www.bom.gov.au/x"))
        verify(Helpers.isSafeUrl("https://www.bom.gov.au/x"))
        verify(Helpers.isSafeUrl("HTTPS://WWW.BOM.GOV.AU"))
    }

    function test_isSafeUrl_rejects_other_schemes() {
        verify(!Helpers.isSafeUrl("file:///etc/passwd"))
        verify(!Helpers.isSafeUrl("javascript:alert(1)"))
        verify(!Helpers.isSafeUrl("ftp://x"))
        verify(!Helpers.isSafeUrl(""))
        verify(!Helpers.isSafeUrl(null))
    }

    // ── linkify ───────────────────────────────────────────────────────────

    function test_linkify_plain_text_escaped_only() {
        compare(Helpers.linkify("storms & gusts <severe>"),
                "storms &amp; gusts &lt;severe&gt;")
    }

    function test_linkify_wraps_bare_url() {
        compare(Helpers.linkify("See http://bom.gov.au/x now"),
                'See <a href="http://bom.gov.au/x">http://bom.gov.au/x</a> now')
    }

    function test_linkify_trailing_punctuation_outside_link() {
        compare(Helpers.linkify("More at https://bom.gov.au/x."),
                'More at <a href="https://bom.gov.au/x">https://bom.gov.au/x</a>.')
    }

    function test_linkify_query_ampersand_escaped_in_href() {
        // & inside the URL must be escaped in both href and text, not break it.
        compare(Helpers.linkify("https://bom.gov.au/p?a=1&b=2"),
                '<a href="https://bom.gov.au/p?a=1&amp;b=2">https://bom.gov.au/p?a=1&amp;b=2</a>')
    }

    function test_linkify_no_url() {
        compare(Helpers.linkify("nothing here"), "nothing here")
        compare(Helpers.linkify(null), "")
    }
}
