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

import base64
import binascii
import collections
import hashlib
import html
import json
import os
import pathlib
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

API = "https://api.weather.bom.gov.au/v1"
# The states and territories as BoM names them; OT is the other
# territories (Norfolk, Christmas and the Cocos Islands).
STATES = {"ACT", "NSW", "NT", "OT", "QLD", "SA", "TAS", "VIC", "WA"}
GEOHASH = re.compile(r"[0-9b-hjkmnp-z]{6}")


class Failure(Exception):
    """A failed poll, of a kind the widget words for the user.

    no_location and not_found mean the configured location needs changing;
    http that BoM answered with an error status; network that BoM could
    not be reached; bad_response that its answer was not what this script
    expects. A permanent failure is not retried: asking again would get
    the same answer.
    """

    def __init__(self, kind, detail="", permanent=False):
        super().__init__(detail)
        self.kind = kind
        self.detail = detail
        self.permanent = permanent


def failure_from(error):
    """ERROR as a Failure."""
    if isinstance(error, Failure):
        return error
    if isinstance(error, urllib.error.HTTPError):
        error.close()  # it holds the response
        # A client error will not change on retry; rate limiting will.
        permanent = 400 <= error.code < 500 and error.code != 429
        return Failure("http", "HTTP %d %s" % (error.code, error.reason), permanent)
    if isinstance(error, OSError):
        return Failure("network", str(getattr(error, "reason", error)))
    return Failure("bad_response", "%s: %s" % (type(error).__name__, error))


