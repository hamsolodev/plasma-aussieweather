// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.plasma.plasmoid
import org.kde.plasma.components 3.0 as PlasmaComponents
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

import "helpers.js" as Helpers
import "radarstations.js" as RadarStations

PlasmoidItem {
    id: root

    FontMetrics {
        id: panelFm
        font.pointSize: Kirigami.Theme.smallFont.pointSize
    }
    Layout.minimumWidth:  Kirigami.Units.iconSizes.smallMedium
    Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
        + (panelText !== ""
            ? Kirigami.Units.smallSpacing
              + Math.ceil(panelFm.advanceWidth(panelText))
              + Kirigami.Units.smallSpacing
            : 0)

    // Keep in sync with metadata.json — Plasma 6 QML exposes no version API.
    readonly property string _widgetVersion: "1.6"

    // ── State ─────────────────────────────────────────────────────────────
    property bool   pollOk:       false
    property string errorText:    ""
    property var    observations: null
    property var    forecast:     []
    property var    warnings:     []
    property var    hourlyForecast: []
    property string locationName: plasmoid.configuration.locationSearch
    property string lastUpdated:  ""
    property string _geohash:     ""

    // Seed from last successful resolve so the widget works across restarts
    // without waiting for a fresh location lookup.
    Component.onCompleted: {
        var gh = plasmoid.configuration.lastGeohash
        var ln = plasmoid.configuration.lastLocationName
        if (gh) _geohash = gh
        if (ln) locationName = ln
    }

    readonly property string locationSearch: plasmoid.configuration.locationSearch
    onLocationSearchChanged: {
        _geohash     = ""
        locationName = locationSearch
        plasmoid.configuration.lastGeohash      = ""
        plasmoid.configuration.lastLocationName = ""
        observations   = null
        forecast       = []
        warnings       = []
        hourlyForecast = []
        lastUpdated    = ""
        pollOk         = false
        errorText      = ""
        _retryCount    = 0
        retryTimer.stop()
        root.refresh()
    }

    readonly property string panelText: pollOk ? Helpers.formatTemp(observations ? observations.temp : null) : ""

    // Night by astronomical sunrise/sunset (minute precision, reactive to
    // currentTime). The hourly is_night flag describes the slot's timestamp
    // instant, so using it for "now" quantises the day/night flip to the
    // hour mark — up to ~59 min after actual sunset.
    readonly property bool hasAstro: pollOk && forecast.length > 0 && !!forecast[0].astronomical
    readonly property bool isNight: {
        if (!hasAstro) return false
        var sunrise = new Date(forecast[0].astronomical.sunrise_time)
        var sunset  = new Date(forecast[0].astronomical.sunset_time)
        return currentTime < sunrise || currentTime >= sunset
    }

    readonly property string currentIcon: {
        if (!pollOk || !forecast || forecast.length === 0)
            return "weather-none-available"
        var now = root.currentTime
        // Descriptor from the hourly entry whose hour-bucket matches or most
        // recently precedes now; its is_night is hourly-quantised, so only
        // used when astronomical times are missing.
        if (hourlyForecast && hourlyForecast.length > 0) {
            var nowBucket = Math.floor(now.getTime() / 3600000)
            var best = null
            for (var i = 0; i < hourlyForecast.length; i++) {
                var bucket = Math.floor(new Date(hourlyForecast[i].time).getTime() / 3600000)
                if (bucket <= nowBucket) best = hourlyForecast[i]
            }
            if (best)
                return Helpers.bomIcon(best.icon_descriptor,
                                       root.hasAstro ? root.isNight : best.is_night)
        }
        return Helpers.bomIcon(forecast[0].icon_descriptor, root.isNight)
    }

    readonly property bool hasWarnings: Array.isArray(warnings) && warnings.length > 0

    Plasmoid.icon: currentIcon
    toolTipMainText: i18nc("BoM is the Bureau of Meteorology; %1 is the location",
                           "BoM — %1", locationName)
    toolTipSubText: pollOk
        ? (Helpers.formatTemp(observations ? observations.temp : null)
           + (forecast.length > 0 ? "  " + Helpers.titleCase(forecast[0].short_text || forecast[0].icon_descriptor || "") : ""))
        : (errorText || i18n("Connecting…"))

    // ── Python poll script ────────────────────────────────────────────────
    function shellQuote(s) {
        return "\"" + String(s || "").replace(/[\\\"`$]/g, "\\$&") + "\""
    }

    function pollScript() {
        return `import sys, json, urllib.request, urllib.parse
geohash = sys.argv[1]
q = sys.argv[2]
base = "https://api.weather.bom.gov.au/v1"
hdrs = {"User-Agent": "net.tropism.plasma.aussieweather/${root._widgetVersion}", "Accept": "application/json"}
def get(u):
    return json.load(urllib.request.urlopen(urllib.request.Request(u, headers=hdrs), timeout=15))
try:
    o = {"ok": True}
    if not geohash:
        parts = q.strip().rsplit(None, 1)
        state = parts[-1] if len(parts) > 1 and parts[-1].isalpha() and parts[-1].isupper() and 2 <= len(parts[-1]) <= 3 else None
        term = parts[0].strip() if state else q.strip()
        d = get(base + "/locations?search=" + urllib.parse.quote(term))
        locs = d.get("data", [])
        if not locs:
            print(json.dumps({"ok": False, "permanent": True, "error": "Location not found: " + q}))
            raise SystemExit(0)
        if state:
            preferred = [l for l in locs if l.get("state", "").upper() == state.upper()]
            if preferred:
                locs = preferred
        loc = locs[0]
        geohash = loc.get("geohash", "")[:6]
        o["geohash"] = geohash
        o["locationName"] = loc.get("name", "") + ", " + loc.get("state", "")
    obs = get(base + "/locations/" + geohash + "/observations")
    o["observations"] = obs.get("data", {})
    fc = get(base + "/locations/" + geohash + "/forecasts/daily")
    o["forecast"] = fc.get("data", [])[:7]
    try:
        hr = get(base + "/locations/" + geohash + "/forecasts/hourly")
        o["hourly"] = hr.get("data", [])[:8]
    except Exception:
        o["hourly"] = []
    try:
        w = get(base + "/locations/" + geohash + "/warnings")
        raw = w.get("data", [])
        warnings = []
        for warn in raw:
            wid = (warn.get("id") or "").strip()
            if wid:
                try:
                    detail = get(base + "/warnings/" + urllib.parse.quote(wid, safe=""))
                    merged = dict(warn)
                    merged.update(detail.get("data", {}))
                    warnings.append(merged)
                except Exception:
                    warnings.append(warn)
            else:
                warnings.append(warn)
        o["warnings"] = warnings
    except Exception:
        o["warnings"] = []
    print(json.dumps(o))
except SystemExit:
    pass
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
`
    }

    function buildPollCommand() {
        return "python3 -c '" + pollScript() + "' "
             + shellQuote(_geohash) + " "
             + shellQuote(locationSearch)
    }

    function _handlePoll(out) {
        var d
        try { d = JSON.parse(out) }
        catch (e) { d = { ok: false, error: i18n("Bad response") } }

        if (!d || !d.ok) {
            errorText = (d && d.error) ? d.error : i18n("Unreachable")
            // Keep showing the last good data through a transient failure —
            // a missed poll shouldn't blank a working widget.
            if (!observations) pollOk = false
            // Transient failures (e.g. DNS not yet up after wake from
            // sleep) are retried with exponential backoff: 5s..160s, ~5.3
            // min total, then the regular poll cycle takes over. Definitive
            // answers (permanent: location not found) are not retried.
            if (!d.permanent && _retryCount < 6) {
                retryTimer.interval = 5000 * Math.pow(2, _retryCount)
                _retryCount++
                retryTimer.restart()
            }
            return
        }

        _retryCount = 0
        retryTimer.stop()

        if (d.geohash) {
            _geohash = d.geohash
            plasmoid.configuration.lastGeohash = d.geohash
        }
        if (d.locationName) {
            locationName = d.locationName
            plasmoid.configuration.lastLocationName = d.locationName
        }
        observations    = d.observations || null
        forecast        = d.forecast     || []
        warnings        = d.warnings     || []
        hourlyForecast  = d.hourly       || []
        lastUpdated  = Qt.formatTime(new Date(), "h:mm ap")
        errorText    = ""
        pollOk       = true
    }

    // ── Poll plumbing ─────────────────────────────────────────────────────
    P5Support.DataSource {
        id: poller
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            poller.disconnectSource(sourceName)
            root._handlePoll((data["stdout"] || "").trim())
        }
    }

    property real _lastPollMs: 0
    property int  _retryCount: 0

    Timer {
        id: retryTimer
        repeat: false
        onTriggered: root.refresh()
    }

    // Floor of 10 minutes regardless of config — matches BoM's own
    // observation update cadence; polling faster gains nothing.
    readonly property int effectivePollInterval:
        Math.max(600000, plasmoid.configuration.pollInterval)

    function refresh() {
        _lastPollMs = Date.now()
        poller.connectSource(buildPollCommand())
    }

    Timer {
        interval: root.effectivePollInterval
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.refresh()
    }

    // Qt timers don't advance during system sleep. This watchdog uses
    // wall-clock time (Date.now() = CLOCK_REALTIME, which does advance
    // during sleep) to detect that data is stale after a wake and
    // triggers an immediate refresh rather than waiting out the
    // remaining timer interval.
    Timer {
        interval: 30000
        running: true
        repeat: true
        onTriggered: {
            if (root._lastPollMs > 0
                    && (Date.now() - root._lastPollMs) > root.effectivePollInterval)
                root.refresh()
        }
    }

    // ── Radar frame animation ─────────────────────────────────────────────
    property var radarFrameUrls: []
    property int radarFrameIdx:  0
    // True only while the popup is open on the Radar tab — gates all radar
    // network activity. Written by a Binding inside the radar tab.
    property bool radarActive: false

    // Ephemeral station override from the radar tab's quick picker. Cleared
    // when the tab is left, reverting to the station configured in settings.
    property string radarOverride: ""
    readonly property string activeRadarStation:
        radarOverride !== "" ? radarOverride : plasmoid.configuration.radarStation

    onActiveRadarStationChanged: {
        radarFrameUrls = []
        radarFrameIdx  = 0
        if (radarActive) refreshRadarFrames()
    }
    onRadarActiveChanged: if (!radarActive) radarOverride = ""

    // Minute-resolution clock snapped to wall-clock minute boundaries.
    // currentIcon and any is_night bindings reference this so they re-evaluate on the hour.
    property var currentTime: new Date()

    Timer {
        id: clockSync
        running: false
        repeat: false
        onTriggered: {
            root.currentTime = new Date()
            clockTick.start()
        }
        Component.onCompleted: {
            var now = new Date()
            var ms = (60 - now.getSeconds()) * 1000 - now.getMilliseconds()
            interval = ms > 100 ? ms : ms + 60000
            start()
        }
    }
    Timer {
        id: clockTick
        interval: 60000
        repeat: true
        running: false
        onTriggered: root.currentTime = new Date()
    }

    function radarFrameScript() {
        return `import sys, json, ftplib
station = sys.argv[1]
try:
    ftp = ftplib.FTP("ftp.bom.gov.au", timeout=15)
    ftp.login()
    ftp.cwd("/anon/gen/radar")
    files = []
    ftp.retrlines("NLST", files.append)
    ftp.quit()
    prefix = station + ".T."
    matching = sorted([f for f in files if f.startswith(prefix) and f.endswith(".png")])[-6:]
    urls = ["https://www.bom.gov.au/radar/" + f for f in matching]
    print(json.dumps({"ok": True, "frames": urls}))
except Exception as e:
    print(json.dumps({"ok": False, "error": str(e)}))
`
    }

    P5Support.DataSource {
        id: radarPoller
        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => {
            radarPoller.disconnectSource(sourceName)
            try {
                var d = JSON.parse((data["stdout"] || "").trim())
                if (d.ok && d.frames && d.frames.length > 0
                        && JSON.stringify(d.frames) !== JSON.stringify(root.radarFrameUrls)) {
                    root.radarFrameUrls = d.frames
                    root.radarFrameIdx  = 0
                }
            } catch(e) {}
        }
    }

    function refreshRadarFrames() {
        radarPoller.connectSource("python3 -c '"
            + radarFrameScript() + "' "
            + shellQuote(activeRadarStation))
    }

    // BoM radar scans every 5 minutes — refresh only while the Radar tab is
    // being viewed. triggeredOnStart re-checks the frame list each time the
    // tab becomes active; unchanged lists are dropped in onNewData, so
    // already-loaded frames are not re-downloaded.
    Timer {
        interval: 300000
        running: root.radarActive
        repeat: true
        triggeredOnStart: true
        onTriggered: root.refreshRadarFrames()
    }

    // ── Compact (panel) ───────────────────────────────────────────────────
    compactRepresentation: Item {
        clip: true
        MouseArea {
            anchors.fill: parent
            onClicked: root.expanded = !root.expanded
        }
        Kirigami.Icon {
            id: compactIco
            anchors.left: parent.left
            anchors.verticalCenter: parent.verticalCenter
            width:  Kirigami.Units.iconSizes.smallMedium
            height: width
            source: root.currentIcon
        }
        Rectangle {
            visible: root.hasWarnings
            height: Math.round(compactIco.height * 0.45)
            width:  Math.max(height, warningBadgeText.implicitWidth + Kirigami.Units.smallSpacing)
            radius: height / 2
            color:  Kirigami.Theme.neutralTextColor
            anchors.top:   compactIco.top
            anchors.right: compactIco.right
            Text {
                id: warningBadgeText
                anchors.centerIn: parent
                text: root.warnings.length
                font.pixelSize: Math.round(parent.height * 0.7)
                font.bold: true
                color: "#ffffff"
            }
        }
        PlasmaComponents.Label {
            anchors.left:         compactIco.right
            anchors.leftMargin:   Kirigami.Units.smallSpacing
            anchors.right:        parent.right
            anchors.verticalCenter: parent.verticalCenter
            visible: root.panelText !== ""
            text:    root.panelText
            font.pointSize: Kirigami.Theme.smallFont.pointSize
            elide:   Text.ElideRight
        }
    }

    // ── Full representation (popup) ───────────────────────────────────────
    fullRepresentation: ColumnLayout {
        spacing: 0
        Layout.minimumWidth:   Kirigami.Units.gridUnit * 20
        Layout.preferredWidth: Kirigami.Units.gridUnit * 22

        // Tab bar — the Warnings tab only exists while warnings are in effect.
        // TabBar doesn't collapse invisible buttons, so width must be zeroed too.
        PlasmaComponents.TabBar {
            id: tabBar
            Layout.fillWidth: true
            PlasmaComponents.TabButton { text: i18n("Weather") }
            PlasmaComponents.TabButton { text: i18n("Radar")   }
            PlasmaComponents.TabButton {
                visible: root.hasWarnings
                width: root.hasWarnings ? tabBar.width / 3 : 0
                text: i18n("⚠ Warnings (%1)", root.warnings.length)
            }
        }

        Connections {
            target: root
            function onHasWarningsChanged() {
                if (!root.hasWarnings && tabBar.currentIndex === 2)
                    tabBar.currentIndex = 0
            }
        }

        // Both tab bodies live in a StackLayout so the popup height is always
        // the taller of the two — no resize jump when switching tabs.
        StackLayout {
            currentIndex: tabBar.currentIndex
            Layout.fillWidth: true
            Layout.fillHeight: true

        // ── Weather tab ───────────────────────────────────────────────────
        ColumnLayout {
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            // Severe weather warning banner — click to open the Warnings tab
            Item {
                id: warningBanner
                visible: root.hasWarnings
                Layout.fillWidth: true
                implicitHeight: warnHeaderRow.implicitHeight + Kirigami.Units.smallSpacing * 2

                Rectangle {
                    anchors.fill: parent
                    color: Kirigami.Theme.neutralTextColor
                    opacity: 0.18
                    radius: 3
                }
                RowLayout {
                    id: warnHeaderRow
                    anchors {
                        left: parent.left; right: parent.right
                        verticalCenter: parent.verticalCenter
                        leftMargin:  Kirigami.Units.smallSpacing
                        rightMargin: Kirigami.Units.smallSpacing
                    }
                    spacing: Kirigami.Units.smallSpacing
                    PlasmaComponents.Label {
                        Layout.fillWidth: true
                        wrapMode: Text.WordWrap
                        color: Kirigami.Theme.neutralTextColor
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize
                        text: {
                            if (!root.hasWarnings) return ""
                            return "⚠  " + root.warnings.map(function(w) {
                                return w.title || w.type || "Warning"
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
                    onClicked: tabBar.currentIndex = 2
                }
            }

            // Current conditions: icon | big temp | description(fillWidth) | today hi/lo
            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin:  Kirigami.Units.smallSpacing
                Layout.leftMargin: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.smallSpacing

                Kirigami.Icon {
                    Layout.preferredWidth:  Kirigami.Units.iconSizes.large
                    Layout.preferredHeight: Kirigami.Units.iconSizes.large
                    source: root.currentIcon
                    visible: root.pollOk
                }

                PlasmaComponents.Label {
                    visible: root.pollOk
                    text: root.observations ? Helpers.formatTemp(root.observations.temp) : "—"
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize * 3
                    font.weight: Font.Bold
                }

                PlasmaComponents.Label {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignVCenter
                    visible: root.pollOk && root.observations !== null
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    opacity: 0.7
                    wrapMode: Text.WordWrap
                    text: {
                        if (!root.observations) return ""
                        var parts = []
                        var fl = root.observations.temp_feels_like
                        if (fl !== null && fl !== undefined)
                            parts.push(i18n("Feels like %1", Helpers.formatTemp(fl)))
                        var desc = root.forecast.length > 0
                            ? Helpers.titleCase(root.forecast[0].short_text
                                                || root.forecast[0].icon_descriptor || "")
                                  .replace(/\.$/, "")
                            : ""
                        if (desc) parts.push(desc)
                        return parts.join("  ·  ")
                    }
                }

                // Today's high / low from forecast
                ColumnLayout {
                    visible: root.pollOk && root.forecast.length > 0
                    spacing: 0
                    Layout.alignment: Qt.AlignVCenter
                    Layout.rightMargin: Kirigami.Units.smallSpacing

                    PlasmaComponents.Label {
                        Layout.alignment: Qt.AlignRight
                        text: Helpers.formatTemp(root.forecast.length > 0 ? root.forecast[0].temp_max : null)
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize + 1
                        font.weight: Font.Bold
                        color: {
                            var key = Helpers.tempColorKey(root.forecast.length > 0 ? root.forecast[0].temp_max : null)
                            if (key === "hot")  return Kirigami.Theme.negativeTextColor
                            if (key === "warm") return Kirigami.Theme.neutralTextColor
                            return Kirigami.Theme.textColor
                        }
                    }
                    PlasmaComponents.Label {
                        Layout.alignment: Qt.AlignRight
                        text: Helpers.formatTemp(root.forecast.length > 0 ? root.forecast[0].temp_min : null)
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize
                        opacity: 0.55
                    }
                    PlasmaComponents.Label {
                        Layout.alignment: Qt.AlignRight
                        visible: root.forecast.length > 0 && root.forecast[0].rain
                        text: (root.forecast.length > 0 && root.forecast[0].rain)
                            ? (root.forecast[0].rain.chance || 0) + "%"
                            : ""
                        font.pointSize: Kirigami.Theme.defaultFont.pointSize
                        color: {
                            var key = root.forecast.length > 0 && root.forecast[0].rain
                                ? Helpers.rainColorKey(root.forecast[0].rain.chance || 0) : "none"
                            if (key === "heavy")    return Kirigami.Theme.negativeTextColor
                            if (key === "moderate") return Kirigami.Theme.neutralTextColor
                            return Kirigami.Theme.disabledTextColor
                        }
                    }
                }
            }

            // Detail stats — row 1: wind (left) | filler | humidity · pressure (right)
            RowLayout {
                visible: root.pollOk && root.observations !== null
                Layout.fillWidth: true
                Layout.leftMargin:  Kirigami.Units.smallSpacing
                Layout.rightMargin: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.smallSpacing

                PlasmaComponents.Label {
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    text: {
                        if (!root.observations) return ""
                        var w = root.observations.wind || {}
                        var g = root.observations.gust || {}
                        var ws = Helpers.windStr(w.speed_kilometre, w.direction)
                        return "💨  " + (g.speed_kilometre
                            ? i18n("%1  (gusts %2)", ws, Math.round(g.speed_kilometre))
                            : ws)
                    }
                }
                Item { Layout.fillWidth: true }
                PlasmaComponents.Label {
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    visible: root.observations && root.observations.humidity !== undefined
                    text: root.observations
                        ? "💧  " + i18nc("relative humidity", "%1% RH",
                                         Math.round(root.observations.humidity || 0))
                        : ""
                }
                PlasmaComponents.Label {
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    visible: root.observations && root.observations.pressure !== undefined
                    text: root.observations
                        ? ("⬤  " + Helpers.pressureStr(root.observations.pressure,
                                                        root.observations.pressure_tendency))
                        : ""
                }
            }

            // Detail stats — row 2: rain (left) | filler | dew point / cloud (right)
            RowLayout {
                visible: root.pollOk && root.observations !== null
                         && (root.observations.rain_since_9am !== undefined
                             || root.observations.dew_point !== undefined
                             || root.observations.cloud)
                Layout.fillWidth: true
                Layout.leftMargin:  Kirigami.Units.smallSpacing
                Layout.rightMargin: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.smallSpacing

                PlasmaComponents.Label {
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    visible: root.observations && root.observations.rain_since_9am !== undefined
                    text: root.observations
                        ? "🌧  " + i18n("%1 mm since 9 am", root.observations.rain_since_9am || 0)
                        : ""
                }
                Item { Layout.fillWidth: true }
                PlasmaComponents.Label {
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    opacity: 0.65
                    visible: root.observations
                             && (root.observations.dew_point !== undefined || root.observations.cloud)
                    text: {
                        if (!root.observations) return ""
                        var parts = []
                        if (root.observations.dew_point !== undefined)
                            parts.push(i18nc("abbreviated dew point", "Dew pt %1",
                                             Helpers.formatTemp(root.observations.dew_point)))
                        if (root.observations.cloud) parts.push(root.observations.cloud)
                        return parts.join("  ·  ")
                    }
                }
            }

            Kirigami.Separator {
                Layout.fillWidth: true
                visible: root.pollOk && (root.hourlyForecast.length > 0 || root.forecast.length > 0)
                Layout.topMargin: Kirigami.Units.smallSpacing / 2
            }

            // Hourly forecast
            PlasmaComponents.Label {
                visible: root.pollOk && root.hourlyForecast.length > 0
                Layout.leftMargin: Kirigami.Units.smallSpacing
                text: i18n("Next 8 Hours")
                font.pointSize: Kirigami.Theme.defaultFont.pointSize
                font.weight: Font.Bold
                opacity: 0.55
            }

            Row {
                id: hourlyRow
                visible: root.pollOk && root.hourlyForecast.length > 0
                Layout.fillWidth: true
                Layout.leftMargin:  Kirigami.Units.smallSpacing
                Layout.rightMargin: Kirigami.Units.smallSpacing

                Repeater {
                    model: root.hourlyForecast
                    delegate: ColumnLayout {
                        required property var modelData
                        required property int index
                        width: hourlyRow.width / Math.max(root.hourlyForecast.length, 1)
                        spacing: 1

                        PlasmaComponents.Label {
                            Layout.alignment: Qt.AlignHCenter
                            font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            font.weight: index === 0 ? Font.Bold : Font.Normal
                            opacity: 0.65
                            text: {
                                var d = new Date(modelData.time)
                                var now = new Date()
                                if (Math.floor(d.getTime() / 3600000) === Math.floor(now.getTime() / 3600000))
                                    return i18n("Now")
                                return Qt.formatTime(d, "h ap").replace(" ", "")
                            }
                        }
                        Kirigami.Icon {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth:  Kirigami.Units.iconSizes.medium
                            Layout.preferredHeight: Kirigami.Units.iconSizes.medium
                            source: Helpers.bomIcon(modelData.icon_descriptor, modelData.is_night)

                            HoverHandler { id: hourHover }
                            PlasmaComponents.ToolTip {
                                visible: hourHover.hovered && text !== ""
                                delay: Kirigami.Units.toolTipDelay
                                text: {
                                    var lines = []
                                    if (modelData.temp_feels_like !== null && modelData.temp_feels_like !== undefined)
                                        lines.push(i18n("Feels like %1", Helpers.formatTemp(modelData.temp_feels_like)))
                                    var w = modelData.wind || {}
                                    if (w.speed_kilometre !== undefined) {
                                        var ws = Helpers.windStr(w.speed_kilometre, w.direction)
                                        lines.push(w.gust_speed_kilometre
                                            ? i18n("Wind %1 (gusts %2)", ws, Math.round(w.gust_speed_kilometre))
                                            : i18n("Wind %1", ws))
                                    }
                                    var hd = []
                                    if (modelData.relative_humidity !== null && modelData.relative_humidity !== undefined)
                                        hd.push(i18n("Humidity %1%", Math.round(modelData.relative_humidity)))
                                    if (modelData.dew_point !== null && modelData.dew_point !== undefined)
                                        hd.push(i18nc("abbreviated dew point", "Dew pt %1",
                                                      Helpers.formatTemp(modelData.dew_point)))
                                    if (hd.length) lines.push(hd.join("  ·  "))
                                    if (modelData.uv)
                                        lines.push(i18n("UV %1", modelData.uv))
                                    var ra = modelData.rain && modelData.rain.amount
                                    if (ra && ra.max)
                                        lines.push(i18n("Rain %1–%2 mm", ra.min || 0, ra.max))
                                    return lines.join("\n")
                                }
                            }
                        }
                        PlasmaComponents.Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: Helpers.formatTemp(modelData.temp)
                            font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            font.weight: Font.DemiBold
                        }
                        PlasmaComponents.Label {
                            Layout.alignment: Qt.AlignHCenter
                            visible: modelData.rain && (modelData.rain.chance || 0) > 0
                            font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            text: modelData.rain ? ((modelData.rain.chance || 0) + "%") : ""
                            color: {
                                var c = modelData.rain ? (modelData.rain.chance || 0) : 0
                                var key = Helpers.rainColorKey(c)
                                if (key === "heavy")    return Kirigami.Theme.negativeTextColor
                                if (key === "moderate") return Kirigami.Theme.neutralTextColor
                                if (key === "low")      return Kirigami.Theme.textColor
                                return Kirigami.Theme.disabledTextColor
                            }
                        }
                    }
                }
            }

            Kirigami.Separator {
                Layout.fillWidth: true
                visible: root.pollOk && root.hourlyForecast.length > 0 && root.forecast.length > 0
            }

            // 7-day forecast
            PlasmaComponents.Label {
                visible: root.pollOk && root.forecast.length > 0
                Layout.leftMargin: Kirigami.Units.smallSpacing
                text: i18n("7-Day Forecast")
                font.pointSize: Kirigami.Theme.defaultFont.pointSize
                font.weight: Font.Bold
                opacity: 0.55
            }

            // Row positioner: each delegate gets explicit width = 1/N of row width.
            // RowLayout + Repeater + Layout.fillWidth is unreliable when the model
            // populates after initial layout; Row with explicit widths is not.
            Row {
                id: forecastRow
                visible: root.pollOk && root.forecast.length > 0
                Layout.fillWidth: true
                Layout.leftMargin:  Kirigami.Units.smallSpacing
                Layout.rightMargin: Kirigami.Units.smallSpacing

                Repeater {
                    model: root.forecast
                    delegate: ColumnLayout {
                        required property var modelData
                        required property int index
                        width: forecastRow.width / Math.max(root.forecast.length, 1)
                        spacing: 1

                        PlasmaComponents.Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: index === 0 ? i18n("Today") : Helpers.shortDay(modelData.date)
                            font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            font.weight: index === 0 ? Font.Bold : Font.Normal
                            opacity: 0.65
                        }
                        Kirigami.Icon {
                            Layout.alignment: Qt.AlignHCenter
                            Layout.preferredWidth:  Kirigami.Units.iconSizes.large
                            Layout.preferredHeight: Kirigami.Units.iconSizes.large
                            source: Helpers.bomIcon(modelData.icon_descriptor, false)

                            HoverHandler { id: dayHover }
                            PlasmaComponents.ToolTip {
                                visible: dayHover.hovered && text !== ""
                                delay: Kirigami.Units.toolTipDelay
                                text: modelData.extended_text || modelData.short_text || ""
                            }
                        }
                        PlasmaComponents.Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: Helpers.formatTemp(modelData.temp_max)
                            font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            font.weight: Font.DemiBold
                            color: {
                                var key = Helpers.tempColorKey(modelData.temp_max)
                                if (key === "hot")  return Kirigami.Theme.negativeTextColor
                                if (key === "warm") return Kirigami.Theme.neutralTextColor
                                return Kirigami.Theme.textColor
                            }
                        }
                        PlasmaComponents.Label {
                            Layout.alignment: Qt.AlignHCenter
                            text: Helpers.formatTemp(modelData.temp_min)
                            font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            opacity: 0.5
                        }
                        PlasmaComponents.Label {
                            Layout.alignment: Qt.AlignHCenter
                            visible: modelData.rain !== undefined && modelData.rain !== null
                            text: {
                                var c = (modelData.rain && modelData.rain.chance !== undefined)
                                    ? modelData.rain.chance : null
                                return c !== null ? c + "%" : ""
                            }
                            font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            color: {
                                var c = (modelData.rain && modelData.rain.chance !== undefined)
                                    ? modelData.rain.chance : 0
                                var key = Helpers.rainColorKey(c)
                                if (key === "heavy")    return Kirigami.Theme.negativeTextColor
                                if (key === "moderate") return Kirigami.Theme.neutralTextColor
                                if (key === "low")      return Kirigami.Theme.textColor
                                return Kirigami.Theme.disabledTextColor
                            }
                        }
                    }
                }
            }

            // Error / loading state
            PlasmaComponents.Label {
                visible: !root.pollOk
                Layout.fillWidth: true
                Layout.margins: Kirigami.Units.largeSpacing
                wrapMode: Text.WordWrap
                horizontalAlignment: Text.AlignHCenter
                opacity: 0.7
                text: root.errorText
                    ? i18n("Cannot reach BoM:\n%1", root.errorText)
                    : i18n("Waiting for data…")
            }

            Kirigami.Separator {
                Layout.fillWidth: true
                visible: root.pollOk && root.forecast.length > 0
                Layout.topMargin: Kirigami.Units.smallSpacing / 2
            }

            // Extended forecast text
            PlasmaComponents.Label {
                visible: root.pollOk && root.forecast.length > 0
                             && (root.forecast[0].extended_text || "") !== ""
                Layout.fillWidth: true
                Layout.leftMargin:  Kirigami.Units.smallSpacing
                Layout.rightMargin: Kirigami.Units.smallSpacing
                Layout.topMargin:   Kirigami.Units.smallSpacing / 2
                wrapMode: Text.WordWrap
                font.pointSize: Kirigami.Theme.defaultFont.pointSize
                opacity: 0.75
                text: root.forecast.length > 0 ? (root.forecast[0].extended_text || "") : ""
            }

            // UV · Sunrise/Sunset · Moon phase (merged row)
            RowLayout {
                visible: root.pollOk && root.forecast.length > 0
                Layout.fillWidth: true
                Layout.leftMargin:  Kirigami.Units.smallSpacing
                Layout.rightMargin: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.smallSpacing

                // At night UV is always 0 — show a happy moon instead; the
                // sun icon + UV reading return at sunrise (isNight is
                // minute-reactive via currentTime).
                PlasmaComponents.Label {
                    visible: root.isNight
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    text: "🌛"
                }
                Kirigami.Icon {
                    visible: !root.isNight && !!root.forecast[0].uv
                    Layout.preferredWidth:  Kirigami.Units.iconSizes.small
                    Layout.preferredHeight: Kirigami.Units.iconSizes.small
                    source: "weather-clear-symbolic"
                }
                PlasmaComponents.Label {
                    visible: !root.isNight && !!root.forecast[0].uv
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    font.weight: Font.DemiBold
                    text: {
                        if (!root.forecast.length || !root.forecast[0].uv) return ""
                        var uv = root.forecast[0].uv
                        var label = Helpers.titleCase((uv.category || "").replace(/_/g, " "))
                        var idx = (uv.max_index !== null && uv.max_index !== undefined) ? uv.max_index : ""
                        return label + (idx !== "" ? "  " + idx : "")
                    }
                    color: {
                        if (!root.forecast.length || !root.forecast[0].uv) return Kirigami.Theme.textColor
                        switch ((root.forecast[0].uv.category || "").toLowerCase()) {
                            case "extreme":
                            case "very_high": return Kirigami.Theme.negativeTextColor
                            case "high":      return Kirigami.Theme.neutralTextColor
                            case "low":       return Kirigami.Theme.positiveTextColor
                            default:          return Kirigami.Theme.textColor
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                PlasmaComponents.Label {
                    visible: !!root.forecast[0].astronomical
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    opacity: 0.65
                    text: {
                        if (!root.forecast.length || !root.forecast[0].astronomical) return ""
                        var a = root.forecast[0].astronomical
                        return "🌅 " + Qt.formatTime(new Date(a.sunrise_time), "h:mm ap").replace(" ", "")
                               + "  ·  🌇 " + Qt.formatTime(new Date(a.sunset_time), "h:mm ap").replace(" ", "")
                    }
                }

                Item { Layout.fillWidth: true }

                PlasmaComponents.Label {
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    text: {
                        var mp = Helpers.moonPhase(root.currentTime)
                        return mp.emoji + "  " + mp.name
                    }
                }
            }

            Item { Layout.fillHeight: true }

            Kirigami.Separator { Layout.fillWidth: true }

            // Footer
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin:   Kirigami.Units.smallSpacing
                Layout.rightMargin:  Kirigami.Units.smallSpacing
                Layout.bottomMargin: Kirigami.Units.smallSpacing

                PlasmaComponents.Label {
                    Layout.fillWidth: true
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    opacity: 0.5
                    elide: Text.ElideRight
                    text: {
                        var parts = [root.locationName]
                        if (root.pollOk && root.observations && root.observations.station) {
                            var st = root.observations.station
                            var km = st.distance ? (st.distance / 1000).toFixed(1) : null
                            parts.push(st.name + (km ? " (" + km + " km)" : ""))
                        }
                        if (root.lastUpdated) parts.push(root.lastUpdated)
                        return parts.join("  ·  ")
                    }
                }
                PlasmaComponents.Button {
                    icon.name: "view-refresh-symbolic"
                    onClicked: root.refresh()
                }
                PlasmaComponents.Button {
                    icon.name: "internet-web-browser-symbolic"
                    text: "BoM"
                    onClicked: Qt.openUrlExternally("https://www.bom.gov.au/vic/")
                }
            }
        }

        // ── Radar tab ─────────────────────────────────────────────────────
        ColumnLayout {
            id: radarTab
            Layout.fillWidth: true
            spacing: Kirigami.Units.smallSpacing

            function syncQuickPickers() {
                var p = RadarStations.parseId(root.activeRadarStation)
                if (!p) return
                var stIdx = RadarStations.indexOfSite(p.site)
                if (stIdx < 0) return
                quickStation.currentIndex = stIdx
                var rIdx = RadarStations.stations[stIdx].ranges.indexOf(p.km)
                quickRange.currentIndex = rIdx >= 0 ? rIdx : 0
            }
            Component.onCompleted: syncQuickPickers()

            Binding {
                target: root
                property: "radarActive"
                value: root.expanded && tabBar.currentIndex === 1
            }

            Timer {
                interval: 400
                running: root.radarActive && root.radarFrameUrls.length > 0
                repeat: true
                onTriggered: root.radarFrameIdx = (root.radarFrameIdx + 1) % root.radarFrameUrls.length
            }

            // Equal stretch above and below centres the radar vertically;
            // the buttons row stays pinned to the bottom.
            Item { Layout.fillHeight: true }

            // Quick station/range picker. Selections set root.radarOverride,
            // which is cleared on leaving the tab — the configured station is
            // the sticky default.
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin:  Kirigami.Units.smallSpacing
                Layout.rightMargin: Kirigami.Units.smallSpacing
                spacing: Kirigami.Units.smallSpacing

                PlasmaComponents.Label {
                    Layout.fillWidth: true
                    elide: Text.ElideRight
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    font.weight: Font.Bold
                    text: {
                        var p = RadarStations.parseId(root.activeRadarStation)
                        if (!p) return root.activeRadarStation
                        var idx = RadarStations.indexOfSite(p.site)
                        var name = idx >= 0 ? RadarStations.stations[idx].name
                                            : root.activeRadarStation
                        return i18nc("radar loop title: station name, range",
                                     "%1  ·  %2 km", name, p.km)
                    }
                }

                QQC2.ComboBox {
                    id: quickStation
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 8
                    model: RadarStations.stations.map(function(s) { return s.name })
                    onActivated: {
                        var st = RadarStations.stations[currentIndex]
                        var p  = RadarStations.parseId(root.activeRadarStation)
                        var km = p && st.ranges.indexOf(p.km) >= 0
                            ? p.km : st.ranges[st.ranges.length - 1]
                        root.radarOverride = RadarStations.stationId(st.site, km)
                    }
                }
                QQC2.ComboBox {
                    id: quickRange
                    Layout.preferredWidth: Kirigami.Units.gridUnit * 5
                    model: quickStation.currentIndex >= 0
                        ? RadarStations.stations[quickStation.currentIndex].ranges.map(
                              function(r) { return i18n("%1 km", r) })
                        : []
                    onActivated: {
                        var st = RadarStations.stations[quickStation.currentIndex]
                        root.radarOverride = RadarStations.stationId(
                            st.site, st.ranges[currentIndex])
                    }
                }
            }

            // Keep the pickers tracking the active station — both when the
            // override reverts on tab exit and when settings change.
            Connections {
                target: root
                function onActiveRadarStationChanged() { radarTab.syncQuickPickers() }
            }

            // Composited radar: topography + animated loop + overlays
            Item {
                id: radarFrame
                Layout.fillWidth: true
                implicitHeight: Kirigami.Units.gridUnit * 22

                // BoM radar imagery is square (512×512). All layers live in
                // this centred square so they are never stretched, whatever
                // shape the popup or a plasmawindowed window takes.
                Item {
                anchors.centerIn: parent
                width:  Math.min(radarFrame.width, radarFrame.height)
                height: width

                // Opaque base map. BoM's overlays (locations, range) use black
                // text/lines, so the base must stay light regardless of the
                // desktop theme — the Rectangle matches background.png's land
                // colour and covers loading/failure.
                Rectangle {
                    anchors.fill: parent
                    color: "#e7dcbd"
                }
                Image {
                    anchors.fill: parent
                    source: "http://www.bom.gov.au/products/radar_transparencies/"
                          + root.activeRadarStation + ".background.png"
                    fillMode: Image.Stretch
                    asynchronous: true
                    cache: false
                }

                // Terrain shading (partially transparent)
                Image {
                    anchors.fill: parent
                    source: "http://www.bom.gov.au/products/radar_transparencies/"
                          + root.activeRadarStation + ".topography.png"
                    fillMode: Image.Stretch
                    asynchronous: true
                    cache: false
                }

                // Animated radar loop — all frames pre-loaded, only current frame visible.
                // cache: false so replaced frames are released when the model updates.
                Repeater {
                    model: root.radarFrameUrls
                    Image {
                        required property string modelData
                        required property int index
                        anchors.fill: parent
                        source: modelData
                        fillMode: Image.Stretch
                        asynchronous: true
                        cache: false
                        visible: index === root.radarFrameIdx
                    }
                }

                // Locations label overlay
                Image {
                    anchors.fill: parent
                    source: "http://www.bom.gov.au/products/radar_transparencies/"
                          + root.activeRadarStation + ".locations.png"
                    fillMode: Image.Stretch
                    asynchronous: true
                    cache: false
                }

                // Range rings overlay
                Image {
                    anchors.fill: parent
                    source: "http://www.bom.gov.au/products/radar_transparencies/"
                          + root.activeRadarStation + ".range.png"
                    fillMode: Image.Stretch
                    asynchronous: true
                    cache: false
                }

                // Frame counter — shows where the loop starts. Black to match
                // BoM's own overlay text; the base map is always light.
                PlasmaComponents.Label {
                    anchors {
                        left: parent.left
                        bottom: parent.bottom
                        margins: Kirigami.Units.smallSpacing
                    }
                    visible: root.radarFrameUrls.length > 0
                    text: (root.radarFrameIdx + 1) + "/" + root.radarFrameUrls.length
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    color: "black"
                }
                } // square layer container
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin:  Kirigami.Units.smallSpacing
                Layout.rightMargin: Kirigami.Units.smallSpacing

                PlasmaComponents.Label {
                    Layout.fillWidth: true
                    font.pointSize: Kirigami.Theme.defaultFont.pointSize
                    opacity: 0.55
                    text: root.radarFrameUrls.length > 0
                        ? i18n("Radar: %1  ·  %2 frames",
                               root.activeRadarStation,
                               root.radarFrameUrls.length)
                        : i18n("Radar: %1  ·  Loading…",
                               root.activeRadarStation)
                }
                PlasmaComponents.Button {
                    icon.name: "view-refresh-symbolic"
                    onClicked: {
                        root.radarFrameUrls = []
                        root.refreshRadarFrames()
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
                        "https://www.bom.gov.au/products/"
                        + root.activeRadarStation + ".loop.shtml")
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

        // ── Warnings tab ──────────────────────────────────────────────────
        QQC2.ScrollView {
            id: warningsTab
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: warningsTab.availableWidth
                spacing: Kirigami.Units.smallSpacing

                Repeater {
                    model: root.warnings
                    delegate: ColumnLayout {
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        Layout.leftMargin:  Kirigami.Units.smallSpacing
                        Layout.rightMargin: Kirigami.Units.smallSpacing
                        spacing: 2

                        PlasmaComponents.Label {
                            Layout.fillWidth: true
                            Layout.topMargin: Kirigami.Units.smallSpacing
                            wrapMode: Text.WordWrap
                            color: Kirigami.Theme.neutralTextColor
                            font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            font.weight: Font.Bold
                            text: modelData.title || modelData.type || "Warning"
                        }
                        PlasmaComponents.Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            visible: (modelData.text || modelData.description || modelData.message || "").length > 0
                            text: modelData.text || modelData.description || modelData.message || ""
                        }
                        PlasmaComponents.Label {
                            Layout.fillWidth: true
                            wrapMode: Text.WordWrap
                            font.pointSize: Kirigami.Theme.defaultFont.pointSize
                            opacity: 0.6
                            visible: !!(modelData.valid_from)
                            text: {
                                if (!modelData.valid_from) return ""
                                var from = Qt.formatDateTime(new Date(modelData.valid_from), "d MMM h:mm ap")
                                if (!modelData.valid_to) return "From: " + from
                                return "Valid: " + from + " – " + Qt.formatDateTime(new Date(modelData.valid_to), "d MMM h:mm ap")
                            }
                        }
                        Kirigami.Separator {
                            Layout.fillWidth: true
                            Layout.topMargin: Kirigami.Units.smallSpacing
                            visible: index < root.warnings.length - 1
                        }
                    }
                }
            }
        }
        } // StackLayout
    }
}
