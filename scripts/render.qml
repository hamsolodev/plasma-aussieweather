// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

// The widget's popup in a plain window, fed fixture data, for
// scripts/render.py. `fixtureJson` and `liveRadar` are context properties
// set by the script. The fixture is parsed here so the data are plain JS
// objects and arrays, as JSON.parse makes them from poll.py's output in the
// widget. Without liveRadar the popup counts as closed, so the radar stays
// inactive and fetches nothing.

import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import org.kde.kirigami as Kirigami

import "../contents/ui"

Window {
    id: window

    readonly property var fixture: JSON.parse(fixtureJson)

    // As wide as Plasma makes the popup.
    width: view.Layout.preferredWidth
    height: view.implicitHeight
    visible: true
    color: Kirigami.Theme.backgroundColor

    MinuteClock {
        id: clock
        now: new Date(window.fixture.now)
    }

    WeatherModel {
        id: weather
        now: clock.now
        hasData: true
        errorText: window.fixture.errorText
        observations: window.fixture.observations
        forecast: window.fixture.forecast
        hourlyForecast: window.fixture.hourly
        warnings: window.fixture.warnings
        locationName: window.fixture.locationName
        lastSuccessMs: Date.parse(window.fixture.now) - 4 * 60000
    }

    RadarSource {
        id: radar
        configuredStation: window.fixture.station
        interval: 600000
    }

    FullView {
        id: view
        objectName: "fullView"
        width: window.width
        height: window.height
        weather: weather
        radar: radar
        clock: clock
        expanded: liveRadar
        inPanelPopup: true
    }
}
