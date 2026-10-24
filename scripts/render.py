#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Render the widget's popup offscreen, one PNG per tab, from fixture data.

    scripts/render.py OUTDIR [--scheme light|dark] [--radar-wait SECONDS]

The views are the real ones from contents/ui, fed a synthetic forecast,
inside a plain window (scripts/render.qml) instead of plasmashell. Prints
each tab's popup height, and exits non-zero if QML logged any warning, so
it doubles as a smoke test of the QML that plasmashell would swallow.

The Radar tab is live: it lists frames through radar.py and loads BoM's
images, so it needs the network and differs from run to run.

Needs KDE Plasma 6's QML modules and PySide6 built against the same Qt
(Fedora: python3-pyside6). CI has neither, so this runs locally only.
"""

import argparse
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMES = {"light": "BreezeLight", "dark": "BreezeDark"}
TABS = ["weather", "radar", "warnings"]
# Logged by the offscreen setup itself, not by the widget: KWindowSystem has
# no plugin for the offscreen platform.
EXPECTED_MESSAGES = {"Could not find any platform plugin"}
# The Radar tab is live, and BoM's FTP listing sometimes names a frame its
# web server does not have yet. The widget skips such frames; the harness
# reports them without failing.
LIVE_IMAGE_FAILURE = re.compile(r"QML Image: Error transferring https://www\.bom\.gov\.au/")


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def fixture(now):
    """Weather shaped like poll.py's output, for Seaford VIC at NOW (UTC)."""
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
    return {
        "now": iso(now),
        "locationName": "Seaford, VIC",
        "station": "IDR023",
        "errorText": "",
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
            # Stands in for a warning map, which poll.py saves as a file.
            "images": [str(ROOT / "docs" / "screenshots" / "light-radar.png")],
        }],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("outdir", type=pathlib.Path)
    parser.add_argument("--scheme", choices=sorted(SCHEMES), default="light")
    parser.add_argument("--radar-wait", type=float, default=20.0)
    options = parser.parse_args()

    # The KDE platform theme reads its colours from kdeglobals; a private
    # config home with the chosen Breeze scheme's colours sets light or dark.
    config_home = pathlib.Path(tempfile.mkdtemp(prefix="aussieweather-render-"))
    shutil.copy(f"/usr/share/color-schemes/{SCHEMES[options.scheme]}.colors",
                config_home / "kdeglobals")
    os.environ.update({"XDG_CONFIG_HOME": str(config_home), "QT_QPA_PLATFORM": "offscreen",
                       "QT_QPA_PLATFORMTHEME": "kde", "TZ": "Australia/Melbourne"})

    from PySide6.QtCore import QObject, QTimer, QUrl, qInstallMessageHandler, QtMsgType
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlEngine
    from PySide6.QtQuick import QQuickWindow
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
    engine.rootContext().setContextProperty("fixtureJson", json.dumps(fixture(now)))
    engine.load(str(ROOT / "scripts" / "render.qml"))
    if not engine.rootObjects():
        print("FAIL: render.qml did not load", file=sys.stderr)
        return 1
    window = shiboken6.wrapInstance(shiboken6.getCppPointer(engine.rootObjects()[0])[0], QQuickWindow)
    view = window.findChild(QObject, "fullView")
    tab_bar = next(item for item in view.findChildren(QObject)
                   if item.metaObject().className().startswith("TabBar"))

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
    for index, name in enumerate(TABS):
        tab_bar.setProperty("currentIndex", index)
        settle(options.radar_wait if name == "radar" else 1.0)
        heights[name] = settled_height()
        window.setProperty("height", heights[name])
        settle(0.5)
        path = options.outdir / f"{options.scheme}-{name}.png"
        window.grabWindow().save(str(path))
        print(f"{path}: popup height {heights[name]:.0f}")

    shutil.rmtree(config_home, ignore_errors=True)
    if network:
        print(f"note: {len(network)} radar image(s) failed to load from BoM", file=sys.stderr)
    if problems:
        print(f"FAIL: QML logged {len(problems)} warning(s)", file=sys.stderr)
        return 1
    print(f"OK: {len(TABS)} tabs rendered, no QML warnings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
