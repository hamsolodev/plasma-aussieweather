# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

import base64
import contextlib
import io
import json
import unittest
import urllib.error
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
        base + "/forecasts/hourly": {"data": [{"time": "2026-10-24T00:00:00Z"}] * 24},
        base + "/warnings": {"data": list(warnings)},
    }
    for wid, detail in (details or {}).items():
        responses["/warnings/" + wid] = {"data": detail}
    responses.update(overrides)
    return FakeApi(responses)


def http_error(code):
    return urllib.error.HTTPError("https://api.example/x", code, "status %d" % code, {}, None)


def run_main(api, geohash, query):
    """poll.main's JSON output, with API calls answered by API."""
    original = poll.make_get
    poll.make_get = lambda version: api
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            poll.main(["poll.py", "1.8.0", geohash, query])
        return json.loads(out.getvalue())
    finally:
        poll.make_get = original


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
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW)
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
        out = poll.collect(api, "", "Seaford VIC", NOW)
        self.assertEqual(out["geohash"], "r1ppnx")
        self.assertEqual(out["locationName"], "Seaford, VIC")

    def test_failed_extras_are_unknown_not_empty(self):
        api = location_api("r1ppnx", **{"/locations/r1ppnx/forecasts/hourly": http_error(503),
                                        "/locations/r1ppnx/warnings": http_error(503)})
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW)
        self.assertIsNone(out["hourly"])
        self.assertIsNone(out["warnings"])
        self.assertIn("503", out["warningsError"])

    def test_hourly_not_offered_is_empty(self):
        api = location_api("rd3het", **{"/locations/rd3het/forecasts/hourly": http_error(404)})
        out = poll.collect(api, "rd3het", "Lord Howe Island NSW", NOW)
        self.assertEqual(out["hourly"], [])

    def test_forecasts_are_trimmed(self):
        out = poll.collect(location_api("r1ppnx"), "r1ppnx", "Seaford VIC", NOW)
        self.assertEqual(len(out["forecast"]), 8)
        # More hours than are shown: the widget drops slots that have passed.
        self.assertEqual(len(out["hourly"]), 12)

    def test_warning_detail_is_merged(self):
        summary = {"id": "VIC_X_1", "title": "Flood Warning"}
        api = location_api("r1ppnx", warnings=[summary],
                           details={"VIC_X_1": {"message": "<p>Detail</p>"}})
        out = poll.collect(api, "r1ppnx", "Seaford VIC", NOW)
        self.assertEqual(out["warnings"][0]["html"], "<p>Detail</p>")
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


PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 16
EPS = b"%!PS-Adobe-3.0 EPSF-3.0\n"


def data_uri(mime, payload):
    return "data:" + mime + ";base64," + base64.b64encode(payload).decode()


class SanitiseHtmlTest(unittest.TestCase):

    def test_bom_markup_survives_without_attributes(self):
        html = ('<div class="product"><h2>Heatwave</h2><p style="x">Hot <b>days</b>.</p>'
                '<ul class="l"><li>one</li></ul><br/></div>')
        self.assertEqual(poll.sanitise_html(html),
                         "<div><h2>Heatwave</h2><p>Hot <b>days</b>.</p><ul><li>one</li></ul><br></div>")

    def test_scripts_styles_and_unknown_tags_are_dropped(self):
        html = '<p>a<script>alert(1)</script><style>p{}</style><iframe src="x">b</iframe>c</p>'
        self.assertEqual(poll.sanitise_html(html), "<p>abc</p>")

    def test_event_handlers_are_dropped(self):
        self.assertEqual(poll.sanitise_html('<p onclick="x()">t</p>'), "<p>t</p>")

    def test_only_https_links_survive(self):
        html = ('<a href="https://nt.gov.au/h?a=1&amp;b=2">ok</a>'
                '<a href="javascript:alert(1)">js</a><a href="file:///etc/passwd">f</a>'
                '<a href="http://bom.gov.au">plain</a>')
        self.assertEqual(poll.sanitise_html(html),
                         '<a href="https://nt.gov.au/h?a=1&amp;b=2">ok</a>jsfplain')

    def test_only_real_png_data_images_survive(self):
        png = data_uri("image/png", PNG)
        html = ('<img alt="map" src="%s">' % png
                + '<img src="https://tracker.example/p.png">'
                + '<img src="%s">' % data_uri("image/png", EPS)
                + '<img src="%s">' % data_uri("image/svg+xml", b"<svg/>")
                + '<img src="data:image/png;base64,!!!">')
        self.assertEqual(poll.sanitise_html(html), '<img src="%s" alt="map">' % png)

    def test_text_stays_escaped(self):
        self.assertEqual(poll.sanitise_html("<p>a &lt;b&gt; &amp; c</p>"),
                         "<p>a &lt;b&gt; &amp; c</p>")

    def test_attribute_quotes_cannot_break_out(self):
        html = '<a href=\'https://x.au/"onmouseover="y\'>t</a>'
        self.assertEqual(poll.sanitise_html(html),
                         '<a href="https://x.au/&quot;onmouseover=&quot;y">t</a>')

    def test_unclosed_and_stray_tags_are_balanced(self):
        self.assertEqual(poll.sanitise_html("<ul><li>x</b></ul></p><p>y"),
                         "<ul><li>x</li></ul><p>y</p>")


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

    def test_html_message_is_sanitised(self):
        view = poll.warning_view({"id": "A", "title": "Flood Warning", "phase": "new",
                                  "issue_time": "2026-10-24T00:00:00Z",
                                  "expiry_time": "2026-10-25T00:00:00Z",
                                  "message": "<p>Rising<script>x</script></p>"})
        self.assertEqual(view, {"id": "A", "title": "Flood Warning", "phase": "new",
                                "issue_time": "2026-10-24T00:00:00Z",
                                "expiry_time": "2026-10-25T00:00:00Z",
                                "html": "<p>Rising</p>"})

    def test_summary_without_detail_falls_back(self):
        view = poll.warning_view({"id": "A", "short_title": "Sheep Graziers Warning"})
        self.assertEqual(view["title"], "Sheep Graziers Warning")
        self.assertEqual(view["html"], "")

    def test_plain_text_body_is_linkified(self):
        view = poll.warning_view({"id": "A", "text": "See https://bom.gov.au now"})
        self.assertEqual(view["html"],
                         'See <a href="https://bom.gov.au">https://bom.gov.au</a> now')


if __name__ == "__main__":
    unittest.main()
