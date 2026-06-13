# Changelog

## 1.5 — unreleased (first public release)

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