class HttpsOnlyRedirects(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only to another https URL.

    The API is https; a redirect to http (or any other scheme) would drop
    TLS for the rest of the exchange.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.lower().startswith("https://"):
            raise urllib.error.HTTPError(newurl, code, "redirect off https refused", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def make_get(version):
    """A GET-and-parse-JSON function for API paths."""
    headers = {
        "User-Agent": "net.tropism.plasma.aussieweather/" + version,
        "Accept": "application/json",
    }
    opener = urllib.request.build_opener(HttpsOnlyRedirects)

    def get(path):
        request = urllib.request.Request(API + path, headers=headers)
        with opener.open(request, timeout=15) as response:
            return json.load(response)

    return get


def split_state(query):
    """QUERY as (place, state), the state None unless the last word is one.

    The state may be written in any case: "seaford vic" is Seaford, VIC.
    """
    words = query.split()
    if len(words) > 1 and words[-1].upper() in STATES:
        return " ".join(words[:-1]), words[-1].upper()
    return " ".join(words), None


def search(get, place):
    """BoM's locations matching PLACE."""
    return get("/locations?search=" + urllib.parse.quote(place)).get("data", [])


def resolve(get, query):
    """Look QUERY up and return (geohash, display name).

    When QUERY names a state, only places in that state match: "Seaford
    NSW" is not found rather than quietly becoming Seaford, VIC. A last
    word that is not a state and leaves nothing found ("Sydney CBD") is
    dropped and the place searched again.
    """
    place, state = split_state(query)
    if not place:
        raise Failure("no_location", permanent=True)
    locations = search(get, place)
    if state:
        locations = [l for l in locations if (l.get("state") or "").upper() == state]
    elif not locations and len(place.split()) > 1:
        locations = search(get, place.rsplit(None, 1)[0])
    if not locations:
        raise Failure("not_found", query.strip(), permanent=True)
    location = locations[0]
    geohash = (location.get("geohash") or "")[:6]
    if not GEOHASH.fullmatch(geohash):
        raise Failure("bad_response", "location without a geohash")
    return geohash, location.get("name", "") + ", " + location.get("state", "")


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


# Warning bodies are shown as Qt RichText, which fetches <img> sources, hands
# every image to whichever decoder sniffs it, and lays nested tables out in
# time that doubles with each level. So the HTML BoM sends is rebuilt from
# this allowlist rather than passed through: links survive only as https,
# nesting and text are capped, and images leave the markup (see ImageStore).
ALLOWED_TAGS = {
    "a", "b", "br", "div", "em", "h1", "h2", "h3", "h4", "h5", "h6", "hr",
    "i", "li", "ol", "p", "pre", "span", "strong", "sub", "sup", "u", "ul",
}
VOID_TAGS = {"br", "hr"}
DROPPED_WITH_CONTENT = {"script", "style"}
MAX_DEPTH = 8
MAX_TEXT = 20000

PNG_URI_PREFIX = "data:image/png;base64,"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGES = 8

Sanitised = collections.namedtuple("Sanitised", ["html", "images"])


def png_bytes(src):
    """The bytes of a data: URI holding a PNG, else None."""
    if not src.lower().startswith(PNG_URI_PREFIX):
        return None
    payload = "".join(src[len(PNG_URI_PREFIX):].split())
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not data.startswith(PNG_SIGNATURE) or len(data) > MAX_IMAGE_BYTES:
        return None
    return data


class _Sanitiser(HTMLParser):

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.images = []
        # Every allowed element still open, as (tag, emitted): one past
        # MAX_DEPTH is tracked but not emitted, so its end tag closes it and
        # not an outer element.
        self.stack = []
        self.dropping = 0
        self.text_left = MAX_TEXT

    def depth(self):
        return sum(emitted for _, emitted in self.stack)

    def handle_starttag(self, tag, attrs):
        if tag in DROPPED_WITH_CONTENT:
            self.dropping += 1
            return
        if self.dropping or self.text_left <= 0:
            return
        if tag == "img":
            data = png_bytes(dict(attrs).get("src") or "")
            if data is not None and len(self.images) < MAX_IMAGES:
                self.images.append(data)
            return
        if tag not in ALLOWED_TAGS:
            return
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if not href.lower().startswith("https://"):
                return
            start = '<a href="%s">' % html.escape(href, quote=True)
        else:
            start = "<" + tag + ">"
        if tag in VOID_TAGS:
            self.out.append(start)
            return
        emitted = self.depth() < MAX_DEPTH
        if emitted:
            self.out.append(start)
        self.stack.append((tag, emitted))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in DROPPED_WITH_CONTENT:
            self.dropping = max(0, self.dropping - 1)
            return
        if self.text_left <= 0 or all(t != tag for t, _ in self.stack):
            return
        while self.stack:
            closing, emitted = self.stack.pop()
            if emitted:
                self.out.append("</" + closing + ">")
            if closing == tag:
                break

    def handle_data(self, data):
        if self.dropping or self.text_left <= 0:
            return
        if len(data) > self.text_left:
            data = data[:self.text_left] + "…"
        self.text_left -= len(data)
        self.out.append(html.escape(data, quote=False))

    def result(self):
        self.close()
        closing = "".join("</" + t + ">" for t, emitted in reversed(self.stack) if emitted)
        return Sanitised("".join(self.out) + closing, self.images)


def sanitise(markup):
    """MARKUP rebuilt from the allowlist, safe to show as RichText, and the
    PNG images taken out of it."""
    sanitiser = _Sanitiser()
    sanitiser.feed(markup)
    return sanitiser.result()


class ImageStore:
    """Warning images, as PNG files the widget shows with a QML Image.

    A data: image left in RichText is handed to every image plugin's
    sniffer before the PNG decoder (LibRaw claims some PNG-signature data
    by its size alone); a QML Image of a .png file goes to the PNG decoder.
    Files are named by their content's hash, so a poll rewrites nothing.
    """

    # An unreferenced file younger than this may belong to a poll still
    # running (the location changed mid-poll), so prune leaves it.
    PRUNE_AFTER = 600

    def __init__(self, directory):
        self.directory = directory
        self.kept = set()

    def save(self, data):
        """Store DATA; its file's path."""
        path = self.directory / (hashlib.sha256(data).hexdigest() + ".png")
        if not path.exists():
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=self.directory, suffix=".tmp", delete=False) as f:
                f.write(data)
            os.replace(f.name, path)
        self.kept.add(path.name)
        return str(path)

    def prune(self):
        """Delete files no current warning shows."""
        if not self.directory.is_dir():
            return
        cutoff = time.time() - self.PRUNE_AFTER
        for path in self.directory.iterdir():
            if path.name not in self.kept and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)


def image_store():
    """The ImageStore under the user's cache directory."""
    cache = os.environ.get("XDG_CACHE_HOME") or ""
    base = pathlib.Path(cache) if os.path.isabs(cache) else pathlib.Path.home() / ".cache"
    return ImageStore(base / "net.tropism.plasma.aussieweather" / "warnings")


