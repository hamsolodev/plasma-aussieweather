#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Extract translatable strings from the widget's QML/JS into template.pot,
# then merge updates into any existing .po files.
# Per https://develop.kde.org/docs/plasma/widget/translations-i18n/
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_ROOT="$DIR/.."
PLASMOID_NAME="net.tropism.plasma.aussieweather"
PROJECT_NAME="plasma_applet_${PLASMOID_NAME}"
BUG_ADDRESS="https://github.com/hamsolodev/plasma-aussieweather/issues"

cd "$PACKAGE_ROOT"
find contents -name '*.qml' -o -name '*.js' | sort > "$DIR/infiles.list"

xgettext \
    --files-from="$DIR/infiles.list" \
    --from-code=UTF-8 \
    --language=JavaScript \
    -ci18n \
    -ki18n:1 -ki18nc:1c,2 -ki18np:1,2 -ki18ncp:1c,2,3 \
    -kxi18n:1 -kxi18nc:1c,2 -kxi18np:1,2 -kxi18ncp:1c,2,3 \
    --package-name="$PROJECT_NAME" \
    --msgid-bugs-address="$BUG_ADDRESS" \
    -o "$DIR/template.pot"

rm -f "$DIR/infiles.list"

for po in "$DIR"/*.po; do
    [ -e "$po" ] || continue
    echo "Merging $(basename "$po")"
    msgmerge --update --backup=none "$po" "$DIR/template.pot"
done

echo "Wrote $DIR/template.pot"
