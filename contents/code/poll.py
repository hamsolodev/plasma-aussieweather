#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fetch one location's weather from the BoM API and print it as JSON.

main.qml runs this through Plasma's executable engine as

    python3 -I poll.py VERSION GEOHASH QUERY

GEOHASH is the cached result of an earlier lookup; when it is empty, QUERY
("Suburb STATE") is resolved first. Every outcome is one JSON object on
stdout carrying "ok"; the exit status is always 0.
"""

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.weather.bom.gov.au/v1"


class NotFound(Exception):
    """A definitive answer that retrying will not change."""


def make_get(version):
    """A GET-and-parse-JSON function for API paths."""
    headers = {
        "User-Agent": "net.tropism.plasma.aussieweather/" + version,
        "Accept": "application/json",
    }

    def get(path):
        request = urllib.request.Request(API + path, headers=headers)
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.load(response)

    return get


def resolve(get, query):
    """Look QUERY up and return (geohash, display name)."""
    parts = query.strip().rsplit(None, 1)
    last = parts[-1] if len(parts) > 1 else ""
    state = last if last.isalpha() and last.isupper() and 2 <= len(last) <= 3 else None
    term = parts[0].strip() if state else query.strip()

    locations = get("/locations?search=" + urllib.parse.quote(term)).get("data", [])
    if not locations:
        raise NotFound("Location not found: " + query)
    if state:
        preferred = [l for l in locations if l.get("state", "").upper() == state.upper()]
        if preferred:
            locations = preferred
    location = locations[0]
    return (location.get("geohash", "")[:6],
            location.get("name", "") + ", " + location.get("state", ""))


def parse_time(value):
    """An API timestamp as an aware datetime, or None if it isn't one."""
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def is_current(warning, now):
    """False once BoM has cancelled the warning or it has expired.

    The API keeps listing a cancelled warning (phase "cancelled") until its
    original expiry, so the phase has to be checked as well as the time.
    """
    if warning.get("phase") == "cancelled":
        return False
    expiry = parse_time(warning.get("expiry_time"))
    return expiry is None or expiry > now


def warnings_for(get, geohash, now):
    """The location's current warnings, each merged with its detail."""
    warnings = []
    for warning in get("/locations/" + geohash + "/warnings").get("data", []):
        if not is_current(warning, now):
            continue
        wid = (warning.get("id") or "").strip()
        if wid:
            try:
                detail = get("/warnings/" + urllib.parse.quote(wid, safe=""))
                warning = dict(warning, **detail.get("data", {}))
            except Exception:
                pass
        warnings.append(warning)
    return warnings


def collect(get, geohash, query, now):
    """Everything the widget shows, as one JSON-ready dict."""
    out = {"ok": True}
    if not geohash:
        geohash, out["locationName"] = resolve(get, query)
        out["geohash"] = geohash
    base = "/locations/" + geohash
    out["observations"] = get(base + "/observations").get("data", {})
    out["forecast"] = get(base + "/forecasts/daily").get("data", [])[:7]
    try:
        out["hourly"] = get(base + "/forecasts/hourly").get("data", [])[:8]
    except Exception:
        out["hourly"] = []
    try:
        out["warnings"] = warnings_for(get, geohash, now)
    except Exception:
        out["warnings"] = []
    return out


def main(argv):
    version, geohash, query = argv[1:4]
    try:
        result = collect(make_get(version), geohash, query, datetime.now(timezone.utc))
    except NotFound as e:
        result = {"ok": False, "permanent": True, "error": str(e)}
    except Exception as e:
        result = {"ok": False, "error": str(e)}
    print(json.dumps(result))


if __name__ == "__main__":
    main(sys.argv)
