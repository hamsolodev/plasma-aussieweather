// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import org.kde.kirigami as Kirigami

// The warnings in force, by title, on a band at the top of the Weather tab;
// clicking it opens the Warnings tab.
Item {
    id: banner

    required property WeatherModel weather

    signal clicked()

    visible: weather.hasWarnings
    implicitHeight: bannerRow.implicitHeight + Kirigami.Units.smallSpacing * 2

    Rectangle {
        anchors.fill: parent
        color: Kirigami.Theme.neutralTextColor
        opacity: 0.18
        radius: 3
    }
    RowLayout {
        id: bannerRow
        anchors {
            left: parent.left; right: parent.right
            verticalCenter: parent.verticalCenter
            leftMargin:  Kirigami.Units.smallSpacing
            rightMargin: Kirigami.Units.smallSpacing
        }
        spacing: Kirigami.Units.smallSpacing
        PlainLabel {
            Layout.fillWidth: true
            wrapMode: Text.WordWrap
            color: Kirigami.Theme.neutralTextColor
            text: {
                if (!banner.weather.hasWarnings) return ""
                return "⚠  " + banner.weather.currentWarnings.map(function(w) {
                    return w.title || i18n("Warning")
                }).join("  ·  ")
            }
        }
        Kirigami.Icon {
            Layout.preferredWidth:  Kirigami.Units.iconSizes.small
            Layout.preferredHeight: Kirigami.Units.iconSizes.small
            color: Kirigami.Theme.neutralTextColor
            source: "go-next-symbolic"
        }
    }
    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: banner.clicked()
    }
}
