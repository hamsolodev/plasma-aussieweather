// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtTest
import "../contents/ui/places.js" as Places
import "../contents/ui/radarstations.js" as RadarStations

TestCase {
    name: "AussieWeatherPlaces"

    function entry(search, radar) {
        return JSON.stringify({ search: search, radar: radar })
    }

    function test_a_config_from_before_saved_places_has_its_one_place() {
        var expected = [{ search: "Seaford VIC", radar: "IDR023" }]
        compare(Places.fromConfig([], "Seaford VIC", "IDR023"), expected)
        compare(Places.fromConfig(undefined, "Seaford VIC", "IDR023"), expected)
    }

    function test_saved_places_keep_their_order() {
        var places = Places.fromConfig([entry("Seaford VIC", "IDR023"), entry("Frankston VIC", "IDR022")],
                                       "Frankston VIC", "IDR022")
        compare(places, [{ search: "Seaford VIC", radar: "IDR023" },
                         { search: "Frankston VIC", radar: "IDR022" }])
    }

    function test_the_place_on_show_is_always_offered() {
        // Set by an older version, or by hand: it goes first.
        var places = Places.fromConfig([entry("Frankston VIC", "IDR022")], "Seaford VIC", "IDR023")
        compare(places[0], { search: "Seaford VIC", radar: "IDR023" })
        compare(places.length, 2)
    }

    function test_the_place_on_show_has_the_radar_on_show() {
        var places = Places.fromConfig([entry("Seaford VIC", "IDR022")], "Seaford VIC", "IDR023")
        compare(places, [{ search: "Seaford VIC", radar: "IDR023" }])
    }

    function test_entries_that_make_no_sense_are_skipped() {
        var places = Places.fromConfig(["not json", "{}", entry("", "IDR023"), entry("   ", "IDR023"),
                                        JSON.stringify({ search: 3, radar: "IDR023" }), "[1]", "null",
                                        entry("Sydney NSW", "IDR713")],
                                       "", "IDR022")
        compare(places, [{ search: "Sydney NSW", radar: "IDR713" }])
    }

    function test_an_unknown_radar_station_becomes_the_default() {
        var places = Places.fromConfig([entry("Sydney NSW", "IDR999"), entry("Perth WA", 7)], "", "")
        compare(places, [{ search: "Sydney NSW", radar: RadarStations.defaultId },
                         { search: "Perth WA", radar: RadarStations.defaultId }])
    }

    function test_searches_are_trimmed() {
        compare(Places.fromConfig([entry("  Sydney NSW ", "IDR713")], "", ""),
                [{ search: "Sydney NSW", radar: "IDR713" }])
    }

    function test_the_same_place_twice_is_kept_once() {
        var places = Places.fromConfig([entry("Sydney NSW", "IDR713"), entry("sydney  nsw", "IDR714")],
                                       "", "")
        compare(places, [{ search: "Sydney NSW", radar: "IDR713" }])
    }

    function test_no_place_at_all() {
        compare(Places.fromConfig([], "", "IDR022"), [])
        compare(Places.fromConfig([], "   ", "IDR022"), [])
    }

    function test_the_config_round_trips() {
        var places = [{ search: "Seaford VIC", radar: "IDR023" }, { search: "Perth WA", radar: "IDR703" }]
        compare(Places.fromConfig(Places.toConfig(places), "Seaford VIC", "IDR023"), places)
    }

    function test_blank_places_are_not_saved() {
        compare(Places.toConfig([{ search: "Seaford VIC", radar: "IDR023" }, { search: " ", radar: "IDR023" }]),
                [entry("Seaford VIC", "IDR023")])
    }

    function test_any_name_is_a_place() {
        // Names an object has already: a plain object as the set of names
        // seen would take them for seen.
        var places = Places.fromConfig([entry("constructor", "IDR023"), entry("__proto__", "IDR023"),
                                        entry("toString", "IDR023")], "", "")
        compare(places.map(function(p) { return p.search }), ["constructor", "__proto__", "toString"])
    }

    function test_a_place_listed_twice_is_saved_once() {
        compare(Places.toConfig([{ search: "Seaford VIC", radar: "IDR023" },
                                 { search: "seaford  vic", radar: "IDR024" }]),
                [entry("Seaford VIC", "IDR023")])
    }

    function test_indexOf_ignores_case_and_spacing() {
        var places = [{ search: "Seaford VIC", radar: "IDR023" }, { search: "Perth WA", radar: "IDR703" }]
        compare(Places.indexOf(places, "Perth WA"), 1)
        compare(Places.indexOf(places, " seaford   vic "), 0)
        compare(Places.indexOf(places, "Hobart TAS"), -1)
        compare(Places.indexOf(places, ""), -1)
    }
}
