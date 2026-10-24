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

    function test_defaultId_is_known() {
        verify(RadarStations.isKnownId(RadarStations.defaultId))
    }
}
