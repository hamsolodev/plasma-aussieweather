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

    // Last applied range in km — survives the range model rebinding (which
    // resets rangeCombo.currentIndex) when the station changes.
    property int _selectedKm: 128

    function applySelection() {
        var st = RadarStations.stations[stationCombo.currentIndex]
        var km = st.ranges[rangeCombo.currentIndex]
        _selectedKm = km
        cfg_radarStation = RadarStations.stationId(st.site, km)
    }

    Component.onCompleted: {
        var id = plasmoid.configuration.radarStation
        var parsed = RadarStations.parseId(
            RadarStations.isKnownId(id) ? id : RadarStations.defaultId)
        var stIdx = RadarStations.indexOfSite(parsed.site)
        stationCombo.currentIndex = stIdx
        var rIdx = RadarStations.stations[stIdx].ranges.indexOf(parsed.km)
        rangeCombo.currentIndex = rIdx >= 0 ? rIdx : 0
        applySelection()
    }

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
        onActivated: {
            // Keep the previously chosen range if the new station offers it
            var ranges = RadarStations.stations[currentIndex].ranges
            var rIdx = ranges.indexOf(page._selectedKm)
            rangeCombo.currentIndex = rIdx >= 0 ? rIdx : ranges.length - 1
            page.applySelection()
        }
    }

    QQC2.ComboBox {
        id: rangeCombo
        Kirigami.FormData.label: i18n("Radar range:")
        Layout.minimumWidth: Kirigami.Units.gridUnit * 18
        model: stationCombo.currentIndex >= 0
            ? RadarStations.stations[stationCombo.currentIndex].ranges.map(
                  function(r) { return i18n("%1 km", r) })
            : []
        onActivated: page.applySelection()
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
