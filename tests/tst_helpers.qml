// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtTest
import "../contents/ui/helpers.js" as Helpers

TestCase {
    name: "AussieWeatherHelpers"

    // ── hasValue ──────────────────────────────────────────────────────────

    // BoM sends null for a reading a station did not take; 0 is a reading.
    function test_hasValue() {
        verify(Helpers.hasValue(0))
        verify(Helpers.hasValue(98))
        verify(Helpers.hasValue(""))
        verify(!Helpers.hasValue(null))
        verify(!Helpers.hasValue(undefined))
    }

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

    // ── forecastWeekday / titleCase ───────────────────────────────────────

    // BoM dates a daily forecast by the location's local midnight, in UTC.
    // Each of these is Saturday 24 October 2026 where it is forecast for.
    function test_forecastWeekday_is_the_locations_day() {
        compare(Helpers.forecastWeekday("2026-10-23T13:00:00Z"), 6)   // VIC, daylight time
        compare(Helpers.forecastWeekday("2026-10-23T13:30:00Z"), 6)   // SA, daylight time
        compare(Helpers.forecastWeekday("2026-10-23T14:00:00Z"), 6)   // QLD
        compare(Helpers.forecastWeekday("2026-10-23T16:00:00Z"), 6)   // WA
        compare(Helpers.forecastWeekday("2026-10-23T17:00:00Z"), 6)   // Christmas Island
        compare(Helpers.forecastWeekday("2026-10-23T17:30:00Z"), 6)   // Cocos Islands
        compare(Helpers.forecastWeekday("2026-10-23T12:00:00Z"), 6)   // Norfolk, daylight time
    }

    function test_forecastWeekday_invalid() {
        compare(Helpers.forecastWeekday(null), -1)
        compare(Helpers.forecastWeekday("garbage"), -1)
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

    // ── uvKey ─────────────────────────────────────────────────────────────

    // BoM sends "veryhigh"; tolerate the spellings a person would write.
    function test_uvKey_normalises_bom_categories() {
        compare(Helpers.uvKey("veryhigh"), "veryhigh")
        compare(Helpers.uvKey("very_high"), "veryhigh")
        compare(Helpers.uvKey("Very High"), "veryhigh")
        compare(Helpers.uvKey("extreme"), "extreme")
        compare(Helpers.uvKey("LOW"), "low")
    }

    function test_uvKey_unknown_is_empty() {
        compare(Helpers.uvKey(null), "")
        compare(Helpers.uvKey(""), "")
        compare(Helpers.uvKey("scorching"), "")
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

    // ── isSafeUrl ─────────────────────────────────────────────────────────

    function test_isSafeUrl_allows_https() {
        verify(Helpers.isSafeUrl("https://www.bom.gov.au/x"))
        verify(Helpers.isSafeUrl("HTTPS://WWW.BOM.GOV.AU"))
    }

    function test_isSafeUrl_rejects_other_schemes() {
        verify(!Helpers.isSafeUrl("http://www.bom.gov.au/x"))
        verify(!Helpers.isSafeUrl("file:///etc/passwd"))
        verify(!Helpers.isSafeUrl("javascript:alert(1)"))
        verify(!Helpers.isSafeUrl("ftp://x"))
        verify(!Helpers.isSafeUrl(""))
        verify(!Helpers.isSafeUrl(null))
    }

    // ── shellQuote / localPath ────────────────────────────────────────────

    function test_shellQuote_escapes_what_double_quotes_leave_special() {
        compare(Helpers.shellQuote("Seaford VIC"), '"Seaford VIC"')
        compare(Helpers.shellQuote('a"b'), '"a\\"b"')
        compare(Helpers.shellQuote("$(id)`id`"), '"\\$(id)\\`id\\`"')
        compare(Helpers.shellQuote("back\\slash"), '"back\\\\slash"')
        compare(Helpers.shellQuote("it's"), "\"it's\"")
        compare(Helpers.shellQuote(""), '""')
        compare(Helpers.shellQuote(null), '""')
    }

    function test_localPath_decodes_file_url() {
        compare(Helpers.localPath("file:///usr/share/x/poll.py"), "/usr/share/x/poll.py")
        compare(Helpers.localPath("file:///home/u/my%20widgets/poll.py"),
                "/home/u/my widgets/poll.py")
    }

    // ── isStale / isSameDay ───────────────────────────────────────────────

    function test_isStale_after_two_missed_polls() {
        var interval = 600000
        var last = Date.UTC(2026, 9, 24, 0, 0)
        verify(!Helpers.isStale(last, last + 2 * interval, interval))
        verify(Helpers.isStale(last, last + 2 * interval + 1, interval))
    }

    function test_isStale_not_before_the_first_poll() {
        verify(!Helpers.isStale(0, Date.UTC(2026, 9, 24), 600000))
    }

    function test_isSameDay_uses_the_local_calendar() {
        var morning = new Date(2026, 9, 24, 0, 5).getTime()
        var night = new Date(2026, 9, 24, 23, 55).getTime()
        var next = new Date(2026, 9, 25, 0, 5).getTime()
        verify(Helpers.isSameDay(morning, night))
        verify(!Helpers.isSameDay(night, next))
    }

    // ── scriptResult ──────────────────────────────────────────────────────

    function test_scriptResult_parses_the_printed_object() {
        compare(Helpers.scriptResult({ "stdout": '{"ok": true, "x": 1}\n', "exit code": 0 }),
                { ok: true, x: 1 })
    }

    function test_scriptResult_reports_a_script_that_printed_nothing() {
        compare(Helpers.scriptResult({ "stdout": "", "stderr": "sh: line 1: python3: command not found\n",
                                       "exit code": 127 }),
                { ok: false, error: "script", detail: "sh: line 1: python3: command not found" })
        compare(Helpers.scriptResult({ "stdout": "Traceback", "stderr": "", "exit code": 1 }),
                { ok: false, error: "script", detail: "exit code 1" })
        compare(Helpers.scriptResult({ "stdout": "[1]", "exit code": 0 }).error, "script")
    }

    // ── isPollFor / isRadarFor ────────────────────────────────────────────

    function test_isPollFor_matches_the_current_request() {
        verify(Helpers.isPollFor({ query: "Kimba SA", geohash: "r4152n" }, "Kimba SA", "r4152n"))
        verify(Helpers.isPollFor({ query: "Kimba SA", geohash: "" }, "Kimba SA", ""))
    }

    function test_isPollFor_rejects_an_overtaken_request() {
        // The location changed while a lookup was in flight.
        verify(!Helpers.isPollFor({ query: "Seaford VIC", geohash: "" }, "Kimba SA", ""))
        // A poll of the old cached place, after the cache was reset.
        verify(!Helpers.isPollFor({ query: "Kimba SA", geohash: "r1ppnx" }, "Kimba SA", ""))
        verify(!Helpers.isPollFor(undefined, "Kimba SA", ""))
    }

    function test_isRadarFor() {
        verify(Helpers.isRadarFor({ station: "IDR022" }, "IDR022"))
        verify(!Helpers.isRadarFor({ station: "IDR023" }, "IDR022"))
        verify(!Helpers.isRadarFor({}, "IDR022"))
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
