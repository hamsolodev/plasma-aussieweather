#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Compile .po translations into contents/locale/<lang>/LC_MESSAGES/*.mo so
# they ship inside the .plasmoid package. Run before packaging (CI does this).
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_ROOT="$DIR/.."
PLASMOID_NAME="net.tropism.plasma.aussieweather"
PROJECT_NAME="plasma_applet_${PLASMOID_NAME}"

found=0
for po in "$DIR"/*.po; do
    [ -e "$po" ] || continue
    found=1
    lang="$(basename "$po" .po)"
    dest="$PACKAGE_ROOT/contents/locale/$lang/LC_MESSAGES"
    mkdir -p "$dest"
    msgfmt -o "$dest/$PROJECT_NAME.mo" "$po"
    echo "Built $lang"
done

[ "$found" = 1 ] || echo "No .po files to build."
