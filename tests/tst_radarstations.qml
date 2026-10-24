// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtTest
import "../contents/ui/radarstations.js" as RadarStations

TestCase {
    name: "AussieWeatherRadarStations"

    function test_parseId() {
        compare(RadarStations.parseId("IDR023"), { site: "02", km: 128 })
        compare(RadarStations.parseId("IDR1141"), { site: "114", km: 512 })
        compare(RadarStations.parseId("IDR025"), null)
        compare(RadarStations.parseId("XYZ022"), null)
        compare(RadarStations.parseId(""), null)
        compare(RadarStations.parseId(null), null)
        compare(RadarStations.parseId(7), null)
        compare(RadarStations.parseId({}), null)
        compare(RadarStations.isKnownId(7), false)
    }

    function test_stationId_round_trips() {
        compare(RadarStations.stationId("02", 256), "IDR022")
        compare(RadarStations.stationId("114", 64), "IDR1144")
    }

    function test_isKnownId() {
        verify(RadarStations.isKnownId("IDR022"))
        verify(RadarStations.isKnownId("IDR713"))
        // Wyndham publishes only its 128 km product.
        verify(RadarStations.isKnownId("IDR073"))
        verify(!RadarStations.isKnownId("IDR074"))
        verify(!RadarStations.isKnownId("IDR992"))
        verify(!RadarStations.isKnownId("IDR0x2"))
        verify(!RadarStations.isKnownId("IDR02;x2"))
        verify(!RadarStations.isKnownId(""))
    }

    function test_locate_gives_picker_indices() {
        var at = RadarStations.locate("IDR023")
        compare(RadarStations.stations[at.station].site, "02")
        compare(RadarStations.stations[at.station].ranges[at.range], 128)
        compare(RadarStations.locate("IDR074"), null)
        compare(RadarStations.locate("garbage"), null)
    }

    function test_idAt_is_the_inverse_of_locate() {
        var at = RadarStations.locate("IDR713")
        compare(RadarStations.idAt(at.station, at.range), "IDR713")
    }

    // Switching station keeps the range if the new station offers it,
    // else takes its smallest (most detailed).
    function test_idFor_keeps_the_range_where_offered() {
        var melbourne = RadarStations.locate("IDR022").station
        var wyndham = RadarStations.locate("IDR073").station
        compare(RadarStations.idFor(melbourne, 256), "IDR022")
        compare(RadarStations.idFor(wyndham, 256), "IDR073")
        compare(RadarStations.idFor(melbourne, 999), "IDR024")
    }

    function test_defaultId_is_known() {
        verify(RadarStations.isKnownId(RadarStations.defaultId))
    }
}
