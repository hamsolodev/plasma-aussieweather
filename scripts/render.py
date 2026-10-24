#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Render the widget's popup offscreen, one PNG per tab, from fixture data.

    scripts/render.py OUTDIR [--scheme light|dark] [--radar-wait SECONDS] [--offline]
                             [--live PLACE [--station ID]] [--scale FACTOR]

The views are the real ones from contents/ui, fed a synthetic forecast,
inside a plain window (scripts/render.qml) instead of plasmashell. With
--live they show BoM's weather for PLACE now instead, fetched by poll.py,
and the radar of --station; scripts/docs-screenshots.sh takes the
README's screenshots this way. --scale renders at that many device pixels
to each pixel. Prints
each tab's popup height, and exits non-zero if QML logged any warning, so
it doubles as a smoke test of the QML that plasmashell would swallow. It
also renders the panel, and runs the real poll.py through WeatherSource
for a widget with no location (which needs no network), failing unless it
says "No location set".

The Radar tab is live: it lists frames through radar.py and loads BoM's
images, so it needs the network and differs from run to run. With
--offline the radar stays inactive, as in a closed popup, and fetches
nothing (CI renders this way).

Then it puts the same poll in again with every string from BoM marked up,
and checks that every text item built shows its text as plain text: this
is what catches a label that would render BoM's data as markup.

