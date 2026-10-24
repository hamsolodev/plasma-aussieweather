// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import org.kde.plasma.components as PlasmaComponents

// A Label that never interprets markup. Nearly everything this widget shows
// comes from the BoM API or the user's config, and a Label's default
// AutoText renders a string that opens with a tag as StyledText — loading
// any <img> in it. Use this for all text except the sanitised warning body.
PlasmaComponents.Label {
    textFormat: Text.PlainText
}
