// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import org.kde.kirigami as Kirigami

// The panel: condition icon, a badge counting warnings, and the temperature
// (dimmed once out of date).
Item {
    id: compact

    required property WeatherModel weather

    signal activated()

    clip: true

    MouseArea {
        anchors.fill: parent
        onClicked: compact.activated()
    }
    Kirigami.Icon {
        id: icon
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width:  Kirigami.Units.iconSizes.smallMedium
        height: width
        source: compact.weather.currentIcon
    }
    Rectangle {
        visible: compact.weather.hasWarnings
        height: Math.round(icon.height * 0.45)
        width:  Math.max(height, badgeText.implicitWidth + Kirigami.Units.smallSpacing)
        radius: height / 2
        color:  Kirigami.Theme.neutralTextColor
        anchors.top:   icon.top
        anchors.right: icon.right
        Text {
            id: badgeText
            anchors.centerIn: parent
            textFormat: Text.PlainText
            text: compact.weather.warnings.length
            font.pixelSize: Math.round(parent.height * 0.7)
            font.bold: true
            color: "#ffffff"
        }
    }
    PlainLabel {
        anchors.left:         icon.right
        anchors.leftMargin:   Kirigami.Units.smallSpacing
        anchors.right:        parent.right
        anchors.verticalCenter: parent.verticalCenter
        visible: compact.weather.temperatureText !== ""
        text:    compact.weather.temperatureText
        opacity: compact.weather.isStale ? 0.5 : 1
        font.pointSize: Kirigami.Theme.smallFont.pointSize
        elide:   Text.ElideRight
    }
}
