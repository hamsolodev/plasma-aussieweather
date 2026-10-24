// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

// i18n and friends for scripts/render.py, as plasmashell's KLocalizedContext
// provides them: set as the root context object, so the widget's bare
// i18n() calls resolve here. No translation, only %1..%9 substitution.

import QtQml

QtObject {
    function fill(text, args, first) {
        return text.replace(/%(\d)/g, function(match, n) {
            var i = first + Number(n) - 1
            return i < args.length ? String(args[i]) : match
        })
    }
    function i18n(text) { return fill(text, arguments, 1) }
    function i18nc(context, text) { return fill(text, arguments, 2) }
    function i18np(singular, plural, count) {
        return fill(count === 1 ? singular : plural, arguments, 2)
    }
    function i18ncp(context, singular, plural, count) {
        return fill(count === 1 ? singular : plural, arguments, 3)
    }
}
