#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Run every test suite that needs no Plasma: the fetch scripts' Python
# tests, then the QML tests of the helpers, the station table and
# WeatherModel. Used by CI and the release workflow. "test.sh python" runs
# the Python tests alone, as CI does on each Python the scripts support.
set -euo pipefail

case "${1:-}" in
    "" | python) ;;
    *) echo "usage: $0 [python]" >&2; exit 2 ;;
esac

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# -B: importing the scripts must not leave bytecode inside contents/.
python3 -I -B -m unittest discover --start-directory "$ROOT/tests" --pattern 'test_*.py'
if [ "${1:-}" = python ]; then
    exit 0
fi

runner="$(command -v qmltestrunner || true)"
for candidate in /usr/lib64/qt6/bin/qmltestrunner /usr/lib/qt6/bin/qmltestrunner; do
    [ -n "$runner" ] && break
    [ -x "$candidate" ] && runner="$candidate"
done
if [ -z "$runner" ]; then
    echo "FAIL: qmltestrunner not found" >&2
    exit 1
fi
# BoM's times are UTC and its locations span +6:30 to +12, so date logic
# that leans on the system time zone passes in one zone and fails in
# another. Run the QML tests in several.
# A private config directory: KDE code writes config as it loads, and an
# unwritable one makes KConfig pop up a dialog.
XDG_CONFIG_HOME="$(mktemp -d)"
export XDG_CONFIG_HOME
trap 'rm -r "$XDG_CONFIG_HOME"' EXIT
for tz in UTC Australia/Adelaide Australia/Brisbane America/New_York; do
    echo "== QML tests, TZ=$tz"
    TZ="$tz" QT_QPA_PLATFORM=offscreen "$runner" -input "$ROOT/tests"
done
