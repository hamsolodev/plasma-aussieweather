// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick

import "helpers.js" as Helpers
import "radarstations.js" as RadarStations

// The radar loop's frame list for the station on show, fetched through
// radar.py, and only while the radar is on screen (active).
QtObject {
    id: radar

    // The station configured in settings.
    required property string configuredStation
    // Milliseconds between refreshes.
    required property int interval

    // True only while the Radar tab is on screen. It gates all radar network
    // activity: the frame list, the frames and the overlays.
    property bool active: false

    // A station picked in the Radar tab's quick picker. Cleared when the tab
    // is left, reverting to the configured station, the sticky default.
    property string pickedStation: ""

    // The station on show. One not in RadarStations' table (a stale or
    // hand-edited config) falls back to the default rather than reaching a
    // URL.
    readonly property string station: {
        var id = pickedStation !== "" ? pickedStation : configuredStation
        return RadarStations.isKnownId(id) ? id : RadarStations.defaultId
    }

    property var frames: []
    property real lastRefreshMs: 0
    // Why the last refresh failed; "" when it did not.
    property string errorText: ""
    property int _retryCount: 0

    onStationChanged: {
        reset()
        if (active) refresh()
    }
    onActiveChanged: {
        if (!active) {
            pickedStation = ""
            _retry.stop()
        }
    }

    // Forget the station's frames and any failure, so the next fetch starts
    // afresh. Writes only what changes: assigning a var property signals a
    // change even when the value is the same, and the station's first
    // evaluation lands here while views are reading the frames.
    function reset() {
        if (frames.length > 0) frames = []
        lastRefreshMs = 0
        errorText     = ""
        _retryCount   = 0
        _retry.stop()
    }

    function refresh() {
        _lister.run([station])
    }

    // A radar failure, as radar.py or scriptResult reports it, worded for
    // the user.
    function failureText(d) {
        switch (d.error) {
        case "invalid_station": return i18n("Not a radar station: %1", d.detail)
        case "no_frames":       return i18n("No recent radar images. The station may be offline; try a neighbouring one.")
        case "network":         return i18n("Cannot reach BoM's radar listing: %1", d.detail)
        case "script":          return i18n("The radar script failed: %1", d.detail)
        default:                return i18n("Radar update failed: %1", d.detail || d.error)
        }
    }

    function _handle(d) {
        // Drop a listing for a station no longer shown. Output that names no
        // station (it did not parse) can only be taken as this one's.
        if (d.station !== undefined && !Helpers.isRadarFor(d, station))
            return

        if (!d.ok) {
            errorText = failureText(d)
            // While the tab is open, retry with backoff: 30 s doubling to a
            // 5-minute ceiling. Leaving the tab stops it.
            if (!d.permanent && active) {
                _retry.interval = Math.min(30000 * Math.pow(2, _retryCount), 300000)
                _retryCount++
                _retry.restart()
            }
            return
        }

        errorText     = ""
        _retryCount   = 0
        _retry.stop()
        lastRefreshMs = Date.now()
        if (JSON.stringify(d.frames) !== JSON.stringify(frames))
            frames = d.frames
    }

    property ScriptRunner _lister: ScriptRunner {
        script: "radar.py"
        onFinished: (result) => radar._handle(result)
    }

    property Timer _retry: Timer {
        repeat: false
        onTriggered: if (radar.active) radar.refresh()
    }

    // Refreshes when due, like the weather poll, but only while active.
    // Becoming active checks at once; a recent fetch is not repeated, so
    // switching tabs back and forth does not refetch.
    property Timer _due: Timer {
        interval: 30000
        running: radar.active
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            if (Helpers.isDue(radar.lastRefreshMs, Date.now(), radar.interval))
                radar.refresh()
        }
    }
}
