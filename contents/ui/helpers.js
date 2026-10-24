// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

.pragma library

// BoM icon_descriptor → Breeze icon name.
//
// The first block is the descriptor set the BoM v1 API actually emits; anything
// outside it falls back to weather-none-available (Breeze's purple "?"), so the
// spelling has to match BoM exactly — it sends "windy", not "wind". Every icon
// named here must also exist in the Breeze applets set; weather-severe-alert
// does not, which is why cyclones point at weather-many-clouds-wind.
var _iconMap = {
    "sunny":               "weather-clear",
    "clear":               "weather-clear",
    "mostly_sunny":        "weather-clear",
    "partly_cloudy":       "weather-few-clouds",
    "cloudy":              "weather-overcast",
    "hazy":                "weather-mist",
    "dusty":               "weather-fog",
    "fog":                 "weather-fog",
    "frost":               "weather-freezing-rain",
    "light_shower":        "weather-showers-scattered",
    "shower":              "weather-showers",
    "heavy_shower":        "weather-showers",
    "light_rain":          "weather-showers-scattered",
    "rain":                "weather-showers",
    "storm":               "weather-storm",
    "snow":                "weather-snow",
    "windy":               "weather-clear-wind",
    "cyclone":             "weather-many-clouds-wind",
    "tropical_cyclone":    "weather-many-clouds-wind",

    // Aliases BoM isn't known to send, kept so a variant spelling still lands
    // on a real icon rather than the fallback.
    "mostly_cloudy":       "weather-clouds",
    "overcast":            "weather-overcast",
    "dust":                "weather-fog",
    "wind":                "weather-clear-wind",
    "heavy_rain":          "weather-showers",
    "thunderstorm":        "weather-storm",
    "light_snow":          "weather-snow-scattered",
    "sleet":               "weather-freezing-rain",
    "hail":                "weather-hail"
}

var _nightOverrides = {
    "weather-clear":             "weather-clear-night",
    "weather-clear-wind":        "weather-clear-wind-night",
    "weather-few-clouds":        "weather-few-clouds-night",
    "weather-showers-scattered": "weather-showers-scattered-night",
    "weather-storm":             "weather-storm-night"
}

function bomIcon(descriptor, isNight) {
    var base = _iconMap[String(descriptor || "").toLowerCase()] || "weather-none-available"
    if (isNight && _nightOverrides[base]) return _nightOverrides[base]
    return base
}

