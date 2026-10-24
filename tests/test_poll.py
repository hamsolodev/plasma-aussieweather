# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import base64
import struct
import zlib
import contextlib
import http.client
import hashlib
import os
import pathlib
import tempfile
import time
import io
import grp
import json
import pwd
import re
import unittest
from unittest import mock
import urllib.error
import urllib.request
from datetime import datetime, timezone

from codeloader import load

poll = load("poll")

class FakeApi:
    """Stands in for poll.make_get: answers API paths from a dict.

    A value that is an exception instance is raised instead of returned.
    Every path asked for is recorded in .requested.
    """

    def __init__(self, responses):
        self.responses = responses
        self.requested = []

    def __call__(self, path):
        self.requested.append(path)
        if path not in self.responses:
            raise AssertionError("unexpected API request: " + path)
        value = self.responses[path]
        if isinstance(value, Exception):
            raise value
        return value


# Minimal stand-ins shaped like the BoM v1 API's responses.
SEAFORD_VIC = {"geohash": "r1ppnxx", "name": "Seaford", "state": "VIC"}
SEAFORD_SA = {"geohash": "r1f93cz", "name": "Seaford", "state": "SA"}
NOW = datetime(2026, 10, 24, 1, 0, tzinfo=timezone.utc)
# Where warning images go in tests that do not look at them.
_IMAGE_DIR = tempfile.TemporaryDirectory()
IMAGE_DIR = pathlib.Path(_IMAGE_DIR.name)


def tearDownModule():
    _IMAGE_DIR.cleanup()


def location_api(geohash, warnings=(), details=None, **overrides):
    """A FakeApi serving one location's endpoints."""
    base = "/locations/" + geohash
    responses = {
        base + "/observations": {"data": {"temp": 17.2}},
        base + "/forecasts/daily": {"data": [{"date": "2026-10-23T13:00:00Z"}] * 8},
        base + "/forecasts/hourly": {"data": [{"time": "2026-10-24T00:00:00Z"}] * 24},
        base + "/warnings": {"data": list(warnings)},
    }
    for wid, detail in (details or {}).items():
        responses["/warnings/" + wid] = {"data": detail}
    responses.update(overrides)
    return FakeApi(responses)


def http_error(code):
    return urllib.error.HTTPError("https://api.example/x", code, "status %d" % code, {}, io.BytesIO())


def run_main(api, geohash, query):
    """poll.main's JSON output, with API calls answered by API."""
    out = io.StringIO()
    with (mock.patch.object(poll, "make_get", lambda version: api),
          mock.patch.dict(os.environ, {"XDG_CACHE_HOME": _IMAGE_DIR.name}),
          contextlib.redirect_stdout(out)):
        poll.main(["poll.py", "1.8.0", geohash, query])
    return json.loads(out.getvalue())


class ResponseSizeTest(unittest.TestCase):

    def test_oversized_response_is_refused(self):
        class Opener:
            def open(self, request, timeout):
                return io.BytesIO(b" " * (poll.MAX_RESPONSE + 1))
        with mock.patch.object(poll.urllib.request, "build_opener", lambda *handlers: Opener()):
            get = poll.make_get("1.8.0")
            with self.assertRaises(poll.Failure) as caught:
                get("/locations/r1ppnx/observations")
        self.assertEqual(caught.exception.kind, "bad_response")


class RedirectTest(unittest.TestCase):

    def setUp(self):
        self.handler = poll.HttpsOnlyRedirects()
        self.request = urllib.request.Request("https://api.weather.bom.gov.au/v1/x")

    def test_https_redirect_is_followed(self):
        followed = self.handler.redirect_request(
            self.request, None, 302, "Found", {}, "https://api.weather.bom.gov.au/v1/y")
        self.assertEqual(followed.full_url, "https://api.weather.bom.gov.au/v1/y")

    def test_redirect_off_https_is_refused(self):
        for target in ("http://api.weather.bom.gov.au/v1/y", "ftp://x/y", "file:///etc/passwd"):
            with self.assertRaises(urllib.error.HTTPError, msg=target) as caught:
                self.handler.redirect_request(self.request, None, 302, "Found", {}, target)
            caught.exception.close()


class SplitStateTest(unittest.TestCase):

    def test_state_suffix_in_any_case(self):
        self.assertEqual(poll.split_state("Seaford VIC"), ("Seaford", "VIC"))
        self.assertEqual(poll.split_state("seaford vic"), ("seaford", "VIC"))
        self.assertEqual(poll.split_state("  Port  Lincoln   Sa "), ("Port Lincoln", "SA"))

    def test_other_territories(self):
        # BoM files Norfolk, Christmas and the Cocos Islands under "OT".
        self.assertEqual(poll.split_state("Norfolk Island OT"), ("Norfolk Island", "OT"))

    def test_last_word_that_is_not_a_state(self):
        self.assertEqual(poll.split_state("Port Lincoln"), ("Port Lincoln", None))
        self.assertEqual(poll.split_state("Mount Isa"), ("Mount Isa", None))
        self.assertEqual(poll.split_state("WA"), ("WA", None))


