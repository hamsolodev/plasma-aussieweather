// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

.pragma library

// BoM icon_descriptor → Breeze icon name
var _iconMap = {
    "sunny":               "weather-clear",
    "mostly_sunny":        "weather-clear",
    "partly_cloudy":       "weather-few-clouds",
    "mostly_cloudy":       "weather-clouds",
    "cloudy":              "weather-overcast",
    "overcast":            "weather-overcast",
    "hazy":                "weather-mist",
    "fog":                 "weather-fog",
    "frost":               "weather-freezing-rain",
    "light_shower":        "weather-showers-scattered",
    "light_rain":          "weather-showers-scattered",
    "shower":              "weather-showers",
    "rain":                "weather-showers",
    "heavy_shower":        "weather-showers",
    "heavy_rain":          "weather-showers",
    "thunderstorm":        "weather-storm",
    "light_snow":          "weather-snow-scattered",
    "snow":                "weather-snow",
    "sleet":               "weather-freezing-rain",
    "hail":                "weather-hail",
    "dust":                "weather-fog",
    "wind":                "weather-few-clouds",
    "cyclone":             "weather-severe-alert"
}

var _nightOverrides = {
    "weather-clear":             "weather-clear-night",
    "weather-few-clouds":        "weather-few-clouds-night",
    "weather-showers-scattered": "weather-showers-scattered-night",
    "weather-storm":             "weather-storm-night"
}

function bomIcon(descriptor, isNight) {
    var base = _iconMap[String(descriptor || "").toLowerCase()] || "weather-none-available"
    if (isNight && _nightOverrides[base]) return _nightOverrides[base]
    return base
}

// HTML-escape so external text can't inject markup when shown as RichText.
function escapeHtml(s) {
    return String(s == null ? "" : s)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
}

// Only http/https are ever opened externally — gate Qt.openUrlExternally with
// this so a crafted link (file:, javascript:, …) can't be launched.
function isSafeUrl(url) {
    return /^https?:\/\//i.test(String(url == null ? "" : url))
}

// Turn plain warning text into RichText-safe HTML: everything is escaped, and
// bare http(s) URLs become <a> links (the only markup we emit). Trailing
// sentence punctuation is kept outside the link so "see http://x.au." works.
function linkify(s) {
    var text = String(s == null ? "" : s)
    var re = /https?:\/\/[^\s<>"]+/gi
    var out = ""
    var last = 0
    var m
    while ((m = re.exec(text)) !== null) {
        var url = m[0]
        var trail = ""
        var tm = url.match(/[.,;:!?)\]}'"]+$/)
        if (tm) {
            trail = url.slice(url.length - tm[0].length)
            url = url.slice(0, url.length - tm[0].length)
        }
        out += escapeHtml(text.slice(last, m.index))
        var esc = escapeHtml(url)
        out += '<a href="' + esc + '">' + esc + '</a>'
        out += escapeHtml(trail)
        last = m.index + m[0].length
    }
    out += escapeHtml(text.slice(last))
    return out
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
