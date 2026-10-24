// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import QtQuick.Layouts
import org.kde.plasma.components as PlasmaComponents
import org.kde.kirigami as Kirigami

// A forecast entry's condition icon, with more about it on hover.
Kirigami.Icon {
    id: icon

    // Shown in a tooltip on hover; none when empty.
    property string details: ""

    Layout.alignment: Qt.AlignHCenter

    HoverHandler { id: hover }
    PlasmaComponents.ToolTip {
        visible: hover.hovered && text !== ""
        textFormat: Text.PlainText
        delay: Kirigami.Units.toolTipDelay
        text: icon.details
    }
}