class ResolveTest(unittest.TestCase):

    def test_state_suffix_prefers_that_state(self):
        api = FakeApi({"/locations?search=Seaford": {"data": [SEAFORD_VIC, SEAFORD_SA]}})
        self.assertEqual(poll.resolve(api, "Seaford SA"), ("r1f93c", "Seaford, SA"))

    def test_lowercase_state_is_still_a_state(self):
        api = FakeApi({"/locations?search=Seaford": {"data": [SEAFORD_VIC, SEAFORD_SA]}})
        self.assertEqual(poll.resolve(api, "Seaford sa"), ("r1f93c", "Seaford, SA"))

    def test_no_match_in_the_named_state_is_not_found(self):
        api = FakeApi({"/locations?search=Seaford": {"data": [SEAFORD_VIC, SEAFORD_SA]}})
        with self.assertRaises(poll.Failure) as caught:
            poll.resolve(api, "Seaford NSW")
        self.assertEqual(caught.exception.kind, "not_found")

    def test_unknown_suffix_falls_back_to_the_place(self):
        # "Sydney CBD" finds nothing as written; without its last word it
        # does, as it did when any short capitalised suffix was taken for a
        # state.
        sydney = {"geohash": "r3gx2fz", "name": "Sydney", "state": "NSW"}
        api = FakeApi({"/locations?search=Sydney%20CBD": {"data": []},
                       "/locations?search=Sydney": {"data": [sydney]}})
        self.assertEqual(poll.resolve(api, "Sydney CBD"), ("r3gx2f", "Sydney, NSW"))

    def test_dropped_suffix_must_leave_the_place_itself(self):
        # A misspelt place must not become whatever BoM lists first for its
        # first word: "Glen Waverly" is not Glen Alice, NSW.
        glen_alice = {"geohash": "r65t0ez", "name": "Glen Alice", "state": "NSW"}
        api = FakeApi({"/locations?search=Glen%20Waverly": {"data": []},
                       "/locations?search=Glen": {"data": [glen_alice]}})
        with self.assertRaises(poll.Failure) as caught:
            poll.resolve(api, "Glen Waverly")
        self.assertEqual(caught.exception.kind, "not_found")

    def test_dropped_suffix_allows_bom_spelling_out_mount(self):
        # BoM lists "Mt Buller" as Mount Buller.
        buller = {"geohash": "r1u7m0z", "name": "Mount Buller", "state": "VIC"}
        api = FakeApi({"/locations?search=Mt%20Buller%20Village": {"data": []},
                       "/locations?search=Mt%20Buller": {"data": [buller]}})
        self.assertEqual(poll.resolve(api, "Mt Buller Village"), ("r1u7m0", "Mount Buller, VIC"))

    def test_pt_may_be_point_as_well_as_port(self):
        cook = {"geohash": "r1r0v2z", "name": "Point Cook", "state": "VIC"}
        api = FakeApi({"/locations?search=Pt%20Cook%20Village": {"data": []},
                       "/locations?search=Pt%20Cook": {"data": [cook]}})
        self.assertEqual(poll.resolve(api, "Pt Cook Village"), ("r1r0v2", "Point Cook, VIC"))

    def test_abbreviations_do_not_match_other_words(self):
        self.assertFalse(poll.same_place("Mt Eliza", "Mount Martha"))
        self.assertFalse(poll.same_place("Pt Cook", "Pt"))

    def test_too_short_to_search_is_not_found(self):
        # BoM answers a search of fewer than three characters with 403,
        # which would be reported as a failure rather than "not found".
        api = FakeApi({"/locations?search=Pt%20Fairy": {"data": []},
                       "/locations?search=Pt": http_error(403)})
        with self.assertRaises(poll.Failure) as caught:
            poll.resolve(api, "Pt Fairy")
        self.assertEqual((caught.exception.kind, caught.exception.permanent), ("not_found", True))

    def test_api_geohash_is_checked(self):
        bogus = {"geohash": "../../x", "name": "Seaford", "state": "VIC"}
        api = FakeApi({"/locations?search=Seaford": {"data": [bogus]}})
        with self.assertRaises(poll.Failure) as caught:
            poll.resolve(api, "Seaford VIC")
        self.assertEqual(caught.exception.kind, "bad_response")

    def test_no_match_is_not_found(self):
        api = FakeApi({"/locations?search=Nowhere": {"data": []}})
        with self.assertRaises(poll.Failure) as caught:
            poll.resolve(api, "Nowhere")
        self.assertEqual(caught.exception.kind, "not_found")


