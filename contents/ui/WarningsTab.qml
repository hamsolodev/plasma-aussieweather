// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami

import "helpers.js" as Helpers

// The Warnings tab: each warning in force, with its sanitised body and
// when it was issued and expires.
QQC2.ScrollView {
    id: tab

    required property WeatherModel weather
    required property MinuteClock clock

    // Cap the height this tab contributes to the popup. A long list of
    // warnings otherwise reports its full content height as implicitHeight,
    // inflating the popup past the screen; Plasma then clamps and persists
    // that height, leaving stuck whitespace on the other tabs. Size to the
    // content up to the cap, then scroll the rest.
    implicitHeight: Math.min(content.implicitHeight, Kirigami.Units.gridUnit * 24)
    contentWidth: availableWidth
    clip: true

    ColumnLayout {
        id: content
        width: tab.availableWidth
        spacing: Kirigami.Units.smallSpacing

        Repeater {
            model: tab.weather.currentWarnings
            delegate: ColumnLayout {
                required property var modelData
                required property int index
                Layout.fillWidth: true
                Layout.leftMargin:  Kirigami.Units.smallSpacing
                Layout.rightMargin: Kirigami.Units.smallSpacing
                spacing: 2

                PlainLabel {
                    Layout.fillWidth: true
                    Layout.topMargin: Kirigami.Units.smallSpacing
                    wrapMode: Text.WordWrap
                    color: Kirigami.Theme.neutralTextColor
                    font.weight: Font.Bold
                    text: modelData.title || i18n("Warning")
                }
                PlasmaComponents.Label {
                    // render.py's plain-text check allows RichText here only.
                    objectName: "warningBody"
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    visible: modelData.html !== ""
                    // poll.py rebuilds the body from a tag allowlist
                    // (sanitise): only https links survive and no images,
                    // so nothing here fetches.
                    textFormat: Text.RichText
                    linkColor: Kirigami.Theme.linkColor
                    text: modelData.html
                    onLinkActivated: (link) => { if (Helpers.isSafeUrl(link)) Qt.openUrlExternally(link) }
                    HoverHandler {
                        enabled: parent.hoveredLink !== ""
                        cursorShape: Qt.PointingHandCursor
                    }
                }
                // The warning's images (BoM's heatwave maps), which poll.py
                // saves as PNG files rather than leaving in the RichText.
                Repeater {
                    model: modelData.images || []
                    Image {
                        required property string modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitWidth > 0
                            ? width * implicitHeight / implicitWidth : 0
                        source: Helpers.fileUrl(modelData)
                        // Only ever scales down. No fillMode: with
                        // PreserveAspectFit, Qt scales the source up to
                        // fill the box at load time.
                        sourceSize.width: 1024
                        asynchronous: true
                    }
                }
                PlainLabel {
                    Layout.fillWidth: true
                    wrapMode: Text.WordWrap
                    opacity: 0.6
                    visible: text !== ""
                    // BoM gives each warning an issue and an expiry time;
                    // "final" is the last issue for the event.
                    text: {
                        var parts = []
                        if (modelData.phase === "final")
                            parts.push(i18n("Final warning"))
                        if (modelData.issue_time)
                            parts.push(i18n("Issued %1", tab.clock.dateTimeText(new Date(modelData.issue_time))))
                        if (modelData.expiry_time)
                            parts.push(i18n("Expires %1", tab.clock.dateTimeText(new Date(modelData.expiry_time))))
                        return parts.join("  ·  ")
                    }
                }
                Kirigami.Separator {
                    Layout.fillWidth: true
                    Layout.topMargin: Kirigami.Units.smallSpacing
                    visible: index < tab.weather.currentWarnings.length - 1
                }
            }
        }
    }
}
