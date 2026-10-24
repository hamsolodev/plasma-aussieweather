// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

// The settings page in a plain window, for scripts/check-settings.py: open()
// makes a fresh page from a config, as Plasma's dialog does, and the rest
// read it or act on it as a user would.

import QtQuick
import QtQuick.Window
import org.kde.kirigami as Kirigami

Window {
    id: window
    width: 900
    height: 500
    visible: true
    color: Kirigami.Theme.backgroundColor

    property Item page: null
    readonly property Component pageComponent: Qt.createComponent("../contents/ui/ConfigPage.qml")

    function open(places, locationSearch, radarStation) {
        if (page)
            page.destroy()
        page = pageComponent.createObject(window.contentItem, {
            "cfg_places": places, "cfg_locationSearch": locationSearch,
            "cfg_radarStation": radarStation, "cfg_pollInterval": 600000 })
        page.anchors.fill = window.contentItem
        return page !== null
    }

    // The controls named NAME, in row order.
    function controls(name) {
        var found = []
        var pending = [page]
        while (pending.length > 0) {
            var item = pending.pop()
            if (item.objectName === name)
                found.push(item)
            for (var i = 0; i < item.children.length; i++)
                pending.push(item.children[i])
        }
        return found.sort(function(a, b) { return a.parent.index - b.parent.index })
    }

    // What the page would save, and what it shows, as JSON.
    function state() {
        return JSON.stringify({
            shown: page.shown,
            places: page.cfg_places,
            locationSearch: page.cfg_locationSearch,
            radarStation: page.cfg_radarStation,
            buttons: controls("shownButton").map(function(b) { return [b.enabled, b.checked] }),
            fields: controls("placeField").map(function(f) { return f.text })
        })
    }

    function addPlace() { page.addPlace() }
    function removePlace(row) { page.removePlace(row) }
    function clickShown(row) { controls("shownButton")[row].click() }
    function focusField(row) { controls("placeField")[row].forceActiveFocus() }
}