Needs KDE Plasma 6's QML modules and PySide6 built against the same Qt
(Fedora: python3-pyside6). CI runs it, offline, in a Fedora container.
"""

import argparse
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zlib
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMES = {"light": "BreezeLight", "dark": "BreezeDark"}
# Text.TextFormat's values.
PLAIN_TEXT, RICH_TEXT, AUTO_TEXT = 0, 1, 2
# Fewer text items than these means the walk missed some: the fixture
# builds 114, 82 of them declared by the widget.
MIN_TEXT_ITEMS = 100
MIN_WIDGET_TEXT_ITEMS = 70
# A poll's fields that are not shown as text: times, icon names, ids, and
# the warning body, which poll.py has sanitised to RichText.
NOT_SHOWN_AS_TEXT = {
    "request", "geohash", "id", "phase", "html", "images", "icon_descriptor", "date",
    "time", "issue_time", "expiry_time", "sunrise_time", "sunset_time",
}
# Each is FullView's <name>Tab index.
TABS = ["weather", "radar", "warnings"]
# Logged by the offscreen setup itself, not by the widget: KWindowSystem has
# no plugin for the offscreen platform, and the KDE platform theme (6.6, as
# in CI's container) notes the software renderer when there is no OpenGL.
EXPECTED_MESSAGES = {
    "Could not find any platform plugin",
    "Warning: fallback to QtQuick software backend.",
}
# The Radar tab is live, and BoM's FTP listing sometimes names a frame its
# web server does not have yet. The widget skips such frames; the harness
# reports them without failing.
LIVE_IMAGE_FAILURE = re.compile(r"QML Image: Error transferring https://www\.bom\.gov\.au/")


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def warning_map(path, width=580, height=420):
    """Write a stand-in warning map to PATH: bands of heat, cool to severe,
    as a PNG (the widget shows warning images from PNG files)."""
    colours = [(255, 238, 170), (255, 200, 120), (245, 140, 80), (210, 60, 50), (140, 20, 40)]
    rows = []
    for y in range(height):
        row = bytearray([0])  # filter: none
        for x in range(width):
            row += bytes(colours[(x + y // 2) * len(colours) // (width + height // 2)])
        rows.append(bytes(row))

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))

    path.write_bytes(b"\x89PNG\r\n\x1a\n"
                     + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
                     + chunk(b"IEND", b""))
    return str(path)


def marked(value):
    """VALUE, a poll or part of one, with every string BoM supplies to be
    shown wrapped in <b>...</b>. A label that renders it as markup shows
    bold text rather than the tags."""
    if isinstance(value, dict):
        return {key: item if key in NOT_SHOWN_AS_TEXT else marked(item)
                for key, item in value.items()}
    if isinstance(value, list):
        return [marked(item) for item in value]
    if isinstance(value, str):
        return "<b>" + value + "</b>"
    return value


def fixture(now, map_path):
    """A poll of Seaford VIC at NOW (UTC), shaped as poll.py prints it,
    with the moment and the radar station to show it at."""
    midnight = datetime(now.year, now.month, now.day, 13, tzinfo=timezone.utc)
    if midnight > now:
        midnight -= timedelta(days=1)
    texts = ["Partly cloudy.", "Shower or two.", "Sunny.", "Rain.", "Possible thunderstorm.",
             "Mostly sunny.", "Cloudy.", "Windy."]
    descriptors = ["partly_cloudy", "light_shower", "sunny", "rain", "storm",
                   "mostly_sunny", "cloudy", "windy"]
    forecast = []
    for day in range(8):
        date = midnight + timedelta(days=day)
        forecast.append({
            "date": iso(date),
            "icon_descriptor": descriptors[day],
            "short_text": texts[day],
            "extended_text": "Partly cloudy. Medium chance of showers, most likely in the "
                             "afternoon. Winds southerly 15 to 25 km/h." if day == 0 else texts[day],
            "temp_max": [24, 19, 31, 17, 36, 22, 20, 18][day],
            "temp_min": [13, 11, 16, 12, 21, 12, 10, 9][day],
            "rain": {"chance": [30, 60, 0, 90, 70, 10, 20, 40][day],
                     "amount": {"min": 0, "max": [1, 4, None, 15, 10, None, 1, 2][day]}},
            "uv": {"category": "veryhigh" if day == 0 else None, "max_index": 8 if day == 0 else None},
            "astronomical": {"sunrise_time": iso(date + timedelta(hours=6, minutes=20)),
                             "sunset_time": iso(date + timedelta(hours=19, minutes=42))},
        })
    hour = now.replace(minute=0, second=0, microsecond=0)
    hourly = []
    for slot in range(12):
        start = hour + timedelta(hours=slot)
        hourly.append({
            "time": iso(start),
            "icon_descriptor": ["partly_cloudy", "partly_cloudy", "light_shower", "shower",
                                "shower", "cloudy", "cloudy", "partly_cloudy", "sunny",
                                "sunny", "mostly_sunny", "sunny"][slot],
            "is_night": False,
            "temp": 21 - slot % 5,
            "temp_feels_like": 19 - slot % 5,
            "relative_humidity": 60 + slot,
            "dew_point": 12,
            "uv": 5,
            "wind": {"speed_kilometre": 20, "direction": "SSW", "gust_speed_kilometre": 33},
            "rain": {"chance": [10, 20, 40, 60, 70, 30, 10, 0, 0, 0, 5, 0][slot],
                     "amount": {"min": 0, "max": 2}},
        })
    poll = {
        "ok": True,
        "request": {"query": "Seaford VIC", "geohash": ""},
        "geohash": "r1ppnx",
        "locationName": "Seaford, VIC",
        "observations": {
            "temp": 21.4, "temp_feels_like": 19.8, "humidity": 64, "rain_since_9am": 0.4,
            "wind": {"speed_kilometre": 22, "direction": "SSW"},
            "gust": {"speed_kilometre": 35},
            "station": {"name": "Frankston (Ballam Park)", "distance": 4300},
        },
        "forecast": forecast,
        "hourly": hourly,
        "warnings": [{
            "id": "VIC_X_1",
            "title": "Severe Thunderstorm Warning for Port Phillip forecast district",
            "phase": "update",
            "issue_time": iso(now - timedelta(hours=1)),
            "expiry_time": iso(now + timedelta(hours=5)),
            "html": "<h2>Severe Thunderstorm Warning</h2><p>For people in <b>Port Phillip</b>."
                    "</p><ul><li>Damaging winds</li><li>Heavy rainfall</li></ul>"
                    '<p>See <a href="https://www.bom.gov.au/vic/warnings/">current '
                    "warnings</a>.</p>",
            "images": [map_path],
        }],
    }
    return {"now": iso(now), "station": "IDR023", "poll": poll}


def live(place, station, now, cache):
    """BoM's weather for PLACE now, as fixture() shapes it: poll.py's
    answer, its warning maps saved under CACHE, shown with the radar
    product STATION."""
    result = subprocess.run([sys.executable, "-I", str(ROOT / "contents" / "code" / "poll.py"),
                             "render", "", place],
                            env=dict(os.environ, XDG_CACHE_HOME=cache),
                            capture_output=True, text=True, timeout=180, check=True)
    poll = json.loads(result.stdout)
    if not poll.get("ok"):
        sys.exit("render: BoM's weather for %s: %s %s" % (place, poll.get("error"), poll.get("detail")))
    return {"now": iso(now), "station": station, "poll": poll}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("outdir", type=pathlib.Path)
    parser.add_argument("--scheme", choices=sorted(SCHEMES), default="light")
    parser.add_argument("--radar-wait", type=float, default=20.0)
    parser.add_argument("--offline", action="store_true",
                        help="keep the radar inactive: no network")
    parser.add_argument("--live", metavar="PLACE",
                        help="show BoM's weather for PLACE now, not the fixture")
    parser.add_argument("--station", default="IDR023",
                        help="the radar product shown with --live (default: Melbourne, 128 km)")
    parser.add_argument("--scale", type=float, default=1.0,
                        help="device pixels to each pixel (default: 1)")
    options = parser.parse_args()

    # The KDE platform theme reads its colours from kdeglobals; a private
    # config home with the chosen Breeze scheme's colours sets light or dark.
    with tempfile.TemporaryDirectory(prefix="aussieweather-render-") as config_home:
        shutil.copy(f"/usr/share/color-schemes/{SCHEMES[options.scheme]}.colors",
                    pathlib.Path(config_home) / "kdeglobals")
        return render(options, config_home)


def render(options, config_home):
    # The software renderer: the same pixels with or without a GPU (CI's
    # container has none, and Qt would warn as it fell back to it).
    os.environ.update({"XDG_CONFIG_HOME": config_home, "QT_QPA_PLATFORM": "offscreen",
                       "QT_QPA_PLATFORMTHEME": "kde", "QT_QUICK_BACKEND": "software",
                       "TZ": "Australia/Melbourne", "QT_SCALE_FACTOR": str(options.scale)})

    from PySide6.QtCore import QMetaObject, QObject, QTimer, QUrl, qInstallMessageHandler, QtMsgType
    from PySide6.QtGui import QGuiApplication, QWindow
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickItem, QQuickWindow
    import shiboken6

    problems = []

    network = []

    def on_message(kind, context, message):
        serious = kind in (QtMsgType.QtWarningMsg, QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg)
        if serious and LIVE_IMAGE_FAILURE.search(message):
            network.append(message)
        elif serious and message not in EXPECTED_MESSAGES:
            problems.append(message)
        print(message, file=sys.stderr)

    qInstallMessageHandler(on_message)

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    # Bare i18n() calls resolve through the root context object, as they do
    # through KLocalizedContext in plasmashell.
    i18n_component = QQmlComponent(engine, QUrl.fromLocalFile(str(ROOT / "scripts" / "render-i18n.qml")))
    i18n = i18n_component.create()
    if i18n is None:
        print("FAIL: render-i18n.qml did not load", file=sys.stderr)
        return 1
    QQmlEngine.setObjectOwnership(i18n, QQmlEngine.ObjectOwnership.CppOwnership)
    engine.rootContext().setContextObject(i18n)
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    if options.live:
        shown = live(options.live, options.station, now, config_home)
    else:
        shown = fixture(now, warning_map(pathlib.Path(config_home) / "warning-map.png"))
    engine.rootContext().setContextProperty("fixtureJson", json.dumps(shown))
    engine.rootContext().setContextProperty(
        "markedFixtureJson", json.dumps(dict(shown, poll=marked(shown["poll"]))))
    engine.rootContext().setContextProperty("liveRadar", not options.offline)
    engine.load(str(ROOT / "scripts" / "render.qml"))
    if not engine.rootObjects():
        print("FAIL: render.qml did not load", file=sys.stderr)
        return 1
    window = shiboken6.wrapInstance(shiboken6.getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    view = window.findChild(QObject, "fullView")

    def settle(seconds):
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(app.quit)
        timer.start(int(seconds * 1000))
        app.exec()

    def settled_height():
        """The popup's implicit height once layout has caught up. Layouts
        resize when the window polishes, before drawing a frame, and an
        offscreen window draws one only for a grab; so grab until the
        height holds still."""
        height = None
        for _ in range(20):
            window.grabWindow()
            settle(0.1)
            previous, height = height, view.property("implicitHeight")
            if height == previous:
                return height
        raise RuntimeError("popup height did not settle")

    options.outdir.mkdir(parents=True, exist_ok=True)
    heights = {}
    for name in TABS:
        view.setProperty("currentTab", view.property(name + "Tab"))
        settle(options.radar_wait if name == "radar" and not options.offline else 1.0)
        heights[name] = settled_height()
        window.setProperty("height", heights[name])
        settle(0.5)
        path = options.outdir / f"{options.scheme}-{name}.png"
        window.grabWindow().save(str(path))
        print(f"{path}: popup height {heights[name]:.0f}")

    panel = shiboken6.wrapInstance(
        shiboken6.getCppPointer(window.findChild(QWindow, "panelWindow"))[0], QQuickWindow)
    path = options.outdir / f"{options.scheme}-panel.png"
    panel.grabWindow().save(str(path))
    print(f"{path}: panel")

    # Every text item, as built from the marked-up poll, shows its text as
    # plain text, but for the sanitised warning body.
    # tests/test_qml_text_format.py checks the source; this catches whatever
    # form it misses. Text items Plasma's components declare inside
    # themselves (a button's label) render AutoText, which the widget
    # cannot change: those pass while their text holds no markup, which
    # AutoText shows as it is, and the source check gives those components
    # only translated text.
    window.setProperty("marked", True)
    settle(1.0)
    rich_text = {"warningBody"}
    widget_ui = QUrl.fromLocalFile(str(ROOT / "contents" / "ui"))

    def declared_by_widget(item):
        context = QQmlEngine.contextForObject(item)
        return context is not None and widget_ui.isParentOf(context.baseUrl())

    def shows_plain_text(item, text_format):
        if item.objectName() in rich_text and declared_by_widget(item):
            return text_format == RICH_TEXT
        if text_format == PLAIN_TEXT:
            return True
        return (text_format == AUTO_TEXT and not declared_by_widget(item)
                and not re.search("[<&]", str(item.property("text"))))

    def everything(*roots):
        """Every object under ROOTS, by object tree and by item tree: a
        Repeater's delegates are in the second only, a popup's contents in
        the first only."""
        found = {}
        pending = list(roots)
        while pending:
            obj = pending.pop()
            key = shiboken6.getCppPointer(obj)[0]
            if key in found:
                continue
            found[key] = obj
            pending.extend(obj.children())
            if obj.inherits("QQuickItem"):
                pending.extend(shiboken6.wrapInstance(key, QQuickItem).childItems())
        return list(found.values())

    text_items = [item for item in everything(window, panel)
                  if item.inherits("QQuickText") or item.inherits("QQuickTextEdit")]
    for item in text_items:
        # Read through the engine: PySide cannot convert the C++ enum.
        text_format = engine.newQObject(item).property("textFormat").toInt()
        if not shows_plain_text(item, text_format):
            problems.append("%s %r renders format %d: %r" % (item.metaObject().className(),
                                                             item.objectName(), text_format,
                                                             str(item.property("text"))[:60]))
    widget_items = sum(map(declared_by_widget, text_items))
    marked_items = sum("<b>" in str(item.property("text")) for item in text_items)
    print("%d text items checked for plain text, %d of them declared by the widget,"
          " %d showing marked-up data" % (len(text_items), widget_items, marked_items))
    if len(text_items) < MIN_TEXT_ITEMS or widget_items < MIN_WIDGET_TEXT_ITEMS:
        problems.append("only %d text items found to check, %d of them the widget's:"
                        " is the walk broken?" % (len(text_items), widget_items))
    if not marked_items:
        problems.append("no text item shows the marked-up poll: is it applied?")

    # The place menu is a single choice: picking the place shown keeps it
    # checked. (A checkable item that is not exclusive unchecks itself.)
    place_items = [item for item in everything(window, panel) if item.objectName() == "placeItem"]
    shown_items = [item for item in place_items if item.property("checked")]
    if len(place_items) != 2 or len(shown_items) != 1:
        problems.append("place menu: %d items, %d checked, not 2 and 1"
                        % (len(place_items), len(shown_items)))
    else:
        QMetaObject.invokeMethod(shown_items[0], "click")
        settle(0.1)
        if shown_items[0].property("checked"):
            print("place menu: picking the place shown keeps it checked")
        else:
            problems.append("place menu: picking the place shown unchecked it")

    # Each WeatherSource's first poll, at start, must run: poll.py answers
    # both of these at once, without the network.
    for name, location, expected in (
            ("unconfiguredWeather", "no location", "No location set. Choose one in the widget's settings."),
            ("configuredWeather", "the location Mt", "Location not found: Mt")):
        weather = window.findChild(QObject, name)
        for _ in range(100):
            if weather.property("errorText"):
                break
            settle(0.1)
        said = weather.property("errorText")
        if said == expected:
            print("WeatherSource with %s ran poll.py: %s" % (location, said))
        else:
            problems.append("WeatherSource with %s said %r, not %r" % (location, said, expected))

    if network:
        print(f"note: {len(network)} radar image(s) failed to load from BoM", file=sys.stderr)
    if problems:
        for problem in problems:
            print("problem: " + problem, file=sys.stderr)
        print(f"FAIL: {len(problems)} problem(s): QML warnings or wrong behaviour", file=sys.stderr)
        return 1
    print(f"OK: {len(TABS)} tabs rendered, no QML warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
