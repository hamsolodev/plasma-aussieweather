#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Assert that _widgetVersion in main.qml matches KPlugin.Version in
# metadata.json. Plasma 6 exposes no QML API for the package version, so
# main.qml carries its own copy (it feeds the API User-Agent) — this guard
# keeps the two from drifting. Run in CI.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

meta_version="$(jq -r '.KPlugin.Version' "$ROOT/metadata.json")"
qml_version="$(sed -n 's/.*_widgetVersion: "\([^"]*\)".*/\1/p' "$ROOT/contents/ui/main.qml")"

if [ -z "$meta_version" ] || [ "$meta_version" = "null" ]; then
    echo "FAIL: could not read KPlugin.Version from metadata.json" >&2
    exit 1
fi
if [ -z "$qml_version" ]; then
    echo "FAIL: could not find _widgetVersion in contents/ui/main.qml" >&2
    exit 1
fi
if [ "$meta_version" != "$qml_version" ]; then
    echo "FAIL: version mismatch — metadata.json=$meta_version, main.qml _widgetVersion=$qml_version" >&2
    exit 1
fi

echo "OK: version $meta_version"
