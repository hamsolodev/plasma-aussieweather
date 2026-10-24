// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import org.kde.kirigami as Kirigami

// A PlainLabel coloured by a Helpers colour key (tempColorKey,
// rainColorKey): hot and heavy as negative, warm and moderate as neutral,
// none dimmed, anything else the normal text colour.
PlainLabel {
    property string tone: ""

    color: {
        switch (tone) {
        case "hot":
        case "heavy":    return Kirigami.Theme.negativeTextColor
        case "warm":
        case "moderate": return Kirigami.Theme.neutralTextColor
        case "none":     return Kirigami.Theme.disabledTextColor
        default:         return Kirigami.Theme.textColor
        }
    }
}
