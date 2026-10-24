#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Build net.tropism.plasma.aussieweather-<version>.plasmoid at the repo root:
# compile translations into contents/locale, then zip metadata.json and
# contents/. Prints the package's path on stdout. Used by CI, the release
# workflow and the README's install-from-source steps.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

bash translate/build.sh >&2

package="$ROOT/$(python3 -I scripts/metadata.py Id)-$(python3 -I scripts/metadata.py Version).plasmoid"
rm -f "$package"
zip -qr "$package" metadata.json contents/ -x '*/__pycache__/*' '*.pyc'
echo "$package"
