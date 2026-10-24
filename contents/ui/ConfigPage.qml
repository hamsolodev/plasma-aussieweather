// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kcmutils as KCM
import org.kde.kirigami as Kirigami

import "places.js" as Places
import "radarstations.js" as RadarStations

// A SimpleKCM, as Plasma's own widgets' pages are, so a long list of places
// scrolls.
KCM.SimpleKCM {
    id: page

    property string cfg_locationSearch
    property string cfg_radarStation
    property var    cfg_places
    property int    cfg_pollInterval

    // Plasma passes the page a title (SimpleKCM has one) and a cfg_ property
    // for every config key, and logs "Setting initial properties failed" for
    // each one the page does not declare. The lookup cache's keys
    // (lastGeohash, lastLocationName, lastLocationSearch) are left
    // undeclared on purpose: Plasma writes every declared cfg_ value back on
    // Apply, which would put back the cache as it was when the dialog
    // opened, and counts any difference from it as an unsaved change.

    // The places being edited, {search, radar} each, and the index of the
    // one shown: -1 while none is (no location is set), as the page then
    // shows by checking none.
    ListModel { id: placesModel }
    property int shown: -1

    // Put the edited places in the cfg_ properties Plasma saves: the list,
    // and the place shown as locationSearch and radarStation.
    function save() {
        var places = []
        for (var i = 0; i < placesModel.count; i++)
            places.push({ search: placesModel.get(i).search, radar: placesModel.get(i).radar })
        cfg_places = Places.toConfig(places)
        var place = shown >= 0 ? places[shown] : undefined
        cfg_locationSearch = place ? place.search.trim() : ""
        cfg_radarStation = place ? place.radar : RadarStations.defaultId
    }

    function addPlace() {
        placesModel.append({ search: "", radar: RadarStations.defaultId })
    }

    // Removing the place shown shows the next one (or, if it was last, the
    // one before).
    function removePlace(index) {
        placesModel.remove(index)
        if (index < shown || shown >= placesModel.count)
            shown--
        save()
    }

    // Loading saves nothing: a config from before saved places would
    // otherwise count as changed the moment the page opened.
    Component.onCompleted: {
        var places = Places.fromConfig(cfg_places, cfg_locationSearch, cfg_radarStation)
        for (var i = 0; i < places.length; i++)
            placesModel.append(places[i])
        if (placesModel.count === 0)
            addPlace()
        shown = Places.indexOf(places, cfg_locationSearch)
    }

    Kirigami.FormLayout {
        ColumnLayout {
            Kirigami.FormData.label: i18n("Places:")
            // Beside the first place, not the middle of the list.
            Kirigami.FormData.labelAlignment: Qt.AlignTop
            spacing: Kirigami.Units.smallSpacing

            QQC2.ButtonGroup { id: shownGroup }

            Repeater {
                model: placesModel

                RowLayout {
                    id: row
                    required property int index
                    required property string search
                    required property string radar

                    // Show and store one product ID: the pickers follow it, so
                    // a station change can keep the range (the range model
                    // rebinds and resets).
                    function show(id) {
                        var at = RadarStations.locate(id)
                        stationCombo.currentIndex = at.station
                        rangeCombo.currentIndex = at.range
                    }
                    function select(id) {
                        show(id)
                        placesModel.setProperty(index, "radar", id)
                        page.save()
                    }
                    Component.onCompleted: show(radar)

                    // A blank place cannot be the one shown.
                    QQC2.RadioButton {
                        objectName: "shownButton"
                        QQC2.ButtonGroup.group: shownGroup
                        enabled: row.search.trim() !== ""
                        checked: row.index === page.shown
                        Accessible.name: i18n("Show this place")
                        onToggled: {
                            page.shown = row.index
                            page.save()
                        }
                        QQC2.ToolTip.text: i18n("Show this place")
                        QQC2.ToolTip.visible: hovered
                        QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                    }

                    QQC2.TextField {
                        objectName: "placeField"
                        Layout.preferredWidth: Kirigami.Units.gridUnit * 10
                        text: row.search
                        placeholderText: "Seaford VIC"
                        Accessible.name: i18n("Place")
                        // With none shown, the first place typed is shown.
                        onTextEdited: {
                            placesModel.setProperty(row.index, "search", text)
                            if (page.shown < 0 && text.trim() !== "")
                                page.shown = row.index
                            page.save()
                        }
                    }

                    QQC2.ComboBox {
                        id: stationCombo
                        Layout.preferredWidth: Kirigami.Units.gridUnit * 11
                        Accessible.name: i18n("Radar station")
                        model: RadarStations.stations.map(function(s) { return s.name })
                        onActivated: row.select(RadarStations.idFor(
                            currentIndex, RadarStations.parseId(row.radar).km))
                    }

                    QQC2.ComboBox {
                        id: rangeCombo
                        Layout.preferredWidth: Kirigami.Units.gridUnit * 5
                        Accessible.name: i18n("Radar range")
                        model: stationCombo.currentIndex >= 0
                            ? RadarStations.stations[stationCombo.currentIndex].ranges.map(
                                  function(r) { return i18n("%1 km", r) })
                            : []
                        onActivated: row.select(RadarStations.idAt(stationCombo.currentIndex, currentIndex))
                    }

                    QQC2.ToolButton {
                        icon.name: "list-remove-symbolic"
                        text: i18n("Remove This Place")
                        display: QQC2.AbstractButton.IconOnly
                        enabled: placesModel.count > 1
                        onClicked: page.removePlace(row.index)
                        QQC2.ToolTip.text: i18n("Remove this place")
                        QQC2.ToolTip.visible: hovered
                        QQC2.ToolTip.delay: Kirigami.Units.toolTipDelay
                    }
                }
            }

            QQC2.Button {
                icon.name: "list-add-symbolic"
                text: i18n("Add Place")
                onClicked: page.addPlace()
            }
        }

        QQC2.SpinBox {
            id: intervalSpin
            Kirigami.FormData.label: i18n("Update interval:")
            // main.qml holds polling to 10 minutes at least, whatever is set.
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
            text: i18n("Each place is 'Suburb STATE', e.g. 'Seaford VIC' or 'Sydney NSW', with the radar station nearest it; smaller ranges show more detail.\n" +
                       "The marked place is shown. Click the place's name at the bottom of the popup to switch between them.")
        }
    }
}
