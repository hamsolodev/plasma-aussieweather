#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Fetch one location's weather from the BoM API and print it as JSON.

ScriptRunner.qml runs this, for WeatherSource, through Plasma's executable
engine as

    python3 -I poll.py VERSION GEOHASH QUERY

GEOHASH is the cached result of an earlier lookup; when it is empty, QUERY
("Suburb STATE") is resolved first. Every outcome is one JSON object on
stdout carrying "ok"; the exit status is always 0.
"""

import base64
import binascii
import collections
import grp
import hashlib
import html
import json
import os
import pathlib
import pwd
import re
import resource
import signal
import stat
import struct
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

API = "https://api.weather.bom.gov.au/v1"
# The largest real response, a heatwave warning with its maps, is 478 KB.
MAX_RESPONSE = 4 * 1024 * 1024
MAX_WARNINGS = 20

# A backstop for anything else a hostile reply could make grow: the script
# runs out of memory, not the machine. It needs under 30 MB resident, and
# about 250 MB of address space, most of it the locale archive.
MEMORY_LIMIT = 512 * 1024 * 1024


def limit_memory():
    """Cap this process's address space at MEMORY_LIMIT."""
    _, hard = resource.getrlimit(resource.RLIMIT_AS)
    limit = MEMORY_LIMIT if hard == resource.RLIM_INFINITY else min(hard, MEMORY_LIMIT)
    resource.setrlimit(resource.RLIMIT_AS, (limit, hard))
# The states and territories as BoM names them; OT is the other
# territories (Norfolk, Christmas and the Cocos Islands).
STATES = {"ACT", "NSW", "NT", "OT", "QLD", "SA", "TAS", "VIC", "WA"}
GEOHASH = re.compile(r"[0-9b-hjkmnp-z]{6}")


# A whole poll's limit. Each read has a 15 s timeout, but a server dripping
# a byte at a time never trips it, and while a poll runs the widget cannot
# start another.
POLL_DEADLINE = 120


class PollTimedOut(BaseException):
    """The poll passed POLL_DEADLINE. A BaseException, so the handlers that
    let one extra fail without the others do not swallow it."""


def _deadline_passed(signum, frame):
    raise PollTimedOut()


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
    if isinstance(error, PollTimedOut):
        return Failure("network", "BoM took too long to answer")
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
            body = response.read(MAX_RESPONSE + 1)
        if len(body) > MAX_RESPONSE:
            raise Failure("bad_response", "a response over %d bytes" % MAX_RESPONSE)
        return json.loads(body)

    return get


def split_state(query):
    """QUERY as (place, state), the state None unless the last word is one.

    The state may be written in any case: "seaford vic" is Seaford, VIC.
    """
    words = query.split()
    if len(words) > 1 and words[-1].upper() in STATES:
        return " ".join(words[:-1]), words[-1].upper()
    return " ".join(words), None


# BoM spells abbreviations out: "Mt Buller" is listed as Mount Buller.
SPELLED_OUT = {"mt": "mount", "st": "saint", "pt": "port"}


def same_place(a, b):
    """Whether two place names are the same, abbreviations aside."""
    def words(name):
        return [SPELLED_OUT.get(word, word) for word in name.lower().split()]
    return words(a) == words(b)


def search(get, place):
    """BoM's locations matching PLACE."""
    return get("/locations?search=" + urllib.parse.quote(place)).get("data", [])


def resolve(get, query):
    """Look QUERY up and return (geohash, display name).

    When QUERY names a state, only places in that state match: "Seaford
    NSW" is not found rather than quietly becoming Seaford, VIC. A last
    word that is not a state and leaves nothing found ("Sydney CBD") is
    dropped, but only a place named what is left will do (abbreviations
    aside): a misspelt "Glen Waverly" is not found, rather than Glen Alice,
    NSW.
    """
    place, state = split_state(query)
    if not place:
        raise Failure("no_location", permanent=True)
    locations = search(get, place)
    if state:
        locations = [l for l in locations if (l.get("state") or "").upper() == state]
    elif not locations and len(place.split()) > 1:
        shorter = place.rsplit(None, 1)[0]
        locations = [l for l in search(get, shorter) if same_place(l.get("name") or "", shorter)]
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
# RichText's layout time grows with the markup, not only the text, so the
# elements and the whole markup are capped too, and runs of line breaks
# collapse to two. At most MAX_STACK open elements are tracked; deeper ones
# are dropped outright.
MAX_ELEMENTS = 1000
MAX_OUTPUT = 40000
MAX_BREAKS = 2
MAX_STACK = 256
MAX_HREF = 2048

