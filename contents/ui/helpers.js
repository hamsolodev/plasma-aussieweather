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


// A condition descriptor as it should read at the time: BoM calls a clear
// night slot "sunny", which reads wrong beside a moon.
var _nightConditions = { "sunny": "clear", "mostly_sunny": "mostly_clear" }

function conditionKey(descriptor, isNight) {
    var key = String(descriptor || "")
    return (isNight && _nightConditions[key]) || key
}

// Keywords in a forecast's first sentence → descriptor, first match wins, so
// "Partly cloudy. Medium chance of a shower or two." is partly cloudy.
var _textDescriptors = [
    [/thunder|storm/,                                     "storm"],
    [/shower or two|few showers|possible shower|drizzle/, "light_shower"],
    [/shower/,                                            "shower"],
    [/rain/,                                              "rain"],
    [/snow/,                                              "snow"],
    [/frost/,                                             "frost"],
    [/fog/,                                               "fog"],
    [/haz|smoke/,                                         "hazy"],
    [/dust/,                                              "dusty"],
    [/wind/,                                              "windy"],
    [/partly cloudy/,                                     "partly_cloudy"],
    [/mostly sunny/,                                      "mostly_sunny"],
    [/cloud|overcast/,                                    "cloudy"],
    [/sunny|fine|clear/,                                  "sunny"]
]

