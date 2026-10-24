// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami


// Aussie Weather: wires the configuration to the weather and radar sources,
// and those to the panel view, its tooltip and the popup.
PlasmoidItem {
    id: root

    // A floor of 10 minutes whatever the config says: BoM's observations
    // update about that often, so polling faster gains nothing.
    readonly property int pollInterval: Math.max(600000, Plasmoid.configuration.pollInterval)

    MinuteClock {
        id: minuteClock
    }

    WeatherModel {
        id: weatherModel
        now: minuteClock.now
        interval: root.pollInterval
    }

    WeatherSource {
        id: weatherSource
        config: Plasmoid.configuration
        version: Plasmoid.metaData.version
        interval: root.pollInterval
        weather: weatherModel
    }

    RadarSource {
        id: radarSource
        configuredStation: Plasmoid.configuration.radarStation
        interval: root.pollInterval
    }

    // The panel is as wide as the icon plus the temperature beside it.
    FontMetrics {
        id: panelFont
        font.pointSize: Kirigami.Theme.smallFont.pointSize
    }
    Layout.minimumWidth:  Kirigami.Units.iconSizes.smallMedium
    Layout.preferredWidth: Kirigami.Units.iconSizes.smallMedium
        + (weatherModel.temperatureText !== ""
            ? Kirigami.Units.smallSpacing
              + Math.ceil(panelFont.advanceWidth(weatherModel.temperatureText))
              + Kirigami.Units.smallSpacing
            : 0)

    Plasmoid.icon: weatherModel.currentIcon
    toolTipTextFormat: Text.PlainText
    toolTipMainText: i18nc("BoM is the Bureau of Meteorology; %1 is the location",
                           "BoM — %1", weatherModel.locationName)
    toolTipSubText: {
        if (!weatherModel.hasData) return weatherModel.errorText || i18n("Connecting…")
        var lines = [weatherModel.temperatureText
                     + (weatherModel.summaryText ? "  " + weatherModel.summaryText : "")]
        if (weatherModel.isStale)
            lines.push(i18n("Last updated %1", minuteClock.whenText(weatherModel.lastSuccessMs)))
        if (weatherModel.errorText) lines.push(weatherModel.errorText)
        return lines.join("\n")
    }

    compactRepresentation: CompactView {
        weather: weatherModel
        onActivated: root.expanded = !root.expanded
    }

    fullRepresentation: FullView {
        weather: weatherModel
        radar: radarSource
        clock: minuteClock
        expanded: root.expanded
        inPanelPopup: Plasmoid.formFactor === PlasmaCore.Types.Horizontal
                      || Plasmoid.formFactor === PlasmaCore.Types.Vertical
        onRefreshRequested: weatherSource.refresh()
    }
}