class ErrorKindTest(unittest.TestCase):

    def test_empty_location_is_permanent_and_asks_nothing(self):
        api = FakeApi({})
        result = run_main(api, "", "   ")
        self.assertEqual((result["ok"], result["error"], result["permanent"]),
                         (False, "no_location", True))
        self.assertEqual(api.requested, [])

    def test_not_found_is_permanent(self):
        result = run_main(FakeApi({"/locations?search=Nowhere": {"data": []}}), "", "Nowhere")
        self.assertEqual((result["error"], result["permanent"], result["detail"]),
                         ("not_found", True, "Nowhere"))

    def test_client_error_is_permanent(self):
        result = run_main(location_api("r1ppnx", **{"/locations/r1ppnx/observations": http_error(403)}),
                          "r1ppnx", "Seaford VIC")
        self.assertEqual((result["error"], result["permanent"]), ("http", True))
        self.assertIn("403", result["detail"])

    def test_server_error_and_rate_limit_are_retried(self):
        for code in (500, 503, 429):
            api = location_api("r1ppnx", **{"/locations/r1ppnx/observations": http_error(code)})
            result = run_main(api, "r1ppnx", "Seaford VIC")
            self.assertEqual((result["error"], result["permanent"]), ("http", False), code)

    def test_a_poll_has_a_deadline(self):
        # A server dripping a byte at a time keeps each read inside its
        # timeout; the whole poll must still end.
        def slow(path):
            time.sleep(10)
        started = time.monotonic()
        with mock.patch.object(poll, "POLL_DEADLINE", 1):
            result = run_main(slow, "r1ppnx", "Seaford VIC")
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual((result["error"], result["permanent"]), ("network", False))

    def test_network_failure_is_retried(self):
        api = location_api("r1ppnx", **{"/locations/r1ppnx/observations":
                                        urllib.error.URLError("Name or service not known")})
        result = run_main(api, "r1ppnx", "Seaford VIC")
        self.assertEqual((result["error"], result["permanent"]), ("network", False))

    def test_empty_location_ignores_a_cached_geohash(self):
        result = run_main(FakeApi({}), "r1ppnx", "")
        self.assertEqual((result["ok"], result["error"]), (False, "no_location"))

    def test_malformed_cached_geohash_is_looked_up_again(self):
        api = location_api("r1ppnx", **{"/locations?search=Seaford": {"data": [SEAFORD_VIC]}})
        result = run_main(api, "r1pp/x", "Seaford VIC")
        self.assertTrue(result["ok"])
        self.assertEqual(result["geohash"], "r1ppnx")


class CollectTest(unittest.TestCase):

    def test_cached_geohash_skips_the_lookup(self):
        api = location_api("r1ppnx")
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW, IMAGE_DIR)
        self.assertTrue(out["ok"])
        self.assertNotIn("locationName", out)
        self.assertFalse(any(p.startswith("/locations?") for p in api.requested))

    def test_result_names_the_request_it_answers(self):
        ok = run_main(location_api("r1ppnx"), "r1ppnx", "Seaford VIC")
        failed = run_main(FakeApi({"/locations?search=Nowhere": {"data": []}}), "", "Nowhere")
        self.assertEqual(ok["request"], {"query": "Seaford VIC", "geohash": "r1ppnx"})
        self.assertEqual(failed["request"], {"query": "Nowhere", "geohash": ""})

    def test_lookup_reports_the_resolved_location(self):
        api = location_api("r1ppnx", **{"/locations?search=Seaford": {"data": [SEAFORD_VIC]}})
        out = poll.collect(api, "", "Seaford VIC", NOW, IMAGE_DIR)
        self.assertEqual(out["geohash"], "r1ppnx")
        self.assertEqual(out["locationName"], "Seaford, VIC")

    def test_failed_extras_are_unknown_not_empty(self):
        api = location_api("r1ppnx", **{"/locations/r1ppnx/forecasts/hourly": http_error(503),
                                        "/locations/r1ppnx/warnings": http_error(503)})
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW, IMAGE_DIR)
        self.assertIsNone(out["hourly"])
        self.assertIsNone(out["warnings"])
        self.assertIn("503", out["warningsError"])

    def test_each_location_keeps_its_own_images(self):
        # Two widgets for two places share the cache directory: one place's
        # poll must not prune the other's maps.
        with tempfile.TemporaryDirectory() as tmp:
            cache = pathlib.Path(tmp)
            warning = {"id": "SA_1", "message": '<img src="%s">' % data_uri("image/png", PNG)}
            adelaide = location_api("r1f93c", warnings=[warning], details={"SA_1": {}})
            out = poll.collect(adelaide, "r1f93c", "Adelaide SA", NOW, cache)
            [saved] = out["warnings"][0]["images"]
            # Older than a poll's own prune would spare, but still in use.
            eleven_minutes_ago = time.time() - 660
            os.utime(saved, (eleven_minutes_ago, eleven_minutes_ago))
            poll.collect(location_api("r1ppnx"), "r1ppnx", "Seaford VIC", NOW, cache)
            self.assertTrue(pathlib.Path(saved).exists())
            self.assertEqual(pathlib.Path(saved).parent,
                             cache / "net.tropism.plasma.aussieweather" / "warnings" / "r1f93c")

    def test_a_former_places_images_go_after_a_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = pathlib.Path(tmp)
            warnings = cache / "net.tropism.plasma.aussieweather" / "warnings"
            old = warnings / "r1f93c"
            recent = warnings / "r4152n"
            for place in (old, recent):
                place.mkdir(parents=True, mode=0o700)
                (place / (hashlib.sha256(place.name.encode()).hexdigest() + ".png")).write_bytes(PNG)
            for f in old.iterdir():
                os.utime(f, (0, 0))
            poll.collect(location_api("r1ppnx"), "r1ppnx", "Seaford VIC", NOW, cache)
            self.assertFalse(old.exists())
            self.assertEqual(len(list(recent.iterdir())), 1)

    def test_former_places_are_left_when_their_parent_is_not_private(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = pathlib.Path(tmp) / "cache"
            elsewhere = pathlib.Path(tmp) / "elsewhere"
            (cache / "net.tropism.plasma.aussieweather").mkdir(parents=True, mode=0o700)
            (elsewhere / "r1ppnz").mkdir(parents=True)
            (cache / "net.tropism.plasma.aussieweather" / "warnings").symlink_to(elsewhere)
            poll.prune_former_places(cache, "r1ppnx")
            self.assertTrue((elsewhere / "r1ppnz").exists())

    def test_hourly_not_offered_is_empty(self):
        api = location_api("rd3het", **{"/locations/rd3het/forecasts/hourly": http_error(404)})
        out = poll.collect(api, "rd3het", "Lord Howe Island NSW", NOW, IMAGE_DIR)
        self.assertEqual(out["hourly"], [])

    def test_forecasts_are_trimmed(self):
        out = poll.collect(location_api("r1ppnx"), "r1ppnx", "Seaford VIC", NOW, IMAGE_DIR)
        self.assertEqual(len(out["forecast"]), 8)
        # More hours than are shown: the widget drops slots that have passed.
        self.assertEqual(len(out["hourly"]), 12)

    def test_warning_detail_is_merged(self):
        summary = {"id": "VIC_X_1", "title": "Flood Warning"}
        api = location_api("r1ppnx", warnings=[summary],
                           details={"VIC_X_1": {"message": "<p>Detail</p>"}})
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW, IMAGE_DIR)
        self.assertEqual(out["warnings"][0]["html"], "<p>Detail</p>")
        self.assertEqual(out["warnings"][0]["title"], "Flood Warning")


