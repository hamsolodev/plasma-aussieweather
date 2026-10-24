// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import org.kde.kirigami as Kirigami

// A PlainLabel coloured by a tone (Helpers.tempTone, rainTone, uvTone):
// what the colour means, in the theme's colours.
PlainLabel {
    // "negative", "neutral", "positive", "dim", or "" for ordinary text.
    property string tone: ""

    color: {
        switch (tone) {
        case "negative": return Kirigami.Theme.negativeTextColor
        case "neutral":  return Kirigami.Theme.neutralTextColor
        case "positive": return Kirigami.Theme.positiveTextColor
        case "dim":      return Kirigami.Theme.disabledTextColor
        default:         return Kirigami.Theme.textColor
        }
    }
}
