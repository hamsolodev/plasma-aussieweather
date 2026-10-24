#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Check that a committed translation template lists the right strings.

    scripts/check-pot.py COMMITTED.pot REGENERATED.pot

Compares the translatable strings (context, message and plural) of the
two templates, ignoring order, source locations and the header, which
change whenever code moves between files. Fails if a string is missing
from or extra in COMMITTED, or if either template holds no strings.
"""

import ast
import sys

FIELDS = ("msgctxt", "msgid", "msgid_plural")


def entries(path):
    """The set of (msgctxt, msgid, msgid_plural) in the template at PATH."""
    found = set()
    entry = {}
    field = None
    with open(path, encoding="utf-8") as pot:
        for line in list(pot) + [""]:
            line = line.strip()
            if line.startswith('"') and field:
                entry[field] += ast.literal_eval(line)
                continue
            keyword, _, rest = line.partition(" ")
            if keyword in FIELDS:
                field = keyword
                entry[field] = ast.literal_eval(rest)
                continue
            field = None
            if not line and entry:
                if entry.get("msgid"):
                    found.add(tuple(entry.get(f, "") for f in FIELDS))
                entry = {}
    return found


def main(committed, regenerated):
    have, want = entries(committed), entries(regenerated)
    if not have or not want:
        print("FAIL: a template holds no strings: is the path right?", file=sys.stderr)
        return 1
    missing, extra = sorted(want - have), sorted(have - want)
    for entry in missing:
        print(f"missing from {committed}: {entry!r}", file=sys.stderr)
    for entry in extra:
        print(f"no longer in the code: {entry!r}", file=sys.stderr)
    if missing or extra:
        print("FAIL: run translate/merge.sh and commit translate/template.pot", file=sys.stderr)
        return 1
    print(f"OK: {len(want)} strings, as in the code")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__.split("\n\n")[1])
    sys.exit(main(sys.argv[1], sys.argv[2]))
