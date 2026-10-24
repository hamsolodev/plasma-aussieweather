// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick

import "helpers.js" as Helpers

// Keeps a WeatherModel filled from BoM: polls through poll.py when due,
// retries a failure with backoff, starts afresh when the location changes,
// and caches the location lookup in the config so a restart needs none.
QtObject {
    id: source

    // The plasmoid's configuration. locationSearch is read; the lookup cache
    // (lastGeohash, lastLocationName, lastLocationSearch) is read and written.
    required property var config
    // The package version, which identifies the widget in its User-Agent.
    required property string version
    // Milliseconds between polls.
    required property int interval
    required property WeatherModel weather

    readonly property string locationSearch: config.locationSearch

    // A transient failure is retried after 5 s, doubling, six times (about
    // 5 minutes in all); then the regular polls take over.
    readonly property int retryBaseMs: 5000
    readonly property int retryCapMs: 160000
    readonly property int maxRetries: 6
    // How often to check whether a poll is due (Helpers.isDue).
    readonly property int dueCheckMs: 30000

    property string _geohash: ""
    property real _lastPollMs: 0
    property int _retryCount: 0

    // Start from the last successful lookup so the widget works across
    // restarts without waiting for a fresh one, but only if that lookup was
    // for the location still configured (it may have been edited since;
    // an empty one matches the cache's empty default). Then poll.
    Component.onCompleted: {
        weather.locationName = locationSearch
        if (locationSearch !== "" && config.lastLocationSearch === locationSearch) {
            if (config.lastGeohash) _geohash = config.lastGeohash
            if (config.lastLocationName) weather.locationName = config.lastLocationName
        }
        _due.start()
    }

    onLocationSearchChanged: {
        _geohash = ""
        config.lastGeohash        = ""
        config.lastLocationName   = ""
        config.lastLocationSearch = ""
        weather.clear()
        weather.locationName = locationSearch
        _retryCount = 0
        _retry.stop()
        refresh()
    }

    function refresh() {
        _lastPollMs = Date.now()
        _poller.run([version, _geohash, locationSearch])
    }

    // A failure, as poll.py or scriptResult reports it, worded for the user.
    function failureText(d) {
        switch (d.error) {
        case "no_location":  return i18n("No location set. Choose one in the widget's settings.")
        case "not_found":    return i18n("Location not found: %1", d.detail)
        case "http":         return i18n("BoM returned an error: %1", d.detail)
        case "network":      return i18n("Cannot reach BoM: %1", d.detail)
        case "bad_response": return i18n("Unexpected response from BoM: %1", d.detail)
        case "script":       return i18n("The weather script failed: %1", d.detail)
        default:             return i18n("Update failed: %1", d.detail || d.error)
        }
    }

    function _handlePoll(d) {
        // Drop an answer for a location no longer shown. Output that names no
        // request (it did not parse) can only be taken as this one's.
        if (d.request !== undefined && !Helpers.isPollFor(d.request, locationSearch, _geohash))
            return

        if (!d.ok) {
            // The last good data stays on show, with the error beside it.
            // Transient failures (e.g. DNS not yet up after a wake) are
            // retried; definitive answers (permanent: location not found)
            // are not.
            weather.errorText = failureText(d)
            if (!d.permanent && _retryCount < maxRetries) {
                _retry.interval = Helpers.backoffMs(_retryCount, retryBaseMs, retryCapMs)
                _retryCount++
                _retry.restart()
            }
            return
        }

        _retryCount = 0
        _retry.stop()

        if (d.locationName) {
            _geohash = d.geohash
            config.lastGeohash        = d.geohash
            config.lastLocationName   = d.locationName
            config.lastLocationSearch = d.request.query
        }
        weather.apply(d, Date.now())
        // An extra that failed keeps what was shown (apply); say why.
        var partial = []
        if (d.warningsError)
            partial.push(i18n("Warnings could not be updated: %1", d.warningsError))
        if (d.hourlyError)
            partial.push(i18n("The hourly forecast could not be updated: %1", d.hourlyError))
        if (d.imagesError)
            partial.push(i18n("Warning maps cannot be shown: %1", d.imagesError))
        weather.errorText = partial.join("\n")
    }

    property ScriptRunner _poller: ScriptRunner {
        script: "poll.py"
        onFinished: (result) => source._handlePoll(result)
    }

    property Timer _retry: Timer {
        repeat: false
        onTriggered: source.refresh()
    }

    // Polls when due by wall-clock time (Helpers.isDue), checked every 30 s:
    // that covers the regular interval and a wake from sleep, which Qt
    // timers do not count. The check at start polls at once.
    property Timer _due: Timer {
        interval: source.dueCheckMs
        repeat: true
        triggeredOnStart: true
        onTriggered: {
            if (Helpers.isDue(source._lastPollMs, Date.now(), source.interval))
                source.refresh()
        }
    }
}