// The icon descriptor of a forecast entry. BoM leaves it null for the
// external territories (Lord Howe, Norfolk, Christmas and Cocos Islands),
// whose forecasts carry only short_text, so it is read from that instead.
// "" when there is nothing to go on.
function iconDescriptor(entry) {
    if (!entry) return ""
    if (entry.icon_descriptor) return entry.icon_descriptor
    var sentence = String(entry.short_text || "").toLowerCase().split(".")[0]
    for (var i = 0; i < _textDescriptors.length; i++)
        if (_textDescriptors[i][0].test(sentence)) return _textDescriptors[i][1]
    return ""
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

// A file: URL for an absolute path, each segment percent-encoded so a
// space, # or ? in a directory name stays part of the path.
function fileUrl(path) {
    return "file://" + String(path).split("/").map(encodeURIComponent).join("/")
}

// Only https links are ever opened externally. Warning bodies can only carry
// https links (poll.py's allowlist); this gate on Qt.openUrlExternally keeps
// a file:, javascript: or other scheme from being launched regardless.
function isSafeUrl(url) {
    return /^https:\/\//i.test(String(url == null ? "" : url))
}

// Whether an API field holds a reading. BoM sends null for one a station
// did not take, and that must not show as 0.
function hasValue(v) {
    return v !== null && v !== undefined
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

// The weekday (0 = Sunday) of a daily forecast, where it is forecast for.
// BoM dates each day by the location's local midnight, given in UTC (VIC in
// daylight time: 13:00Z the day before), so the system time zone's weekday
// is wrong wherever it is behind the location's. Noon local time is that
// instant plus 12 hours, which lands on the right UTC date for every offset
// from +0 to +12 (Australia spans +6:30 to +12). -1 if unparseable.
function forecastWeekday(isoDate) {
    var ms = Date.parse(isoDate)
    if (isNaN(ms)) return -1
    return new Date(ms + 12 * 3600000).getUTCDay()
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

// An entry's chance of rain in percent; null when BoM gives none.
function rainChance(entry) {
    return entry && entry.rain && hasValue(entry.rain.chance) ? entry.rain.chance : null
}

// Rain chance colour key: "heavy" ≥ 70, "moderate" ≥ 40, "low" otherwise
function rainColorKey(chance) {
    var n = Number(chance)
    if (isNaN(n) || n < 10) return "none"
    if (n >= 70) return "heavy"
    if (n >= 40) return "moderate"
    return "low"
}

// BoM's UV category as one of low, moderate, high, veryhigh or extreme, or
// "" when missing or unrecognised. BoM sends "veryhigh"; "very_high" and
// "Very High" are accepted too.
var _uvKeys = ["low", "moderate", "high", "veryhigh", "extreme"]

function uvKey(category) {
    var key = String(category || "").toLowerCase().replace(/[\s_]/g, "")
    return _uvKeys.indexOf(key) >= 0 ? key : ""
}

// Moon phase from date — returns {emoji, key}; the widget names the phase.
// Reference: known new moon 2000-01-06T18:14:00Z; synodic month 29.530588853 days.
// Eight equal bands CENTRED on the principal phase instants (new = 0,
// first quarter = ¼ month, full = ½ month, last quarter = ¾ month) — a real
// full moon must report "full", not the band that merely starts there.
var _moonPhases = [
    {emoji: "🌑", key: "new"},
    {emoji: "🌒", key: "waxing_crescent"},
    {emoji: "🌓", key: "first_quarter"},
    {emoji: "🌔", key: "waxing_gibbous"},
    {emoji: "🌕", key: "full"},
    {emoji: "🌖", key: "waning_gibbous"},
    {emoji: "🌗", key: "last_quarter"},
    {emoji: "🌘", key: "waning_crescent"}
]

function moonPhase(date) {
    var knownNewMoon = new Date("2000-01-06T18:14:00Z")
    var synodicMonth = 29.530588853
    var band = synodicMonth / 8
    var daysSince = (date.getTime() - knownNewMoon.getTime()) / 86400000
    var phase = ((daysSince % synodicMonth) + synodicMonth) % synodicMonth
    return _moonPhases[Math.floor(phase / band + 0.5) % 8]
}

// Qt time format for a clock time: the locale's 12- or 24-hour clock.
function clockFormat(use24Hour) {
    return use24Hour ? "HH:mm" : "h:mmap"
}

// The hour a time falls in, counted in UTC hours. BoM's hourly slots start
// on UTC hours, so this matches a time to its slot in half-hour time zones
// too.
function hourBucket(ms) {
    return Math.floor(ms / 3600000)
}

// The hourly entries from the one now falls in onwards. Past slots stay in
// the list until the next poll, an hour away at the longest interval and
// longer while polls fail.
function upcomingSlots(hourly, nowMs) {
    var now = hourBucket(nowMs)
    return (hourly || []).filter(function(h) {
        return hourBucket(Date.parse(h.time)) >= now
    })
}

// The hourly entry for the hour now falls in, or null. Only that hour's
// slot describes now: while polls fail the list ages, and the last slot
// left may be hours old.
function currentSlot(hourly, nowMs) {
    var now = hourBucket(nowMs)
    var list = hourly || []
    for (var i = 0; i < list.length; i++)
        if (hourBucket(Date.parse(list[i].time)) === now) return list[i]
    return null
}

// The warnings not yet expired at nowMs. One with no readable expiry time
// is kept. poll.py drops expired warnings, but the widget keeps showing the
// last list through a failed fetch, so time has to be checked here too.
function unexpired(warnings, nowMs) {
    return (warnings || []).filter(function(w) {
        var expiry = Date.parse(w.expiry_time)
        return isNaN(expiry) || expiry > nowMs
    })
}

// Qt time format for an hourly slot's label: the hour alone when the slot
// starts on the hour locally, with minutes when it does not (UTC-hour slots
// start at half past in SA, the NT, Broken Hill and the Cocos Islands).
function slotTimeFormat(date, use24Hour) {
    if (use24Hour) return "HH:mm"
    return date.getMinutes() === 0 ? "hap" : "h:mmap"
}

// The index of today's entry in the daily forecast. Each entry is dated by
// the location's local midnight (in UTC), so today is the latest one that
// has begun — whatever the system time zone, and even when BoM still lists
// the day that just ended. 0 if none has begun.
function todayIndex(forecast, nowMs) {
    var today = 0
    for (var i = 0; i < (forecast || []).length; i++)
        if (Date.parse(forecast[i].date) <= nowMs) today = i
    return today
}

// Whether a fetch last made at lastMs (0: never) is due again at nowMs.
// Times are wall-clock (Date.now()), which keeps counting while the machine
// sleeps, where Qt timers do not; so a periodic check of this also notices
// a wake.
function isDue(lastMs, nowMs, intervalMs) {
    return lastMs <= 0 || nowMs - lastMs >= intervalMs
}

// Milliseconds from nowMs to just past the next minute boundary, for a
// clock that ticks on the minute.
function msToNextMinute(nowMs) {
    return 60000 - nowMs % 60000 + 50
}

// Whether data last fetched at lastMs is out of date at nowMs: two polls in
// a row have been missed. False before the first fetch (lastMs 0).
function isStale(lastMs, nowMs, intervalMs) {
    return lastMs > 0 && nowMs - lastMs > 2 * intervalMs
}

// Whether two times fall on the same local calendar day.
function isSameDay(aMs, bMs) {
    var a = new Date(aMs)
    var b = new Date(bMs)
    return a.getFullYear() === b.getFullYear()
        && a.getMonth() === b.getMonth()
        && a.getDate() === b.getDate()
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