class CurrentWarningsTest(unittest.TestCase):

    def test_cancelled_and_expired_warnings_are_dropped(self):
        live = {"id": "A", "phase": "renewal", "expiry_time": "2026-10-25T13:30:00Z"}
        cancelled = {"id": "B", "phase": "cancelled", "expiry_time": "2026-10-24T04:16:30Z"}
        expired = {"id": "C", "phase": "update", "expiry_time": "2026-10-24T00:59:59Z"}
        api = location_api("r1ppnx", warnings=[live, cancelled, expired], details={"A": {}})
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW, IMAGE_DIR)
        self.assertEqual([w["id"] for w in out["warnings"]], ["A"])
        self.assertNotIn("/warnings/B", api.requested)
        self.assertNotIn("/warnings/C", api.requested)

    def test_a_bad_detail_does_not_fail_the_rest(self):
        # The warning still shows, by its summary, whatever went wrong.
        for error in (poll.Failure("bad_response", "too large"),
                      http.client.IncompleteRead(b""), RecursionError()):
            with self.subTest(type(error).__name__):
                api = location_api("r1ppnx", warnings=[{"id": "A", "title": "Flood"},
                                                       {"id": "B", "title": "Wind"}],
                                   details={"A": {}, "B": {}}, **{"/warnings/A": error})
                out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW, IMAGE_DIR)
                self.assertEqual([w["title"] for w in out["warnings"]], ["Flood", "Wind"])

    def test_a_malformed_warning_does_not_fail_the_rest(self):
        api = location_api("r1ppnx", warnings=["junk", {"id": 7, "title": "Flood"},
                                               {"id": "B", "title": "Wind"}],
                           details={"B": {"message": ["not", "text"], "title": 3}})
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW, IMAGE_DIR)
        # A detail's field of the wrong type does not hide the summary's.
        self.assertEqual([w["title"] for w in out["warnings"]], ["Flood", "Wind"])
        self.assertEqual([w["html"] for w in out["warnings"]], ["", ""])

    def test_a_time_without_a_zone_does_not_fail_the_rest(self):
        api = location_api("r1ppnx", warnings=[{"id": "A", "title": "Flood", "expiry_time": "2026-10-25"},
                                               {"id": "B", "title": "Wind",
                                                "expiry_time": "2026-10-25T10:00:00"}])
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW, IMAGE_DIR)
        self.assertEqual([w["title"] for w in out["warnings"]], ["Flood", "Wind"])

    def test_warnings_are_capped(self):
        many = [{"id": "W%d" % i, "phase": "new"} for i in range(poll.MAX_WARNINGS + 10)]
        details = {"W%d" % i: {} for i in range(poll.MAX_WARNINGS + 10)}
        api = location_api("r1ppnx", warnings=many, details=details)
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW, IMAGE_DIR)
        self.assertEqual(len(out["warnings"]), poll.MAX_WARNINGS)
        self.assertEqual(sum(p.startswith("/warnings/") for p in api.requested), poll.MAX_WARNINGS)

    def test_warning_without_a_readable_expiry_is_kept(self):
        missing = {"id": "A", "phase": "new"}
        garbled = {"id": "B", "phase": "new", "expiry_time": "soon"}
        api = location_api("r1ppnx", warnings=[missing, garbled], details={"A": {}, "B": {}})
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW, IMAGE_DIR)
        self.assertEqual([w["id"] for w in out["warnings"]], ["A", "B"])


