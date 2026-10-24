#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Run every test suite: the fetch scripts' Python tests, then the QML tests
# of the JavaScript helpers. Used by CI and the release workflow.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

python3 -I -m unittest discover --start-directory "$ROOT/tests" --pattern 'test_*.py'

runner="$(command -v qmltestrunner || true)"
for candidate in /usr/lib64/qt6/bin/qmltestrunner /usr/lib/qt6/bin/qmltestrunner; do
    [ -n "$runner" ] && break
    [ -x "$candidate" ] && runner="$candidate"
done
if [ -z "$runner" ]; then
    echo "FAIL: qmltestrunner not found" >&2
    exit 1
fi
QT_QPA_PLATFORM=offscreen "$runner" -input "$ROOT/tests"
