// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami

// The popup (or the desktop widget): Weather, Radar and, while any are in
// force, Warnings tabs.
ColumnLayout {
    id: full

    required property WeatherModel weather
    required property RadarSource radar
    required property MinuteClock clock
    // Whether the popup is open; the desktop widget is always shown.
    required property bool expanded
    // Whether this is a panel's popup rather than a desktop widget.
    required property bool inPanelPopup

    signal refreshRequested()

    spacing: 0
    Layout.minimumWidth:   Kirigami.Units.gridUnit * 20
    Layout.preferredWidth: Kirigami.Units.gridUnit * 22

    // Each tab body pins its footer to the bottom with an
    // `Item { Layout.fillHeight: true }` spacer, and a ColumnLayout holding a
    // fillHeight child reports Layout.maximumHeight as Infinity. Plasma
    // clamps the popup into [minimumHeight, maximumHeight] against its
    // *current* size, so with an unbounded maximum a popup that grew for a
    // tall tab clamps to itself and never shrinks back: switching to a
    // shorter tab left dead space. (The Warnings tab is a ScrollView with no
    // spacer, so its maximum equals its content height, which is why that
    // one tab always did collapse.) Cap the maximum to the content height in
    // a panel popup; on the desktop the widget must stay freely resizable,
    // so leave it unbounded there.
    Layout.maximumHeight: inPanelPopup ? implicitHeight : Number.POSITIVE_INFINITY

    // The Warnings tab exists only while warnings are in force. TabBar does
    // not collapse an invisible button, so its width is zeroed too; while
    // shown, its width is reset so TabBar shares the space equally. (Sizing
    // it from tabBar.width made a binding loop: TabBar's implicit width is
    // its buttons'.)
    PlasmaComponents.TabBar {
        id: tabBar
        Layout.fillWidth: true
        PlasmaComponents.TabButton { text: i18n("Weather") }
        PlasmaComponents.TabButton { text: i18n("Radar") }
        PlasmaComponents.TabButton {
            visible: full.weather.hasWarnings
            width: full.weather.hasWarnings ? undefined : 0
            text: i18n("⚠ Warnings (%1)", full.weather.currentWarnings.length)
        }
    }

    Connections {
        target: full.weather
        function onHasWarningsChanged() {
            if (!full.weather.hasWarnings && tabBar.currentIndex === 2)
                tabBar.currentIndex = 0
        }
    }

    // The radar fetches only while its tab is on screen: on the desktop
    // that is whenever the tab is chosen; in a panel the popup must be open.
    Binding {
        target: full.radar
        property: "active"
        value: (full.expanded || !full.inPanelPopup) && tabBar.currentIndex === 1
    }

    // Tab bodies in a ColumnLayout with visible bindings, so only the
    // visible tab contributes to the popup's implicit height.
    ColumnLayout {
        Layout.fillWidth: true
        spacing: 0

        WeatherTab {
            visible: tabBar.currentIndex === 0
            Layout.fillWidth: true
            weather: full.weather
            clock: full.clock
            onWarningsRequested: tabBar.currentIndex = 2
            onRefreshRequested: full.refreshRequested()
        }

        RadarTab {
            visible: tabBar.currentIndex === 1
            Layout.fillWidth: true
            radar: full.radar
            clock: full.clock
        }

        WarningsTab {
            visible: tabBar.currentIndex === 2
            Layout.fillWidth: true
            weather: full.weather
            clock: full.clock
        }
    }
}
