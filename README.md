# Aussie Weather

A KDE Plasma 6 panel widget for Australian weather, sourced from the Bureau
of Meteorology's public API: current conditions, hourly and 7-day forecasts,
UV index, severe weather warnings, and an animated rain radar loop.

> **Unofficial client.** This widget is not affiliated with or endorsed by
> the Australian Bureau of Meteorology. Weather data © Australian Bureau of
> Meteorology. The widget identifies itself to BoM services with a versioned
> User-Agent and polls no faster than every 10 minutes.

## Screenshots

| Weather | Radar | Warnings |
| --- | --- | --- |
| ![Weather tab](docs/screenshots/light-weather.png) | ![Radar tab](docs/screenshots/light-radar.png) | ![Warnings tab](docs/screenshots/light-warnings.png) |
| ![Weather tab, dark](docs/screenshots/dark-weather.png) | ![Radar tab, dark](docs/screenshots/dark-radar.png) | ![Warnings tab, dark](docs/screenshots/dark-warnings.png) |

## Features

- **Panel:** condition icon (day/night switches at actual sunset/sunrise,
  to the minute) + current temperature
- **Weather tab:** current conditions with feels-like, wind/gusts, humidity,
  pressure tendency, rain since 9 am, dew point and cloud cover; next 8 hours
  (hover an hour for feels-like, wind, humidity, UV and rain detail); 7-day
  forecast (hover a day for the meteorologist's extended text); today's
  extended forecast; UV index with category colouring; sunrise/sunset times
  and moon phase (a moon replaces the UV reading at night)
- **Radar tab:** animated rain radar composited from BoM's transparency
  layers, with a frame counter and quick station/range switching — the
  station configured in settings stays the sticky default
- **Warnings tab:** appears only while warnings are current for your
  location; full warning text in a scrollable list, plus a banner on the
  Weather tab
- **Radar stations:** all 68 active BoM radar sites, enumerated with their
  available ranges (512/256/128/64 km), selectable by name — no product IDs
  to look up

## Install

**From the KDE Store:** right-click your panel → *Add Widgets* → *Get New
Widgets* → search "Aussie Weather". *(Listing pending first public release.)*

**From a release package:**

```sh
kpackagetool6 --type Plasma/Applet --install net.tropism.plasma.aussieweather-<version>.plasmoid
# or, if already installed:
kpackagetool6 --type Plasma/Applet --upgrade net.tropism.plasma.aussieweather-<version>.plasmoid
```

**From source:**

```sh
git clone https://github.com/hamsolodev/plasma-aussieweather.git
cd plasma-aussieweather
zip -qr aussieweather.plasmoid metadata.json contents/
kpackagetool6 --type Plasma/Applet --install aussieweather.plasmoid
```

### Runtime requirement

`python3` must be on `PATH`. The widget fetches BoM API data and the radar
frame list via small embedded Python scripts (no third-party Python packages
needed).

## Configuration

- **Location** — free text, `Suburb STATE` form: `Seaford VIC`, `Sydney NSW`.
  The widget resolves it once via the BoM location search and caches the
  result.
- **Radar station** — pick by name; the range list offers only what that
  station publishes. Pick the station nearest your location; smaller ranges
  show more detail.
- **Update interval** — 10–60 minutes (10-minute minimum is also enforced in
  code; BoM observations only update every ~10 minutes, so faster polling
  gains nothing).

## Troubleshooting

- **"Cannot reach BoM" / no data** — check that `python3` runs from a
  terminal and that api.weather.bom.gov.au is reachable. BoM occasionally
  blocks unusual User-Agents; the widget sends
  `net.tropism.plasma.aussieweather/<version>`.
- **Radar shows the base map but no rain frames** — the station may be
  offline for maintenance (BoM rotates outages;
  [check here](http://www.bom.gov.au/australia/radar/about/radar_outages.shtml)).
  Switch to a neighbouring station from the Radar tab's quick picker.
- **Location resolves to the wrong place** — include the state suffix
  (`Springfield QLD` vs `Springfield SA`); the widget filters search results
  by state when one is given.

## Development

```sh
./translate/merge.sh   # regenerate translate/template.pot after string changes
./translate/build.sh   # compile .po → contents/locale (run before packaging)
```

This repo is also consumed as a git submodule by a private multi-widget
repo; the widget package itself is `metadata.json` + `contents/` at the repo
root.

## License

GPL-2.0-or-later. This project is [REUSE](https://reuse.software/) compliant.