// One word for /bin/sh: double-quoted, with the four characters that stay
// special inside double quotes (\ " ` $) escaped.
function shellQuote(s) {
    return "\"" + String(s == null ? "" : s).replace(/[\\"`$]/g, "\\$&") + "\""
}

// Filesystem path of a file: URL, as Qt.resolvedUrl returns one.
function localPath(url) {
    return decodeURIComponent(String(url).replace(/^file:\/\//, ""))
}

// Only https links are ever opened externally. Warning bodies can only carry
// https links (poll.py's allowlist); this gate on Qt.openUrlExternally keeps
// a file:, javascript: or other scheme from being launched regardless.
function isSafeUrl(url) {
    return /^https:\/\//i.test(String(url == null ? "" : url))
}

function formatTemp(t) {
    var n = Number(t)
    if (t === null || t === undefined || isNaN(n)) return "—"
    return Math.round(n) + "°C"
}

function windStr(speed, dir) {
    if (speed === null || speed === undefined) return "—"
    var s = Math.round(Number(speed))
    return dir ? (dir + " " + s + " km/h") : (s + " km/h")
}

function pressureStr(hpa, tendency) {
    var n = Number(hpa)
    if (hpa === null || hpa === undefined || isNaN(n)) return "—"
    var arrow = { rising: " ↑", falling: " ↓", steady: " →",
                  rising_slowly: " ↗", falling_slowly: " ↘" }
    return Math.round(n) + " hPa" + (arrow[String(tendency || "").toLowerCase()] || "")
}

function shortDay(isoDate) {
    if (!isoDate) return "—"
    var d = new Date(isoDate)
    return isNaN(d.getTime()) ? "—" : ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][d.getDay()]
}

function titleCase(s) {
    return String(s || "").replace(/_/g, " ").replace(/\b\w/g, function(c) { return c.toUpperCase() })
}

// Colour key for temperature (high): "hot" ≥ 35, "warm" ≥ 28, "normal" otherwise
function tempColorKey(celsius) {
    var n = Number(celsius)
    if (isNaN(n)) return "normal"
    if (n >= 35)  return "hot"
    if (n >= 28)  return "warm"
    return "normal"
}

// Rain chance colour key: "heavy" ≥ 70, "moderate" ≥ 40, "low" otherwise
function rainColorKey(chance) {
    var n = Number(chance)
    if (isNaN(n) || n < 10) return "none"
    if (n >= 70) return "heavy"
    if (n >= 40) return "moderate"
    return "low"
}

// Moon phase from date — returns {emoji, name}
// Reference: known new moon 2000-01-06T18:14:00Z; synodic month 29.530588853 days.
// Eight equal bands CENTRED on the principal phase instants (new = 0,
// first quarter = ¼ month, full = ½ month, last quarter = ¾ month) — a real
// full moon must report "Full Moon", not the band that merely starts there.
function moonPhase(date) {
    var knownNewMoon = new Date("2000-01-06T18:14:00Z")
    var synodicMonth = 29.530588853
    var band = synodicMonth / 8
    var daysSince = (date.getTime() - knownNewMoon.getTime()) / 86400000
    var phase = ((daysSince % synodicMonth) + synodicMonth) % synodicMonth
    if (phase < band * 0.5) return {emoji: "🌑", name: "New Moon"}
    if (phase < band * 1.5) return {emoji: "🌒", name: "Waxing Crescent"}
    if (phase < band * 2.5) return {emoji: "🌓", name: "First Quarter"}
    if (phase < band * 3.5) return {emoji: "🌔", name: "Waxing Gibbous"}
    if (phase < band * 4.5) return {emoji: "🌕", name: "Full Moon"}
    if (phase < band * 5.5) return {emoji: "🌖", name: "Waning Gibbous"}
    if (phase < band * 6.5) return {emoji: "🌗", name: "Last Quarter"}
    if (phase < band * 7.5) return {emoji: "🌘", name: "Waning Crescent"}
    return {emoji: "🌑", name: "New Moon"}
}

// The JSON object a fetch script printed, from the executable engine's data
// for its run. Output that isn't one (python3 missing, the script crashed)
// becomes a failure of kind "script" carrying the last stderr line or the
// exit code, so it is reported as what it is, not as a network problem.
function scriptResult(data) {
    try {
        var parsed = JSON.parse(String(data["stdout"] || ""))
        if (parsed !== null && typeof parsed === "object" && !Array.isArray(parsed))
            return parsed
    } catch (e) {
        // Not JSON: reported below.
    }
    var stderr = String(data["stderr"] || "").trim().split("\n").pop()
    return { ok: false, error: "script",
             detail: stderr || ("exit code " + data["exit code"]) }
}

// Whether a poll answered `request` ({query, geohash}, as poll.py echoes
// it) is the poll that would be made now. Polls can overlap (the location
// changed while a lookup was in flight), and a late answer for the old
// location must not be shown, or cached as the new one's.
function isPollFor(request, query, geohash) {
    return !!request && request.query === query && request.geohash === geohash
}

// Whether a radar listing is for the station now shown.
function isRadarFor(result, station) {
    return result.station === station
}

// The radar loop's next frame after `current`, of `count`: the next one for
// which isReady(i) is true, wrapping round. Frames load asynchronously, so on
// a slow connection the first loop would otherwise show the frames still
// loading as blanks. With nothing else loaded it stays on `current`.
function nextLoadedFrame(current, count, isReady) {
    for (var step = 1; step <= count; step++) {
        var i = (current + step) % count
        if (isReady(i)) return i
    }
    return current
}
