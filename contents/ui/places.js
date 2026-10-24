// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

.pragma library
.import "radarstations.js" as RadarStations

// The places the widget can switch between. A place is {search, radar}: the
// location as typed ("Seaford VIC") and the radar product ID shown with it
// ("IDR023"). The config keeps them in `places`, one JSON object each; the
// place on show is still locationSearch and radarStation, which the weather
// and radar read.

// "  seaford   VIC " and "Seaford VIC" are the same place.
function _key(search) {
    return search.trim().replace(/\s+/g, " ").toLowerCase()
}

function _place(search, radar) {
    return { search: search.trim(),
             radar: RadarStations.isKnownId(radar) ? radar : RadarStations.defaultId }
}

// The saved place in one config entry, or null if it makes no sense.
function _parse(entry) {
    var value
    try {
        value = JSON.parse(entry)
    } catch (e) {
        return null
    }
    if (!value || typeof value.search !== "string" || value.search.trim() === "")
        return null
    return _place(value.search, value.radar)
}

// The places to offer, from the config's `entries` and the place on show
// (`search`, `radar`). A config from before saved places has none, so it
// offers just the place on show; and the place on show is always offered,
// with the radar it is shown with. Entries that make no sense are skipped,
// and a place saved twice is offered once.
function fromConfig(entries, search, radar) {
    var places = []
    var seen = Object.create(null)  // no prototype: "constructor" is a place
    for (var i = 0; entries && i < entries.length; i++) {
        var place = _parse(entries[i])
        if (place && !(_key(place.search) in seen)) {
            seen[_key(place.search)] = true
            places.push(place)
        }
    }
    if (typeof search === "string" && search.trim() !== "") {
        var shown = indexOf(places, search)
        if (shown < 0)
            places.unshift(_place(search, radar))
        else
            places[shown] = _place(places[shown].search, radar)
    }
    return places
}

// The config's `places` entries for `places`; blank ones are not saved, and
// a place listed twice is saved once, as it was first listed.
function toConfig(places) {
    var seen = Object.create(null)
    return places.filter(function(p) {
        var key = _key(p.search)
        if (key === "" || key in seen)
            return false
        seen[key] = true
        return true
    }).map(function(p) { return JSON.stringify({ search: p.search.trim(), radar: p.radar }) })
}

// The index in `places` of the place searched as `search`; -1 if none.
function indexOf(places, search) {
    if (typeof search !== "string" || search.trim() === "")
        return -1
    for (var i = 0; i < places.length; i++)
        if (_key(places[i].search) === _key(search))
            return i
    return -1
}