def png(width, height):
    """The start of a PNG: its signature and IHDR chunk, enough for the
    checks poll.py makes."""
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", len(ihdr)) + b"IHDR" + ihdr
            + struct.pack(">I", zlib.crc32(b"IHDR" + ihdr)))


PNG = png(580, 820)
EPS = b"%!PS-Adobe-3.0 EPSF-3.0\n"


def data_uri(mime, payload):
    return "data:" + mime + ";base64," + base64.b64encode(payload).decode()


class SanitiseHtmlTest(unittest.TestCase):

    def test_bom_markup_survives_without_attributes(self):
        html = ('<div class="product"><h2>Heatwave</h2><p style="x">Hot <b>days</b>.</p>'
                '<ul class="l"><li>one</li></ul><br/></div>')
        self.assertEqual(poll.sanitise(html).html,
                         "<div><h2>Heatwave</h2><p>Hot <b>days</b>.</p><ul><li>one</li></ul><br></div>")

    def test_scripts_styles_and_unknown_tags_are_dropped(self):
        html = '<p>a<script>alert(1)</script><style>p{}</style><iframe src="x">b</iframe>c</p>'
        self.assertEqual(poll.sanitise(html).html, "<p>abc</p>")

    def test_event_handlers_are_dropped(self):
        self.assertEqual(poll.sanitise('<p onclick="x()">t</p>').html, "<p>t</p>")

    def test_only_https_links_survive(self):
        html = ('<a href="https://nt.gov.au/h?a=1&amp;b=2">ok</a>'
                '<a href="javascript:alert(1)">js</a><a href="file:///etc/passwd">f</a>'
                '<a href="http://bom.gov.au">plain</a>')
        self.assertEqual(poll.sanitise(html).html,
                         '<a href="https://nt.gov.au/h?a=1&amp;b=2">ok</a>jsfplain')

    def test_images_leave_the_markup(self):
        # Qt RichText hands a data: image to every image plugin's sniffer
        # (LibRaw claims some PNG-signature data by size alone), so no
        # image stays in the markup; real PNGs are kept aside instead.
        html = ('<p>a<img alt="map" src="%s">b</p>' % data_uri("image/png", PNG)
                + '<img src="https://tracker.example/p.png">'
                + '<img src="%s">' % data_uri("image/png", EPS)
                + '<img src="%s">' % data_uri("image/svg+xml", b"<svg/>")
                + '<img src="data:image/png;base64,!!!">')
        result = poll.sanitise(html)
        self.assertEqual(result.html, "<p>ab</p>")
        self.assertEqual(result.images, [PNG])

    def test_images_must_have_sane_dimensions(self):
        # Qt scales an image to fill its box: a 1×1024 PNG of 89 bytes
        # became a raster of gigabytes inside plasmashell.
        for width, height in ((1, 1024), (1024, 1), (4096, 4096), (0, 10), (2049, 300)):
            html = '<img src="%s">' % data_uri("image/png", png(width, height))
            self.assertEqual(poll.sanitise(html).images, [], (width, height))
        self.assertEqual(len(poll.sanitise('<img src="%s">' % data_uri("image/png", png(580, 820))).images), 1)

    def test_png_needs_its_header(self):
        bare_signature = b"\x89PNG\r\n\x1a\n" + b"\0" * 16
        self.assertEqual(poll.sanitise('<img src="%s">' % data_uri("image/png", bare_signature)).images, [])

    def test_images_are_capped(self):
        html = "".join('<img src="%s">' % data_uri("image/png", PNG + bytes([i]))
                       for i in range(poll.MAX_IMAGES + 3))
        self.assertEqual(len(poll.sanitise(html).images), poll.MAX_IMAGES)

    def test_tables_are_dropped(self):
        # Qt's RichText table layout time doubles with each level of
        # nesting: 20 levels froze the shell for minutes.
        html = "<table><tr><td>" * 20 + "x" + "</td></tr></table>" * 20
        self.assertEqual(poll.sanitise(html).html, "x")

    def test_nesting_is_capped(self):
        html = "<div>" * 50 + "x" + "</div>" * 50
        out = poll.sanitise(html).html
        self.assertEqual(out.count("<div>"), poll.MAX_DEPTH)
        self.assertEqual(out.count("</div>"), poll.MAX_DEPTH)
        self.assertIn("x", out)

    def test_line_break_floods_collapse(self):
        # RichText's layout time grows faster than the number of lines:
        # 240,000 <br> held the GUI for a minute.
        out = poll.sanitise("<p>a" + "<br>" * 100000 + "b</p>").html
        self.assertEqual(out, "<p>a<br><br>b</p>")

    def test_elements_are_capped(self):
        out = poll.sanitise("x<br>" * 100000).html
        self.assertLessEqual(out.count("<br>"), poll.MAX_ELEMENTS)
        # The budget can be overrun by the closing tags of what is open.
        self.assertLessEqual(len(out), poll.MAX_OUTPUT + 100)

    def test_unclosed_tags_cost_linear_time(self):
        # Scanning the open-tag stack on every tag made a megabyte of <b>
        # take tens of minutes.
        started = time.monotonic()
        poll.sanitise("<b>" * 200000 + "</i>" * 200000)
        self.assertLess(time.monotonic() - started, 5)

    def test_plain_text_is_capped_too(self):
        # A warning body with no markup goes through linkify, which must
        # keep to the same budgets.
        out = poll.linkify("a" * (poll.MAX_TEXT * 10))
        self.assertLessEqual(len(out), poll.MAX_OUTPUT)
        links = poll.linkify(" ".join(["https://x.example/%d" % i for i in range(5000)]))
        self.assertLessEqual(links.count("<a "), poll.MAX_ELEMENTS)
        self.assertLessEqual(len(links), poll.MAX_OUTPUT + 100)

    def test_escaping_cannot_overrun_the_budget(self):
        # "&" escapes to five characters: the budget counts what is emitted.
        out = poll.sanitise("<p>" + "&amp;" * 30000 + "</p>").html
        self.assertLessEqual(len(out), poll.MAX_OUTPUT + 100)
        self.assertNotRegex(out, r"&[a-z]*…")

    def test_a_link_cannot_overrun_the_budget(self):
        # A quote escapes to six characters: a 2000-character href, to 12000.
        markup = ("<p>" + "&amp;" * 7000 + "</p><a href='https://x.example/" + '"' * 2000
                  + "'>map</a>")
        self.assertLessEqual(len(poll.sanitise(markup).html), poll.MAX_OUTPUT + 100)

    def test_the_ellipsis_stays_out_of_links(self):
        text = "a" * (poll.MAX_TEXT - 10) + " https://x.example/abcdefghijklmnop"
        out = poll.linkify(text)
        self.assertTrue(out.endswith("…"))
        self.assertNotIn("…", "".join(re.findall(r'href="([^"]*)"', out)))

    def test_clipping_never_splits_an_entity(self):
        self.assertEqual(poll.clip_escaped("ab&#x27;cd", 5), "ab")
        self.assertEqual(poll.clip_escaped("ab&amp;cd", 4), "ab")
        self.assertEqual(poll.clip_escaped("ab&amp;cd", 7), "ab&amp;")

    def test_long_links_are_dropped(self):
        href = "https://x.example/" + "a" * 5000
        self.assertEqual(poll.sanitise('<a href="%s">map</a>' % href).html, "map")

    def test_text_is_capped(self):
        out = poll.sanitise("<p>" + "a" * (poll.MAX_TEXT + 500) + "</p><p>tail</p>").html
        self.assertLessEqual(out.count("a"), poll.MAX_TEXT)
        self.assertNotIn("tail", out)
        self.assertTrue(out.endswith("…</p>"))

    def test_text_stays_escaped(self):
        self.assertEqual(poll.sanitise("<p>a &lt;b&gt; &amp; c</p>").html,
                         "<p>a &lt;b&gt; &amp; c</p>")

    def test_attribute_quotes_cannot_break_out(self):
        html = '<a href=\'https://x.au/"onmouseover="y\'>t</a>'
        self.assertEqual(poll.sanitise(html).html,
                         '<a href="https://x.au/&quot;onmouseover=&quot;y">t</a>')

    def test_unclosed_and_stray_tags_are_balanced(self):
        self.assertEqual(poll.sanitise("<ul><li>x</b></ul></p><p>y").html,
                         "<ul><li>x</li></ul><p>y</p>")


