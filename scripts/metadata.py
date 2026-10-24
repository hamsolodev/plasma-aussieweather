#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Print one KPlugin field of metadata.json, the package's one record of
its id, version and bug address, for the build scripts.

    scripts/metadata.py Id|Version|BugReportUrl
"""

import json
import pathlib
import sys

METADATA = pathlib.Path(__file__).resolve().parent.parent / "metadata.json"

if len(sys.argv) != 2:
    sys.exit(__doc__.split("\n\n")[1])
print(json.loads(METADATA.read_text())["KPlugin"][sys.argv[1]])
