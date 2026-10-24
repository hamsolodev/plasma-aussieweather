// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

import QtQuick
import org.kde.plasma.plasma5support as P5Support

import "helpers.js" as Helpers

// Runs one of the fetch scripts in contents/code/ through Plasma's
// executable engine, and hands back the object it printed (or the failure
// Helpers.scriptResult makes of anything else). -I isolates the script from
// the user's environment: plasmashell's working directory is $HOME, so
// without it a stray ~/json.py would be imported in place of the standard
// library.
P5Support.DataSource {
    id: runner

    required property string script

    signal finished(var result)

    function run(args) {
        var path = Helpers.localPath(Qt.resolvedUrl("../code/" + script))
        connectSource("python3 -I " + [path].concat(args).map(Helpers.shellQuote).join(" "))
    }

    engine: "executable"
    connectedSources: []
    onNewData: (sourceName, data) => {
        disconnectSource(sourceName)
        finished(Helpers.scriptResult(data))
    }
}
