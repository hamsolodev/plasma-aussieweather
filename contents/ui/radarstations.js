// SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
//
// SPDX-License-Identifier: GPL-2.0-or-later

.pragma library

// BoM rain-radar stations with currently published loop products.
// Enumerated 2026-06-13 from ftp.bom.gov.au/anon/gen/radar (active frame
// files) and named via legacy product-page titles on reg.bom.gov.au.
// Product ID = "IDR" + site + range suffix (1=512 km, 2=256 km, 3=128 km, 4=64 km).
// Site 10 is absent from all BoM indexes; identified as Darwin (Airport)
// from its locations overlay. IDR052 (one stale frame from 2021) excluded.

var stations = [
    { site: "64", name: "Adelaide (Buckland Park)", ranges: [512, 256, 128, 64] },
    { site: "46", name: "Adelaide (Sellicks Hill)", ranges: [512, 256, 128] },
    { site: "31", name: "Albany", ranges: [512, 256, 128, 64] },
    { site: "25", name: "Alice Springs", ranges: [512, 256, 128] },
    { site: "68", name: "Bairnsdale", ranges: [512, 256, 128] },
    { site: "24", name: "Bowen", ranges: [512, 256, 128] },
    { site: "93", name: "Brewarrina", ranges: [512, 256, 128, 64] },
    { site: "50", name: "Brisbane (Marburg)", ranges: [512, 256, 128, 64] },
    { site: "66", name: "Brisbane (Mt Stapylton)", ranges: [512, 256, 128, 64] },
    { site: "17", name: "Broome", ranges: [512, 256, 128, 64] },
    { site: "19", name: "Cairns", ranges: [512, 256, 128, 64] },
    { site: "40", name: "Canberra (Captains Flat)", ranges: [512, 256, 128, 64] },
    { site: "114", name: "Carnarvon", ranges: [512, 256, 128, 64] },
    { site: "33", name: "Ceduna", ranges: [512, 256, 128, 64] },
    { site: "15", name: "Dampier", ranges: [512, 256, 128, 64] },
    { site: "10", name: "Darwin (Airport)", ranges: [512, 256, 128, 64] },
    { site: "63", name: "Darwin (Berrimah)", ranges: [512, 256, 128, 64] },
    { site: "72", name: "Emerald", ranges: [512, 256, 128, 64] },
    { site: "32", name: "Esperance", ranges: [512, 256, 128, 64] },
    { site: "06", name: "Geraldton", ranges: [512, 256, 128, 64] },
    { site: "44", name: "Giles", ranges: [512, 256, 128] },
    { site: "23", name: "Gladstone", ranges: [512, 256, 128] },
    { site: "112", name: "Gove", ranges: [512, 256, 128, 64] },
    { site: "28", name: "Grafton", ranges: [512, 256, 128] },
    { site: "74", name: "Greenvale", ranges: [512, 256, 128, 64] },
    { site: "08", name: "Gympie (Mt Kanigan)", ranges: [512, 256, 128, 64] },
    { site: "39", name: "Halls Creek", ranges: [512, 256, 128] },
    { site: "94", name: "Hillston", ranges: [512, 256, 128, 64] },
    { site: "76", name: "Hobart (Mt Koonya)", ranges: [512, 256, 128, 64] },
    { site: "37", name: "Hobart Airport", ranges: [512, 256, 128] },
    { site: "48", name: "Kalgoorlie", ranges: [512, 256, 128, 64] },
    { site: "111", name: "Karratha", ranges: [512, 256, 128, 64] },
    { site: "42", name: "Katherine (Tindal)", ranges: [512, 256, 128] },
    { site: "56", name: "Longreach", ranges: [512, 256, 128] },
    { site: "22", name: "Mackay", ranges: [512, 256, 128, 64] },
    { site: "02", name: "Melbourne", ranges: [512, 256, 128, 64] },
    { site: "01", name: "Melbourne (Broadmeadows)", ranges: [512, 256, 128, 64] },
    { site: "97", name: "Mildura", ranges: [512, 256, 128, 64] },
    { site: "53", name: "Moree", ranges: [512, 256, 128] },
    { site: "36", name: "Mornington Island (Gulf of Carpentaria)", ranges: [512, 256, 128] },
    { site: "75", name: "Mount Isa", ranges: [512, 256, 128, 64] },
    { site: "14", name: "Mt Gambier", ranges: [512, 256, 128] },
    { site: "69", name: "Namoi (Blackjack Mountain)", ranges: [512, 256, 128, 64] },
    { site: "04", name: "Newcastle", ranges: [512, 256, 128, 64] },
    { site: "38", name: "Newdegate", ranges: [512, 256, 128, 64] },
    { site: "62", name: "Norfolk Island", ranges: [512, 256, 128] },
    { site: "52", name: "NW Tasmania (West Takone)", ranges: [512, 256, 128, 64] },
    { site: "70", name: "Perth (Serpentine)", ranges: [512, 256, 128, 64] },
    { site: "26", name: "Perth Airport", ranges: [512, 256, 128, 64] },
    { site: "16", name: "Port Hedland", ranges: [512, 256, 128] },
    { site: "95", name: "Rainbow (Wimmera)", ranges: [512, 256, 128, 64] },
    { site: "107", name: "Richmond", ranges: [512, 256, 128, 64] },
    { site: "58", name: "South Doodlakine", ranges: [512, 256, 128, 64] },
    { site: "71", name: "Sydney (Terrey Hills)", ranges: [512, 256, 128, 64] },
    { site: "98", name: "Taroom", ranges: [512, 256, 128, 64] },
    { site: "108", name: "Toowoomba", ranges: [512, 256, 128, 64] },
    { site: "106", name: "Townsville", ranges: [512, 256, 128, 64] },
    { site: "55", name: "Wagga Wagga", ranges: [512, 256, 128] },
    { site: "67", name: "Warrego", ranges: [512, 256, 128] },
    { site: "77", name: "Warruwi", ranges: [512, 256, 128, 64] },
    { site: "79", name: "Watheroo", ranges: [512, 256, 128, 64] },
    { site: "78", name: "Weipa", ranges: [512, 256, 128, 64] },
    { site: "41", name: "Willis Island", ranges: [512, 256, 128] },
    { site: "03", name: "Wollongong (Appin)", ranges: [512, 256, 128, 64] },
    { site: "27", name: "Woomera", ranges: [512, 256, 128] },
    { site: "07", name: "Wyndham", ranges: [128] },
    { site: "49", name: "Yarrawonga", ranges: [512, 256, 128, 64] },
    { site: "96", name: "Yeoval", ranges: [512, 256, 128, 64] },
]

var rangeSuffix = { 512: "1", 256: "2", 128: "3", 64: "4" }
var suffixRange = { "1": 512, "2": 256, "3": 128, "4": 64 }

function stationId(site, km) {
    return "IDR" + site + rangeSuffix[km]
}

// "IDR023" -> { site: "02", km: 128 } (null if unparseable)
function parseId(id) {
    if (!id || id.length < 5 || id.substr(0, 3) !== "IDR") return null
    var suffix = id.charAt(id.length - 1)
    if (!(suffix in suffixRange)) return null
    return { site: id.substring(3, id.length - 1), km: suffixRange[suffix] }
}

function indexOfSite(site) {
    for (var i = 0; i < stations.length; i++)
        if (stations[i].site === site) return i
    return -1
}
