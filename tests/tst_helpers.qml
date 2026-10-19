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
        compare(Helpers.bomIcon("cyclone", false), "weather-many-clouds-wind")
    }

    // Every descriptor the BoM v1 API is known to emit must map to something
    // other than the fallback — "windy" reaching weather-none-available is the
    // bug this guards against.
    function test_bomIcon_covers_every_bom_descriptor() {
        var descriptors = [
            "sunny", "clear", "mostly_sunny", "partly_cloudy", "cloudy",
            "hazy", "dusty", "fog", "frost", "light_shower", "shower",
            "heavy_shower", "light_rain", "rain", "storm", "snow", "windy",
            "cyclone", "tropical_cyclone"
        ]
        for (var i = 0; i < descriptors.length; ++i) {
            verify(Helpers.bomIcon(descriptors[i], false) !== "weather-none-available",
                   "day icon missing for descriptor: " + descriptors[i])
            verify(Helpers.bomIcon(descriptors[i], true) !== "weather-none-available",
                   "night icon missing for descriptor: " + descriptors[i])
        }
    }

    function test_bomIcon_night_overrides() {
        compare(Helpers.bomIcon("sunny", true), "weather-clear-night")
        compare(Helpers.bomIcon("partly_cloudy", true), "weather-few-clouds-night")
        compare(Helpers.bomIcon("light_shower", true), "weather-showers-scattered-night")
        compare(Helpers.bomIcon("thunderstorm", true), "weather-storm-night")
        compare(Helpers.bomIcon("windy", true), "weather-clear-wind-night")
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

    // ── looksLikeHtml / warningHtml ───────────────────────────────────────

    function test_looksLikeHtml() {
        verify(Helpers.looksLikeHtml('<div class="product"><p>x</p></div>'))
        verify(Helpers.looksLikeHtml("text with <a href=\"http://x\">link</a>"))
        verify(!Helpers.looksLikeHtml("Strong wind warning for Port Phillip."))
        verify(!Helpers.looksLikeHtml("see http://bom.gov.au/x"))
        verify(!Helpers.looksLikeHtml(""))
    }

    function test_warningHtml_passes_html_through() {
        // Real HTML product must NOT be escaped (so it renders, not shows tags)
        var html = '<div class="product"><p>IDV20600</p><a href="http://bom.gov.au/x">map</a></div>'
        compare(Helpers.warningHtml(html), html)
    }

    function test_warningHtml_linkifies_plain_text() {
        compare(Helpers.warningHtml("See http://bom.gov.au/x now"),
                'See <a href="http://bom.gov.au/x">http://bom.gov.au/x</a> now')
        compare(Helpers.warningHtml("plain & simple"), "plain &amp; simple")
    }

    // ── nextLoadedFrame (radar loop) ──────────────────────────────────────

    // Frames as the radar tab sees them: true where the Image has loaded.
    function readyAt(frames) {
        return function(i) { return frames[i] === true }
    }

    function test_nextLoadedFrame_steps_through_loaded_frames() {
        var all = readyAt([true, true, true])
        compare(Helpers.nextLoadedFrame(0, 3, all), 1)
        compare(Helpers.nextLoadedFrame(1, 3, all), 2)
        compare(Helpers.nextLoadedFrame(2, 3, all), 0)
    }

    // The first loop on a slow connection: frames still loading are skipped,
    // never shown blank.
    function test_nextLoadedFrame_skips_frames_not_loaded() {
        var some = readyAt([false, true, false, false, true, false])
        compare(Helpers.nextLoadedFrame(1, 6, some), 4)
        compare(Helpers.nextLoadedFrame(4, 6, some), 1)
        // From a frame not yet loaded (where a new set starts), to the next
        // loaded one.
        compare(Helpers.nextLoadedFrame(0, 6, some), 1)
        compare(Helpers.nextLoadedFrame(5, 6, some), 1)
    }

    function test_nextLoadedFrame_holds_when_nothing_else_has_loaded() {
        compare(Helpers.nextLoadedFrame(2, 4, readyAt([false, false, true, false])), 2)
        compare(Helpers.nextLoadedFrame(0, 4, readyAt([false, false, false, false])), 0)
    }

    function test_nextLoadedFrame_no_frames() {
        compare(Helpers.nextLoadedFrame(0, 0, readyAt([])), 0)
    }
}