class ImageStoreTest(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = poll.ImageStore(pathlib.Path(self.directory.name), "warnings")

    def tearDown(self):
        self.directory.cleanup()

    def test_images_per_poll_are_capped(self):
        saved = [self.store.save(PNG + i.to_bytes(4, "big")) for i in range(poll.MAX_POLL_IMAGES + 5)]
        self.assertEqual(sum(path is not None for path in saved), poll.MAX_POLL_IMAGES)

    def test_image_bytes_per_poll_are_capped(self):
        size = poll.MAX_IMAGE_BYTES
        saved = [self.store.save(PNG + i.to_bytes(8, "big") + b"\0" * (size - len(PNG) - 8))
                 for i in range(12)]
        kept = sum(path is not None for path in saved)
        self.assertEqual(kept, poll.MAX_POLL_IMAGE_BYTES // size)

    def test_a_symlinked_directory_is_refused(self):
        # Someone who could place the directory could point it anywhere;
        # one poll used to delete every old file in the target.
        victim = pathlib.Path(self.directory.name) / "victim"
        victim.mkdir()
        (victim / "precious").write_text("x")
        os.utime(victim / "precious", (0, 0))
        (pathlib.Path(self.directory.name) / "warnings").symlink_to(victim)
        self.assertIsNone(self.store.save(PNG))
        self.store.prune()
        self.assertTrue((victim / "precious").exists())
        self.assertIn("not a private directory", self.store.problem)

    def test_its_own_directories_are_made_private(self):
        # Made under a umask of 002 (Ubuntu's), or by an older build.
        directory = pathlib.Path(self.directory.name) / "warnings"
        directory.mkdir()
        directory.chmod(0o775)
        self.assertIsNotNone(self.store.save(PNG))
        self.assertEqual(directory.stat().st_mode & 0o777, 0o700)

    def test_a_cache_writable_only_by_the_users_own_group_is_accepted(self):
        # User-private groups: ~/.cache is 775 on Ubuntu, but the group is
        # the user's alone.
        cache = pathlib.Path(self.directory.name)
        cache.chmod(0o775)
        with mock.patch.object(poll, "group_is_private", lambda gid: True):
            self.assertIsNotNone(self.store.save(PNG))
        with mock.patch.object(poll, "group_is_private", lambda gid: False):
            fresh = poll.ImageStore(cache, "other")
            self.assertIsNone(fresh.save(PNG))

    def test_a_group_another_account_belongs_to_by_default_is_not_private(self):
        me = pwd.getpwuid(os.getuid())
        group = grp.struct_group((me.pw_name, "x", me.pw_gid, []))
        other = pwd.struct_passwd(("other", "x", me.pw_uid + 1, me.pw_gid, "", "/", "/bin/sh"))
        with (mock.patch.object(poll.grp, "getgrgid", lambda gid: group),
              mock.patch.object(poll.pwd, "getpwall", lambda: [me, other])):
            self.assertFalse(poll.group_is_private(me.pw_gid))
        with (mock.patch.object(poll.grp, "getgrgid", lambda gid: group),
              mock.patch.object(poll.pwd, "getpwall", lambda: [me])):
            self.assertTrue(poll.group_is_private(me.pw_gid))

    def test_a_file_of_another_user_is_not_reused(self):
        path = self.store.directory / (hashlib.sha256(PNG).hexdigest() + ".png")
        self.store.save(PNG)
        with mock.patch.object(poll.os, "getuid", lambda: os.geteuid() + 1):
            self.assertFalse(poll.ImageStore._holds(path, PNG))

    def test_a_hard_linked_file_is_replaced_not_reused(self):
        # Whoever holds the other link could rewrite what the widget shows.
        path = pathlib.Path(self.store.save(PNG))
        other = pathlib.Path(self.directory.name) / "elsewhere"
        os.link(path, other)
        self.store.save(PNG)
        self.assertNotEqual(path.stat().st_ino, other.stat().st_ino)
        self.assertEqual(path.stat().st_nlink, 1)

    def test_a_symlinked_cache_is_followed(self):
        real = pathlib.Path(self.directory.name) / "real"
        real.mkdir(mode=0o700)
        link = pathlib.Path(self.directory.name) / "link"
        link.symlink_to(real)
        self.assertIsNotNone(poll.ImageStore(link, "warnings").save(PNG))

    def test_prune_reports_nothing(self):
        # Pruning an unusable directory is skipped quietly: only a map that
        # could not be stored is worth telling the user about.
        (pathlib.Path(self.directory.name) / "warnings").symlink_to("/nonexistent")
        self.store.prune()
        self.assertEqual(self.store.problem, "")

    def test_a_directory_others_can_write_is_refused(self):
        # One the widget did not make: the cache itself.
        cache = pathlib.Path(self.directory.name)
        cache.chmod(0o777)
        self.assertIsNone(self.store.save(PNG))
        cache.chmod(0o700)

    def test_a_planted_file_is_replaced_not_reused(self):
        # A file with the expected name but other content (say, TIFF bytes
        # Qt would sniff) must not be shown as the warning's map.
        path = pathlib.Path(self.store.save(PNG))
        path.write_bytes(b"II*\0 not the map")
        os.utime(path, (0, 0))
        self.assertEqual(pathlib.Path(self.store.save(PNG)).read_bytes(), PNG)

    def test_a_fifo_with_the_name_is_replaced(self):
        # Reading a FIFO blocks: Qt's image loader hung on one.
        path = self.store.directory / (hashlib.sha256(PNG).hexdigest() + ".png")
        self.store.directory.mkdir(parents=True)
        os.mkfifo(path)
        self.assertEqual(pathlib.Path(self.store.save(PNG)).read_bytes(), PNG)

    def test_reuse_refreshes_the_files_age(self):
        path = pathlib.Path(self.store.save(PNG))
        os.utime(path, (0, 0))
        self.store.save(PNG)
        self.assertGreater(path.stat().st_mtime, 0)

    def test_prune_leaves_what_it_did_not_make(self):
        self.store.save(PNG)
        foreign = self.store.directory / "notes.txt"
        foreign.write_text("x")
        sub = self.store.directory / "sub"
        sub.mkdir()
        for path in (foreign, sub):
            os.utime(path, (0, 0))
        fresh = poll.ImageStore(pathlib.Path(self.directory.name), "warnings")
        fresh.prune()
        self.assertTrue(foreign.exists())
        self.assertTrue(sub.exists())

    def test_same_image_same_file(self):
        self.assertEqual(self.store.save(PNG), self.store.save(PNG))
        self.assertEqual(len(list(self.store.directory.iterdir())), 1)

    def test_prune_skips_a_file_already_gone(self):
        # Another poll may delete or replace a file mid-prune.
        old = self.store.directory / ("0" * 64 + ".png")
        self.store.directory.mkdir(parents=True)
        old.write_bytes(PNG)
        os.utime(old, (0, 0))
        lstat = pathlib.Path.lstat

        def vanishing_lstat(path):
            if path == old:
                raise FileNotFoundError(path)
            return lstat(path)

        with mock.patch.object(pathlib.Path, "lstat", vanishing_lstat):
            self.store.prune()
        self.assertTrue(old.exists(), "the patch should have hidden it from prune")

    def test_prune_keeps_what_this_poll_saved_and_recent_files(self):
        kept = pathlib.Path(self.store.save(PNG))
        old = self.store.directory / ("0" * 64 + ".png")
        recent = self.store.directory / ("1" * 64 + ".png")
        for path in (old, recent):
            path.write_bytes(PNG)
        os.utime(old, (0, 0))
        self.store.prune()
        self.assertTrue(kept.exists())
        self.assertTrue(recent.exists(), "another poll may have just saved it")
        self.assertFalse(old.exists())


class LinkifyTest(unittest.TestCase):

    def test_plain_text_is_escaped(self):
        self.assertEqual(poll.linkify("storms & gusts <severe>"),
                         "storms &amp; gusts &lt;severe&gt;")

    def test_https_url_becomes_a_link_without_trailing_punctuation(self):
        self.assertEqual(poll.linkify("More at https://bom.gov.au/x?a=1&b=2."),
                         'More at <a href="https://bom.gov.au/x?a=1&amp;b=2">'
                         'https://bom.gov.au/x?a=1&amp;b=2</a>.')

    def test_http_url_stays_text(self):
        self.assertEqual(poll.linkify("see http://bom.gov.au/x"), "see http://bom.gov.au/x")


class WarningViewTest(unittest.TestCase):

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = poll.ImageStore(pathlib.Path(self.directory.name), "warnings")

    def tearDown(self):
        self.directory.cleanup()

    def test_images_are_saved_as_png_files(self):
        view = poll.warning_view([{"id": "A", "message": '<p>Map:</p><img src="%s">'
                                  % data_uri("image/png", PNG)}], self.store)
        self.assertEqual(view["html"], "<p>Map:</p>")
        [path] = view["images"]
        self.assertTrue(path.endswith(".png"))
        self.assertEqual(pathlib.Path(path).read_bytes(), PNG)
        self.assertEqual(pathlib.Path(path).parent, self.store.directory)

    def test_html_message_is_sanitised(self):
        view = poll.warning_view([{"id": "A", "title": "Flood Warning", "phase": "new",
                                   "issue_time": "2026-10-24T00:00:00Z",
                                   "expiry_time": "2026-10-25T00:00:00Z",
                                   "message": "<p>Rising<script>x</script></p>"}], self.store)
        self.assertEqual(view, {"id": "A", "title": "Flood Warning", "phase": "new",
                                "issue_time": "2026-10-24T00:00:00Z",
                                "expiry_time": "2026-10-25T00:00:00Z",
                                "html": "<p>Rising</p>", "images": []})

    def test_summary_without_detail_falls_back(self):
        view = poll.warning_view([{}, {"id": "A", "short_title": "Sheep Graziers Warning"}],
                                 self.store)
        self.assertEqual(view["title"], "Sheep Graziers Warning")
        self.assertEqual(view["html"], "")

    def test_plain_text_body_is_linkified(self):
        view = poll.warning_view([{"id": "A", "text": "See https://bom.gov.au now"}], self.store)
        self.assertEqual(view["html"],
                         'See <a href="https://bom.gov.au">https://bom.gov.au</a> now')


if __name__ == "__main__":
    unittest.main()
