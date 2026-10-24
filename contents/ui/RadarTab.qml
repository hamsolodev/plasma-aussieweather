// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami

import "radarstations.js" as RadarStations

// The Radar tab: how fresh the loop is, a quick station and range picker,
// the radar itself, and links to BoM's own loop and maps.
ColumnLayout {
    id: tab

    required property RadarSource radar
    required property MinuteClock clock

    spacing: Kirigami.Units.smallSpacing

    // The pickers follow the station on show, both when a pick reverts on
    // leaving the tab and when settings change. The station on show is
    // always one the table offers.
    function syncPickers() {
        var at = RadarStations.locate(radar.station)
        stationPicker.currentIndex = at.station
        rangePicker.currentIndex = at.range
    }
    Component.onCompleted: syncPickers()
    Connections {
        target: tab.radar
        function onStationChanged() { tab.syncPickers() }
    }

    // Equal stretch above and below centres the radar vertically; the
    // buttons stay pinned to the bottom.
    Item { Layout.fillHeight: true }

    // Picks set radar.pickedStation, which is cleared on leaving the tab:
    // the station configured in settings is the sticky default.
    RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin:  Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing

        PlainLabel {
            Layout.fillWidth: true
            elide: Text.ElideRight
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            opacity: 0.7
            text: {
                if (tab.radar.errorText) return i18n("Update failed")
                if (!tab.radar.lastRefreshMs) return i18n("Fetching…")
                var ageSecs = Math.floor((tab.clock.now.getTime() - tab.radar.lastRefreshMs) / 1000)
                if (ageSecs < 60) return i18n("Updated just now")
                return i18np("Updated a minute ago", "Updated %1 minutes ago",
                             Math.floor(ageSecs / 60))
            }
        }

        QQC2.ComboBox {
            id: stationPicker
            Layout.preferredWidth: Kirigami.Units.gridUnit * 8
            model: RadarStations.stations.map(function(s) { return s.name })
            onActivated: tab.radar.pickedStation = RadarStations.idFor(
                currentIndex, RadarStations.parseId(tab.radar.station).km)
        }
        QQC2.ComboBox {
            id: rangePicker
            Layout.preferredWidth: Kirigami.Units.gridUnit * 5
            model: stationPicker.currentIndex >= 0
                ? RadarStations.stations[stationPicker.currentIndex].ranges.map(
                      function(r) { return i18n("%1 km", r) })
                : []
            onActivated: tab.radar.pickedStation = RadarStations.idAt(
                stationPicker.currentIndex, currentIndex)
        }
    }

    RadarView {
        Layout.fillWidth: true
        radar: tab.radar
    }

    PlainLabel {
        visible: tab.radar.errorText !== ""
        Layout.fillWidth: true
        Layout.leftMargin:  Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing
        wrapMode: Text.WordWrap
        color: Kirigami.Theme.neutralTextColor
        text: "⚠  " + tab.radar.errorText
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin:  Kirigami.Units.smallSpacing
        Layout.rightMargin: Kirigami.Units.smallSpacing

        PlainLabel {
            Layout.fillWidth: true
            opacity: 0.55
            text: tab.radar.frames.length > 0
                ? i18np("Radar: %2  ·  %1 frame", "Radar: %2  ·  %1 frames",
                        tab.radar.frames.length, tab.radar.station)
                : tab.radar.errorText
                    ? i18n("Radar: %1", tab.radar.station)
                    : i18n("Radar: %1  ·  Loading…", tab.radar.station)
        }
        PlasmaComponents.Button {
            icon.name: "view-refresh-symbolic"
            onClicked: {
                tab.radar.reset()
                tab.radar.refresh()
            }
        }
    }

    Item { Layout.fillHeight: true }

    RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin:   Kirigami.Units.smallSpacing
        Layout.rightMargin:  Kirigami.Units.smallSpacing
        Layout.bottomMargin: Kirigami.Units.smallSpacing
        spacing: Kirigami.Units.smallSpacing

        PlasmaComponents.Button {
            Layout.fillWidth: true
            icon.name: "internet-web-browser-symbolic"
            text: i18n("Full radar loop")
            onClicked: Qt.openUrlExternally(
                "https://www.bom.gov.au/products/" + tab.radar.station + ".loop.shtml")
        }
        PlasmaComponents.Button {
            Layout.fillWidth: true
            icon.name: "internet-web-browser-symbolic"
            text: i18n("Weather maps")
            onClicked: Qt.openUrlExternally(
                "https://www.bom.gov.au/weather-and-climate/rain-radar-and-weather-maps")
        }
    }
}
