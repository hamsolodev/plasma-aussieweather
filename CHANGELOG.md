# Changelog

## 1.7.3 — 2026-06-25

- Popup now collapses to the visible tab's content height instead of always
  sizing to the tallest tab (replaced StackLayout with ColumnLayout + visible
  bindings)
- BoM button now links to the national forecasts page (`/location/australia`)
  instead of the broken `/vic/` URL

## 1.7.2 — 2026-06-17

- Fix popup expanding to full screen height on first open: the Warnings
  tab's ScrollView was reporting its full unscrolled content height as
  implicitHeight, which StackLayout used to size the popup; suppressed with
  `implicitHeight: 0` so the popup sizes from Weather/Radar content instead,
  and the Warnings tab scrolls within that height as intended

## 1.7.0 — 2026-06-17

- Warning text rendered as HTML instead of escaped plain text, preserving
  BoM formatting (paragraphs, bold headings)
- Links in warning text open in the default browser

## 1.6.4 — 2026-06-16

- Fix radar refetching on every tab switch: the "last refreshed" timestamp
  was only updated when the fetched frames differed from what was already
  loaded, so an unchanged-but-successful poll never advanced it — leaving
  the update-interval gate looking at a stale timestamp and refetching on
  every re-entry to the Radar tab

## 1.6.3 — 2026-06-16

- Radar tab refresh now respects the configured "Update interval" instead
  of refetching every time the tab is reopened; re-entering within the
  interval reuses the already-loaded frames

## 1.6.2 — 2026-06-16

- Radar tab: replaced the redundant station/range title label with a
  "time since last refresh" indicator, since the dropdowns right next to it
  already show the station and range

## 1.6.1 — 2026-06-16

- Fix extended forecast text leaving dead space when content shrinks to fewer lines

## 1.6 — 2026-06-16

- Warning badge on the panel icon shows the count of active warnings for your location
- Exponential backoff on transient poll failures after waking from sleep (5 s → 10 s → 20 s → 40 s → 80 s → 160 s); stale data stays visible during retries

## 1.5 — 2026-06-13 (first public release)

- Public metadata (website, bug tracker, author contact)
- i18n infrastructure: `template.pot`, translation build scripts, fixes to
  strings that were untranslatable (concatenation-built wind gusts, bare
  literals)
- REUSE-compliant licensing (GPL-2.0-or-later, SPDX headers throughout)
- README, changelog, and release documentation

## 1.4 — 2026-06-13

- Radar station list enumerated from BoM's published products: all 68 active
  sites with their available ranges, selectable by name in settings (replaces
  the free-text product-ID field; the old hint text had the range suffixes
  wrong — `IDR022` is Melbourne 256 km, not 64 km)
- Radar tab: loop title and quick station/range picker; quick picks revert to
  the configured station on leaving the tab
- Radar composite rendered in a centred square — never stretched at
  non-square sizes
- Frame counter on the radar loop (identifies the loop start)
- API poll interval floored at 10 minutes
- Renamed from "BoM Weather" to "Aussie Weather" (no affiliation with the
  Bureau of Meteorology)

## 1.3 — 2026-06-12

- Hourly forecast icons show a detail tooltip: feels-like, wind/gusts,
  humidity, dew point, UV, forecast rain amount
- 7-day forecast icons show the day's extended forecast text as a tooltip
- A moon replaces the UV reading at night (UV is always 0 after dark)
- Panel/current icon flips day/night at actual sunset and sunrise
  (minute precision from BoM astronomical times), not at the hour mark

## 1.2 — 2026-06-12

- Dedicated Warnings tab (appears only while warnings are current) with full
  warning text; warning banner on the Weather tab opens it
- Radar: opaque base layer fixes unreadable overlay text on dark themes;
  frames fetched only while the Radar tab is open; animation vertically
  centred
- Location geohash persisted across plasmashell restarts; immediate refresh
  on location change; refresh on wake from sleep
- Versioned User-Agent on all BoM API requests

## 1.1 — 2026-06-11

- Hourly forecast row (next 8 hours)
- Extended forecast text and UV index row
- Sunrise/sunset times and moon phase
- Night-aware icons driven by a minute-resolution clock
- Stable popup height across tab switches

## 1.0 — 2026-06-11

- Initial release: current conditions, 7-day forecast, animated rain radar
  composited from BoM transparency layers, location search, configurable
  poll interval
