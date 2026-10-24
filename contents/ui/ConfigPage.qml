// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

import "radarstations.js" as RadarStations

Kirigami.FormLayout {
    id: page
    Layout.margins: Kirigami.Units.largeSpacing

    property alias cfg_locationSearch: locationField.text
    property string cfg_radarStation
    property int    cfg_pollInterval:  plasmoid.configuration.pollInterval

    // Plasma passes the page a title and a cfg_ property for every config
    // key, and logs a warning for each one the page doesn't declare. These
    // keys are the widget's own lookup cache, not settings: the page only
    // hands them back unchanged on Apply (the cache is keyed by
    // lastLocationSearch, so writing back an old lookup is harmless).
    property string title
    property string cfg_lastGeohash
    property string cfg_lastLocationName
    property string cfg_lastLocationSearch

    // Show and store one product ID: the pickers follow it, so a station
    // change can keep the range (the range model rebinds and resets).
    function select(id) {
        var at = RadarStations.locate(id)
        stationCombo.currentIndex = at.station
        rangeCombo.currentIndex = at.range
        cfg_radarStation = id
    }

    Component.onCompleted: select(RadarStations.isKnownId(cfg_radarStation)
                                  ? cfg_radarStation : RadarStations.defaultId)

    QQC2.TextField {
        id: locationField
        Kirigami.FormData.label: i18n("Location:")
        placeholderText: "Seaford VIC"
        Layout.minimumWidth: Kirigami.Units.gridUnit * 18
    }

    QQC2.ComboBox {
        id: stationCombo
        Kirigami.FormData.label: i18n("Radar station:")
        Layout.minimumWidth: Kirigami.Units.gridUnit * 18
        model: RadarStations.stations.map(function(s) { return s.name })
        onActivated: page.select(RadarStations.idFor(
            currentIndex, RadarStations.parseId(page.cfg_radarStation).km))
    }

    QQC2.ComboBox {
        id: rangeCombo
        Kirigami.FormData.label: i18n("Radar range:")
        Layout.minimumWidth: Kirigami.Units.gridUnit * 18
        model: stationCombo.currentIndex >= 0
            ? RadarStations.stations[stationCombo.currentIndex].ranges.map(
                  function(r) { return i18n("%1 km", r) })
            : []
        onActivated: page.select(RadarStations.idAt(stationCombo.currentIndex, currentIndex))
    }

    QQC2.SpinBox {
        id: intervalSpin
        Kirigami.FormData.label: i18n("Update interval:")
        from: 10
        to: 60
        value: cfg_pollInterval / 60000
        onValueModified: cfg_pollInterval = value * 60000
        textFromValue: function(v) { return i18nc("minutes", "%1 min", v) }
        valueFromText: function(t) { return parseInt(t) || 10 }
    }

    Item { Kirigami.FormData.isSection: true }

    Kirigami.InlineMessage {
        Layout.fillWidth: true
        Layout.minimumWidth: Kirigami.Units.gridUnit * 20
        type: Kirigami.MessageType.Information
        visible: true
        text: i18n("Location: use 'Suburb STATE', e.g. 'Seaford VIC' or 'Sydney NSW'.\n" +
                   "Pick the radar station nearest your location; smaller ranges show more detail.")
    }
}
