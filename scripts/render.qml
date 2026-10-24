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

    // The fixture's poll goes in as WeatherSource puts a real one in,
    // fetched four minutes before the moment shown.
    WeatherModel {
        id: weather
        now: clock.now
        Component.onCompleted: apply(window.fixture.poll, Date.parse(window.fixture.now) - 4 * 60000)
    }

    RadarSource {
        id: radar
        configuredStation: window.fixture.station
        interval: 600000
    }

    // The panel, beside the popup, as wide as main.qml makes it.
    Window {
        objectName: "panelWindow"
        visible: true
        width: Kirigami.Units.gridUnit * 4
        height: Kirigami.Units.iconSizes.smallMedium + Kirigami.Units.smallSpacing * 2
        color: Kirigami.Theme.backgroundColor

        CompactView {
            anchors.fill: parent
            anchors.leftMargin: Kirigami.Units.smallSpacing
            weather: weather
        }
    }

    // The production wiring, end to end: WeatherSource runs the real
    // poll.py through ScriptRunner. With no location configured, poll.py
    // answers at once, without the network, and the widget should say so.
    WeatherModel {
        id: unconfigured
        objectName: "unconfiguredWeather"
    }
    WeatherSource {
        config: ({ locationSearch: "", lastLocationSearch: "", lastGeohash: "", lastLocationName: "" })
        version: "render"
        interval: 600000
        weather: unconfigured
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