HTTPS_URL = re.compile(r'https://[^\s<>"]+')
TRAILING_PUNCTUATION = re.compile(r"[.,;:!?)\]}'\"]+$")
LOOKS_LIKE_HTML = re.compile(r"<[a-z!/]", re.IGNORECASE)


def linkify(text):
    """Plain TEXT as RichText: escaped, with bare https URLs made links.

    Trailing sentence punctuation stays outside the link, so a sentence
    ending in a URL works.
    """
    out = []
    last = 0
    for match in HTTPS_URL.finditer(text):
        url = match.group(0)
        trail = TRAILING_PUNCTUATION.search(url)
        if trail:
            url = url[:trail.start()]
        out.append(html.escape(text[last:match.start()], quote=False))
        out.append('<a href="%s">%s</a>' % (html.escape(url), html.escape(url, quote=False)))
        last = match.start() + len(url)
    out.append(html.escape(text[last:], quote=False))
    return "".join(out)


def warning_view(warning, images):
    """The fields of a warning the widget shows: its body as safe RichText,
    and the paths of its images, saved in the ImageStore IMAGES."""
    body = warning.get("message") or warning.get("text") or warning.get("description") or ""
    if LOOKS_LIKE_HTML.search(body):
        body_html, pngs = sanitise(body)
    else:
        body_html, pngs = linkify(body), []
    return {
        "id": warning.get("id", ""),
        "title": warning.get("title") or warning.get("short_title") or "",
        "phase": warning.get("phase", ""),
        "issue_time": warning.get("issue_time", ""),
        "expiry_time": warning.get("expiry_time", ""),
        "html": body_html,
        "images": [images.save(png) for png in pngs],
    }


def warnings_for(get, geohash, now, images):
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
        warnings.append(warning_view(warning, images))
    return warnings


def hourly_for(get, geohash):
    """The hourly forecast; empty where BoM offers none.

    BoM answers 404 for the external territories (Lord Howe, Norfolk,
    Christmas and Cocos Islands), which have daily forecasts only.
    """
    try:
        return get("/locations/" + geohash + "/forecasts/hourly").get("data", [])
    except urllib.error.HTTPError as e:
        if e.code == 404:
            e.close()
            return []
        raise


def collect(get, geohash, query, now, images):
    """Everything the widget shows, as one JSON-ready dict."""
    if not query.strip():
        raise Failure("no_location", permanent=True)
    out = {"ok": True}
    if not GEOHASH.fullmatch(geohash):
        geohash = ""
    if not geohash:
        geohash, out["locationName"] = resolve(get, query)
    out["geohash"] = geohash
    base = "/locations/" + geohash
    out["observations"] = get(base + "/observations").get("data", {})
    # One more day than the widget shows: just after local midnight BoM
    # can still list the day that ended, which the widget skips.
    out["forecast"] = get(base + "/forecasts/daily").get("data", [])[:8]
    # The hourly forecast and warnings are extras: if one fails, the rest is
    # still worth showing. None means unknown, so the widget keeps what it
    # had; an empty list would mean there are none.
    try:
        # More than the widget shows: it drops slots that have passed
        # before the next poll.
        out["hourly"] = hourly_for(get, geohash)[:12]
    except Exception as e:
        out["hourly"] = None
        out["hourlyError"] = failure_from(e).detail
    try:
        out["warnings"] = warnings_for(get, geohash, now, images)
        images.prune()
    except Exception as e:
        out["warnings"] = None
        out["warningsError"] = failure_from(e).detail
    return out


def main(argv):
    version, geohash, query = argv[1:4]
    try:
        result = collect(make_get(version), geohash, query, datetime.now(timezone.utc),
                         image_store())
    except Exception as e:
        failure = failure_from(e)
        result = {"ok": False, "error": failure.kind, "detail": failure.detail,
                  "permanent": failure.permanent}
    # Every result names the request it answers: polls can overlap, and
    # the widget drops answers to a request it would no longer make.
    result["request"] = {"query": query, "geohash": geohash}
    print(json.dumps(result))


if __name__ == "__main__":
    main(sys.argv)
