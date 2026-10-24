// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick

import "helpers.js" as Helpers

// A forecast entry's chance of rain, coloured by how likely it is, and
// shown whenever BoM gives one (0% included, dimmed).
ToneLabel {
    required property var entry
    readonly property var chance: Helpers.rainChance(entry)

    visible: chance !== null
    text: chance !== null ? chance + "%" : ""
    tone: Helpers.rainTone(chance)
}