PNG_URI_PREFIX = "data:image/png;base64,"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_IMAGE_BYTES = 2 * 1024 * 1024
MAX_IMAGES = 8
# And per poll, across all its warnings.
MAX_POLL_IMAGES = 24
MAX_POLL_IMAGE_BYTES = 16 * 1024 * 1024
# Qt can scale an image up to fill its box: a tiny 1×1024 PNG became a
# raster of gigabytes. Images must be modest, and not extreme in shape.
MAX_IMAGE_SIDE = 2048
MAX_IMAGE_ASPECT = 8

Sanitised = collections.namedtuple("Sanitised", ["html", "images"])


def clip_escaped(escaped, room):
    """Escaped text cut to at most ROOM characters, without splitting an
    entity."""
    if len(escaped) <= room:
        return escaped
    return re.sub(r"&[a-z]*$", "", escaped[:room])


def png_dimensions(data):
    """(width, height) from a PNG's header chunk, or None if it has none."""
    if len(data) < 24 or data[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", data[16:24])


def png_bytes(src):
    """The bytes of a data: URI holding a PNG of sane dimensions, else
    None."""
    if not src.lower().startswith(PNG_URI_PREFIX):
        return None
    payload = "".join(src[len(PNG_URI_PREFIX):].split())
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        return None
    if not data.startswith(PNG_SIGNATURE) or len(data) > MAX_IMAGE_BYTES:
        return None
    size = png_dimensions(data)
    if size is None:
        return None
    width, height = size
    if not (0 < width <= MAX_IMAGE_SIDE and 0 < height <= MAX_IMAGE_SIDE):
        return None
    if max(width, height) > MAX_IMAGE_ASPECT * min(width, height):
        return None
    return data


class _Sanitiser(HTMLParser):

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.images = []
        # Every allowed element still open, as (tag, emitted): one past
        # MAX_DEPTH is tracked but not emitted, so its end tag closes it and
        # not an outer element. depth (emitted ones) and open_count keep each
        # step's bookkeeping constant-time.
        self.stack = []
        self.open_count = collections.Counter()
        self.depth = 0
        self.dropping = 0
        self.text_left = MAX_TEXT
        self.output_left = MAX_OUTPUT
        self.elements_left = MAX_ELEMENTS
        self.breaks = 0
        # Set once a budget is spent: nothing more is emitted, and result()
        # closes what is open.
        self.full = False

    def emit(self, markup):
        self.out.append(markup)
        self.output_left -= len(markup)
        if self.output_left <= 0:
            self.full = True

    def handle_starttag(self, tag, attrs):
        if tag in DROPPED_WITH_CONTENT:
            self.dropping += 1
            return
        if self.dropping or self.full:
            return
        if tag == "img":
            data = png_bytes(dict(attrs).get("src") or "")
            if data is not None and len(self.images) < MAX_IMAGES:
                self.images.append(data)
            return
        if tag not in ALLOWED_TAGS:
            return
        if tag == "br":
            if self.breaks >= MAX_BREAKS:
                return
            self.breaks += 1
        else:
            self.breaks = 0
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if not href.lower().startswith("https://") or len(href) > MAX_HREF:
                return
            start = '<a href="%s">' % html.escape(href, quote=True)
        else:
            start = "<" + tag + ">"
        if tag in VOID_TAGS:
            if self.elements_left > 0:
                self.elements_left -= 1
                self.emit(start)
            return
        if len(self.stack) >= MAX_STACK:
            return
        emitted = self.depth < MAX_DEPTH and self.elements_left > 0
        if emitted:
            self.elements_left -= 1
            self.depth += 1
            self.emit(start)
        self.stack.append((tag, emitted))
        self.open_count[tag] += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in DROPPED_WITH_CONTENT:
            self.dropping = max(0, self.dropping - 1)
            return
        if self.full or not self.open_count[tag]:
            return
        while self.stack:
            closing, emitted = self.stack.pop()
            self.open_count[closing] -= 1
            if emitted:
                self.depth -= 1
                self.emit("</" + closing + ">")
            if closing == tag:
                break

    def handle_data(self, data):
        if self.dropping or self.full:
            return
        if data.strip():
            self.breaks = 0
        if len(data) > self.text_left:
            data = data[:self.text_left] + "…"
            self.full = True
        self.text_left -= len(data)
        if self.text_left <= 0:
            self.full = True
        # Escaping lengthens text ("&" is five characters): the budget is
        # for what is emitted.
        escaped = html.escape(data, quote=False)
        if len(escaped) > self.output_left:
            escaped = clip_escaped(escaped, self.output_left) + "…"
            self.full = True
        self.emit(escaped)

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


CACHE_NAME = "net.tropism.plasma.aussieweather"
IMAGE_NAME = re.compile(r"[0-9a-f]{64}\.png")
TEMP_NAME = re.compile(r"tmp\w+\.tmp")


def user_cache():
    """The user's cache directory: $XDG_CACHE_HOME, else ~/.cache."""
    cache = os.environ.get("XDG_CACHE_HOME") or ""
    return pathlib.Path(cache) if os.path.isabs(cache) else pathlib.Path.home() / ".cache"


def group_is_private(gid):
    """Whether group GID is the user's alone: the user-private group
    Debian, Ubuntu and Fedora give each user, with no other members. Their
    sessions' umask (002) leaves directories group-writable."""
    try:
        group = grp.getgrgid(gid)
        user = pwd.getpwuid(os.getuid())
    except KeyError:
        return False
    return (gid == user.pw_gid and group.gr_name == user.pw_name
            and not set(group.gr_mem) - {user.pw_name})


def private_cache(path, create):
    """Check the user's cache directory, symlinks followed, is the user's
    and nobody else can write to it. Made (0700) if it is missing and
    CREATE. False if missing and not made; PermissionError if not
    private."""
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        info = path.stat()
    except FileNotFoundError:
        return False
    others = info.st_mode & 0o002 or (info.st_mode & 0o020 and not group_is_private(info.st_gid))
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or others:
        raise PermissionError("%s is not a private directory" % path)
    return True


def private_directory(path, create):
    """Check PATH, one of the widget's own directories, is a real directory
    of the user's (not a symlink), and make it 0700: made so if missing and
    CREATE, tightened if a umask of 002 or an older build left it open.
    False if missing and not made; PermissionError if not the user's."""
    if create:
        try:
            path.mkdir(mode=0o700)
        except FileExistsError:
            pass
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise PermissionError("%s is not a private directory" % path)
    if info.st_mode & 0o077:
        path.chmod(0o700)
    return True


class ImageStore:
    """Warning images, as PNG files the widget shows with a QML Image.

    A data: image left in RichText is handed to every image plugin's
    sniffer before the PNG decoder (LibRaw claims some PNG-signature data
    by its size alone); a QML Image of a .png file goes to the PNG decoder.
    Files are named by their content's hash.

    The user's cache must be the user's and nobody else's to write, and the
    widget's directories under it real directories of the user's, kept
    0700: anyone who could place one could point it elsewhere or plant
    files. If not, nothing is stored, and problem says why.
    """

    # An unreferenced file younger than this may belong to a poll still
    # running (the location changed mid-poll), so prune leaves it.
    PRUNE_AFTER = 600

    def __init__(self, cache, *names):
        self.cache = cache
        self.directory = cache.joinpath(*names)
        self._own = [cache.joinpath(*names[:n]) for n in range(1, len(names) + 1)]
        self.kept = set()
        self.saved_bytes = 0
        self.problem = ""

    def _private(self, create):
        """Whether the cache and the widget's directories are private (made
        so if CREATE); raises OSError if not."""
        return private_cache(self.cache, create) and all(
            private_directory(path, create) for path in self._own)

    def save(self, data):
        """Store DATA; its file's path, or None once this poll has saved
        MAX_POLL_IMAGES images or MAX_POLL_IMAGE_BYTES, or if the directory
        is not private (problem says why)."""
        if (len(self.kept) >= MAX_POLL_IMAGES
                or self.saved_bytes + len(data) > MAX_POLL_IMAGE_BYTES):
            return None
        name = hashlib.sha256(data).hexdigest() + ".png"
        path = self.directory / name
        try:
            self._private(create=True)
            if self._holds(path, data):
                os.utime(path)  # still shown: not one for prune
            else:
                with tempfile.NamedTemporaryFile(dir=self.directory, suffix=".tmp",
                                                 delete=False) as f:
                    f.write(data)
                os.replace(f.name, path)
        except OSError as e:
            self.problem = str(e)
            return None
        self.saved_bytes += len(data)
        self.kept.add(name)
        return str(path)

    @staticmethod
    def _holds(path, data):
        """Whether PATH is a regular file holding DATA. Its type is checked
        first: reading a FIFO would block."""
        try:
            return stat.S_ISREG(path.lstat().st_mode) and path.read_bytes() == data
        except FileNotFoundError:
            return False

    def prune(self, older_than=PRUNE_AFTER):
        """Delete the images and leftover temporary files no current
        warning shows, once OLDER_THAN seconds old. Anything else in the
        directory is not ours and is left; a file another poll removes
        meanwhile is skipped. A directory that is missing or not private is
        skipped quietly: housekeeping, not worth an error."""
        try:
            if not self._private(create=False):
                return
        except OSError:
            return
        cutoff = time.time() - older_than
        for path in self.directory.iterdir():
            if path.name in self.kept:
                continue
            if not (IMAGE_NAME.fullmatch(path.name) or TEMP_NAME.fullmatch(path.name)):
                continue
            try:
                info = path.lstat()
                if not stat.S_ISDIR(info.st_mode) and info.st_mtime < cutoff:
                    path.unlink()
            except FileNotFoundError:
                pass


# Another widget may still show a place this one has left, and refreshes
# its images' age each poll, so they go only when a day old.
FORMER_PLACE_AFTER = 24 * 3600


def prune_former_places(cache, geohash):
    """Tidy the image directories of places other than GEOHASH's, removing
    each once empty."""
    try:
        places = [p for p in (cache / CACHE_NAME / "warnings").iterdir()
                  if p.name != geohash and GEOHASH.fullmatch(p.name)]
    except OSError:
        return
    for place in places:
        ImageStore(cache, CACHE_NAME, "warnings", place.name).prune(FORMER_PLACE_AFTER)
        try:
            place.rmdir()
        except OSError:
            pass


HTTPS_URL = re.compile(r'https://[^\s<>"]+')
TRAILING_PUNCTUATION = re.compile(r"[.,;:!?)\]}'\"]+$")
LOOKS_LIKE_HTML = re.compile(r"<[a-z!/]", re.IGNORECASE)


def linkify(text):
    """Plain TEXT as RichText: escaped, with bare https URLs made links.

    Trailing sentence punctuation stays outside the link, so a sentence
    ending in a URL works. It keeps to the budgets of sanitised HTML: at
    most MAX_TEXT of text, MAX_ELEMENTS links and MAX_OUTPUT of markup.
    """
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT] + "…"
    pieces = []
    last = 0
    for links, match in enumerate(HTTPS_URL.finditer(text)):
        if links >= MAX_ELEMENTS:
            break
        url = match.group(0)
        trail = TRAILING_PUNCTUATION.search(url)
        if trail:
            url = url[:trail.start()]
        pieces.append(html.escape(text[last:match.start()], quote=False))
        if len(url) <= MAX_HREF:
            pieces.append('<a href="%s">%s</a>' % (html.escape(url), html.escape(url, quote=False)))
        else:
            pieces.append(html.escape(url, quote=False))
        last = match.start() + len(url)
    pieces.append(html.escape(text[last:], quote=False))
    out = []
    room = MAX_OUTPUT
    for piece in pieces:
        if len(piece) > room:
            out.append("…" if piece.startswith("<a ") else clip_escaped(piece, room) + "…")
            break
        out.append(piece)
        room -= len(piece)
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
        "images": [path for path in map(images.save, pngs) if path],
    }


