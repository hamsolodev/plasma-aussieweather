# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import unittest
from datetime import datetime, timezone

from codeloader import FakeApi, load

poll = load("poll")

# Minimal stand-ins shaped like the BoM v1 API's responses.
SEAFORD_VIC = {"geohash": "r1ppnxx", "name": "Seaford", "state": "VIC"}
SEAFORD_SA = {"geohash": "r1f93cz", "name": "Seaford", "state": "SA"}
NOW = datetime(2026, 10, 24, 1, 0, tzinfo=timezone.utc)


def location_api(geohash, warnings=(), details=None, **overrides):
    """A FakeApi serving one location's endpoints."""
    base = "/locations/" + geohash
    responses = {
        base + "/observations": {"data": {"temp": 17.2}},
        base + "/forecasts/daily": {"data": [{"date": "2026-10-23T13:00:00Z"}] * 8},
        base + "/forecasts/hourly": {"data": [{"time": "2026-10-24T00:00:00Z"}] * 12},
        base + "/warnings": {"data": list(warnings)},
    }
    for wid, detail in (details or {}).items():
        responses["/warnings/" + wid] = {"data": detail}
    responses.update(overrides)
    return FakeApi(responses)


class ResolveTest(unittest.TestCase):

    def test_state_suffix_prefers_that_state(self):
        api = FakeApi({"/locations?search=Seaford": {"data": [SEAFORD_VIC, SEAFORD_SA]}})
        self.assertEqual(poll.resolve(api, "Seaford SA"), ("r1f93c", "Seaford, SA"))

    def test_no_match_is_not_found(self):
        api = FakeApi({"/locations?search=Nowhere": {"data": []}})
        with self.assertRaises(poll.NotFound):
            poll.resolve(api, "Nowhere")


class CollectTest(unittest.TestCase):

    def test_cached_geohash_skips_the_lookup(self):
        api = location_api("r1ppnx")
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW)
        self.assertTrue(out["ok"])
        self.assertNotIn("geohash", out)
        self.assertFalse(any(p.startswith("/locations?") for p in api.requested))

    def test_lookup_reports_the_resolved_location(self):
        api = location_api("r1ppnx", **{"/locations?search=Seaford": {"data": [SEAFORD_VIC]}})
        out = poll.collect(api, "", "Seaford VIC", NOW)
        self.assertEqual(out["geohash"], "r1ppnx")
        self.assertEqual(out["locationName"], "Seaford, VIC")

    def test_forecasts_are_trimmed(self):
        out = poll.collect(location_api("r1ppnx"), "r1ppnx", "Seaford VIC", NOW)
        self.assertEqual(len(out["forecast"]), 7)
        self.assertEqual(len(out["hourly"]), 8)

    def test_warning_detail_is_merged(self):
        summary = {"id": "VIC_X_1", "title": "Flood Warning"}
        api = location_api("r1ppnx", warnings=[summary],
                           details={"VIC_X_1": {"message": "<p>Detail</p>"}})
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW)
        self.assertEqual(out["warnings"][0]["message"], "<p>Detail</p>")
        self.assertEqual(out["warnings"][0]["title"], "Flood Warning")


class CurrentWarningsTest(unittest.TestCase):

    def test_cancelled_and_expired_warnings_are_dropped(self):
        live = {"id": "A", "phase": "renewal", "expiry_time": "2026-10-25T13:30:00Z"}
        cancelled = {"id": "B", "phase": "cancelled", "expiry_time": "2026-10-24T04:16:30Z"}
        expired = {"id": "C", "phase": "update", "expiry_time": "2026-10-24T00:59:59Z"}
        api = location_api("r1ppnx", warnings=[live, cancelled, expired], details={"A": {}})
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW)
        self.assertEqual([w["id"] for w in out["warnings"]], ["A"])
        self.assertNotIn("/warnings/B", api.requested)
        self.assertNotIn("/warnings/C", api.requested)

    def test_warning_without_a_readable_expiry_is_kept(self):
        missing = {"id": "A", "phase": "new"}
        garbled = {"id": "B", "phase": "new", "expiry_time": "soon"}
        api = location_api("r1ppnx", warnings=[missing, garbled], details={"A": {}, "B": {}})
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW)
        self.assertEqual([w["id"] for w in out["warnings"]], ["A", "B"])


if __name__ == "__main__":
    unittest.main()
