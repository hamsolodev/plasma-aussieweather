#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Retake the README's screenshots, docs/screenshots/: BoM's weather for
# PLACE now (default "Seaford VIC") with the live radar of STATION (default
# IDR023, Melbourne at 128 km), in Breeze Light and Breeze Dark, at twice
# the size. Each popup gets rounded corners, a hairline edge and a shadow,
# as a Plasma popup has; the panel is shown as it is.
#
#     scripts/docs-screenshots.sh [PLACE [STATION]]
#
# Needs what scripts/render.py needs, the network, and ImageMagick.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
place="${1:-Seaford VIC}"
station="${2:-IDR023}"
work="$(mktemp -d)"
trap 'rm -r "$work"' EXIT

# frame IN OUT EDGE: IN with rounded corners, an EDGE-coloured hairline and
# a shadow, written to OUT.
frame() {
    local width height
    read -r width height < <(magick identify -format '%w %h\n' "$1")
    magick "$1" \
        \( -size "${width}x${height}" xc:none -fill white \
           -draw "roundrectangle 0,0,$((width - 1)),$((height - 1)),16,16" \) \
        -alpha set -compose DstIn -composite -compose Over \
        -fill none -stroke "$3" -strokewidth 2 \
        -draw "roundrectangle 1,1,$((width - 2)),$((height - 2)),15,15" \
        \( +clone -background black -shadow 40x20+0+10 \) +swap \
        -background none -layers merge +repage -strip "$2"
}

for scheme in light dark; do
    python3 -I "$ROOT/scripts/render.py" "$work" --scheme "$scheme" \
        --live "$place" --station "$station" --scale 2
done

for scheme in light dark; do
    edge=$([ "$scheme" = light ] && echo "#bcc0c4" || echo "#4d5257")
    for tab in weather radar warnings; do
        frame "$work/$scheme-$tab.png" "$ROOT/docs/screenshots/$scheme-$tab.png" "$edge"
    done
    magick "$work/$scheme-panel.png" -strip "$ROOT/docs/screenshots/$scheme-panel.png"
done
ls -l "$ROOT"/docs/screenshots/*.png