def warnings_for(get, geohash, now, images):
    """The location's current warnings, each merged with its detail."""
    warnings = []
    for warning in get("/locations/" + geohash + "/warnings").get("data", []):
        if not is_current(warning, now):
            continue
        if len(warnings) >= MAX_WARNINGS:
            break
        wid = (warning.get("id") or "").strip()
        if wid:
            # Without its detail a warning still shows, by its summary's
            # title, so a detail that fails to load or makes no sense is
            # skipped rather than failing every warning.
            try:
                detail = get("/warnings/" + urllib.parse.quote(wid, safe=""))
                warning = dict(warning, **detail.get("data", {}))
            except Exception as e:
                failure_from(e)  # closes an HTTP error's response
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


def collect(get, geohash, query, now, cache):
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
    # Each place's images apart, so two widgets for two places do not prune
    # each other's.
    images = ImageStore(cache, CACHE_NAME, "warnings", geohash)
    try:
        out["warnings"] = warnings_for(get, geohash, now, images)
    except Exception as e:
        out["warnings"] = None
        out["warningsError"] = failure_from(e).detail
    else:
        # Tidying old images is housekeeping: failing at it must not fail
        # the poll.
        try:
            images.prune()
            prune_former_places(cache, geohash)
        except OSError:
            pass
    if images.problem:
        out["imagesError"] = images.problem
    return out


def main(argv):
    version, geohash, query = argv[1:4]
    previous = signal.signal(signal.SIGALRM, _deadline_passed)
    signal.alarm(POLL_DEADLINE)
    try:
        result = collect(make_get(version), geohash, query, datetime.now(timezone.utc),
                         user_cache())
    except (Exception, PollTimedOut) as e:
        failure = failure_from(e)
        result = {"ok": False, "error": failure.kind, "detail": failure.detail,
                  "permanent": failure.permanent}
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)
    # Every result names the request it answers: polls can overlap, and
    # the widget drops answers to a request it would no longer make.
    result["request"] = {"query": query, "geohash": geohash}
    print(json.dumps(result))


if __name__ == "__main__":
    limit_memory()
    main(sys.argv)
