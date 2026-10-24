# Branding

Aussie Weather's icon: Australia under the tropism sun, on a light tile.
It is drawn the way the svc family's icons are (vitrine's `branding/README.md`
is the reference, and swarm-stacks' `branding/` the svc one): the same
tile, the same sun in vitrine's place, the subject in the accent's blue. The
owner chose it on 2026-10-24 over a rain cloud under the same sun; a cloud
over the continent was drawn too, and dropped as too busy.

| File | Used at |
|---|---|
| `icon.svg` | 48 pixels and up: Plasma's widget explorer, the README and the website |
| `icon-small.svg` | 32 pixels and below: the website's browser-tab icon. The sun loses its rays and the strokes double, or they blur away at that size |

Each file has the same two parts: `#tile` and `#mark`.

The continent is drawn from 36 points of coastline and 4 of Tasmania,
projected for 27° S and smoothed: what reads as Australia at icon size, not
a map. At 32 pixels and below it is little more than a shape, and that was
known when it was chosen.

## Colours

jot's palette in its light theme, as vitrine's and the svc icon's:

| Colour | Token | Where |
|---|---|---|
| `#f6f7f9` | `--bg` | the tile |
| `#1f5f8b` | `--accent` | the coastline |
| `#ffffff` | `--card` | the mainland |
| `#dde3e9` | `--line` | Tasmania, a shade darker, so it reads as its own island |
| `#e09b12` | | the sun: the tropism sun |

## Where it shows

| Copy | Shown by |
|---|---|
| `contents/screenshot.png` | Plasma's widget explorer (Add or Manage Widgets), in place of the icon |
| `docs/icon.png` | the README and the website's front page |
| `docs/favicon.svg` | the website's browser tab, through `docs/_includes/head-custom.html` |

`metadata.json`'s `Icon` stays a theme icon, `weather-clear-symbolic`, which
Plasma shows wherever it has no screenshot (the widget's settings window, for
one). It cannot name an icon inside the package: KDE's icon loader resolves
an icon theme's name or an absolute path, and the package's path differs
from one install to another. The widget explorer shows a package's
`contents/screenshot.png` instead of its icon when there is one, so the
icon goes there.

The KDE Store's logo is uploaded by hand; use `docs/icon.png`.

## Making the copies

`scripts/make-icons.py` makes every copy from the two sources: run it after
changing either, and commit what it writes. Never edit a copy by hand. It
needs ImageMagick with librsvg (`magick`) and Pillow.

Each PNG records the sha256 of the source it was made from, in a `tEXt`
chunk, and `docs/favicon.svg` must equal `icon-small.svg` byte for byte. So
`scripts/make-icons.py --check`, which CI runs, needs only Python: it fails
when a source has changed without the copies being remade, when a copy was
made from the other source or by anything else, or is the wrong size, or has
lost the tile's transparent corners. `tests/test_make_icons.py` shows it
failing on each.
