#!/usr/bin/env bash

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Run the ruff that requirements-dev.txt pins, with these arguments. CI and
# scripts/hooks/pre-commit both run ruff this way, so they agree. The first
# run installs it, hash-checked, into a venv inside .git, and so does the
# first run after the pin changes.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REQUIREMENTS="$ROOT/requirements-dev.txt"
VENV="$(git -C "$ROOT" rev-parse --absolute-git-dir)/ruff-venv"

if ! cmp -s "$REQUIREMENTS" "$VENV/requirements-dev.txt"; then
    rm -rf "$VENV"
    python3 -I -m venv "$VENV"
    # --only-binary: a wheel, never an sdist built here.
    "$VENV/bin/python" -I -m pip install --quiet --disable-pip-version-check \
        --require-hashes --only-binary :all: -r "$REQUIREMENTS"
    cp "$REQUIREMENTS" "$VENV/requirements-dev.txt"
fi
exec "$VENV/bin/ruff" "$@"
