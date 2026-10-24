// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import org.kde.kirigami as Kirigami

import "helpers.js" as Helpers

// The radar, composited: base map, topography, the animated rain loop,
// then the locations and range-ring overlays, with a frame counter.
Item {
    id: view

    required property RadarSource radar

    // The frame on show.
    property int frameIdx: 0

    implicitHeight: Kirigami.Units.gridUnit * 22

    // A new frame list starts its loop from the first frame.
    Connections {
        target: view.radar
        function onFramesChanged() { view.frameIdx = 0 }
    }

    // Whether frame i has loaded. Frames load asynchronously, and one still
    // loading shows as a blank.
    function frameLoaded(i) {
        var frame = frames.itemAt(i)
        return frame !== null && frame.status === Image.Ready
    }

    // The loop steps only to frames that have loaded, so on a slow
    // connection the first pass skips frames still loading rather than
    // flashing them blank; they join the loop as they arrive.
    Timer {
        interval: 400
        running: view.radar.active && view.radar.frames.length > 0
        repeat: true
        onTriggered: view.frameIdx = Helpers.nextLoadedFrame(
            view.frameIdx, view.radar.frames.length, i => view.frameLoaded(i))
    }

    // One of BoM's static transparencies for the station, stacked over the
    // base map. They never change, so Image's cache keeps them.
    component RadarLayer: Image {
        // Not "layer": that is a FINAL property of every Item, and redeclaring
        // it stops the whole file from compiling.
        required property string overlay
        anchors.fill: parent
        source: view.radar.active
            ? "https://www.bom.gov.au/products/radar_transparencies/"
              + view.radar.station + "." + overlay + ".png"
            : ""
        fillMode: Image.Stretch
        asynchronous: true
    }

    // BoM radar imagery is square (512×512). Every layer lives in this
    // centred square so none is stretched, whatever shape the popup or a
    // desktop widget takes.
    Item {
        anchors.centerIn: parent
        width:  Math.min(view.width, view.height)
        height: width

        // Opaque base map. BoM's overlays (locations, range) use black text
        // and lines, so the base must stay light whatever the desktop theme;
        // the Rectangle matches background.png's land colour and covers
        // loading or failure.
        Rectangle {
            anchors.fill: parent
            color: "#e7dcbd"
        }
        RadarLayer { overlay: "background" }
        // Terrain shading (partly transparent)
        RadarLayer { overlay: "topography" }

        // The loop: every frame loaded, only the current one visible.
        // cache: false, so replaced frames are released with the model.
        Repeater {
            id: frames
            model: view.radar.frames
            Image {
                required property string modelData
                required property int index
                anchors.fill: parent
                source: modelData
                fillMode: Image.Stretch
                asynchronous: true
                cache: false
                visible: index === view.frameIdx
                // While the frame on show has not loaded (a new set has just
                // started), the first to arrive is shown at once rather than
                // at the loop's next step.
                onStatusChanged: {
                    if (status === Image.Ready && !view.frameLoaded(view.frameIdx))
                        view.frameIdx = index
                }
            }
        }

        RadarLayer { overlay: "locations" }
        RadarLayer { overlay: "range" }

        // Frame counter, which shows where the loop starts. Black to match
        // BoM's own overlay text; the base map is always light.
        PlainLabel {
            anchors {
                left: parent.left
                bottom: parent.bottom
                margins: Kirigami.Units.smallSpacing
            }
            visible: view.radar.frames.length > 0
            text: (view.frameIdx + 1) + "/" + view.radar.frames.length
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            color: "black"
        }
    }
}
