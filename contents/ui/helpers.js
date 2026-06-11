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
// Reference: known new moon 2000-01-06T18:14:00Z; synodic month 29.530588853 days
function moonPhase(date) {
    var knownNewMoon = new Date("2000-01-06T18:14:00Z")
    var synodicMonth = 29.530588853
    var daysSince = (date.getTime() - knownNewMoon.getTime()) / 86400000
    var phase = ((daysSince % synodicMonth) + synodicMonth) % synodicMonth
    if (phase <  1.85) return {emoji: "🌑", name: "New Moon"}
    if (phase <  7.38) return {emoji: "🌒", name: "Waxing Crescent"}
    if (phase < 11.08) return {emoji: "🌓", name: "First Quarter"}
    if (phase < 14.77) return {emoji: "🌔", name: "Waxing Gibbous"}
    if (phase < 16.62) return {emoji: "🌕", name: "Full Moon"}
    if (phase < 22.15) return {emoji: "🌖", name: "Waning Gibbous"}
    if (phase < 25.85) return {emoji: "🌗", name: "Last Quarter"}
    if (phase < 27.69) return {emoji: "🌘", name: "Waning Crescent"}
    return {emoji: "🌑", name: "New Moon"}
}
