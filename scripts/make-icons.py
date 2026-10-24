#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2026 Mark Hellewell <aussieweather.sandlot200@passinbox.com>
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Make every copy of the widget's icon from branding/icon.svg and
branding/icon-small.svg.

    scripts/make-icons.py           regenerate every target below
    scripts/make-icons.py --check   fail if a target is missing, the wrong
                                    size, or made from another source (CI)

Two sources, as the svc family's icons have (branding/README.md):
icon.svg for 48 pixels and up, icon-small.svg for 32 and below.

Every PNG carries the sha256 of the source it was rendered from, as a tEXt
chunk, and that is what --check reads: it needs only the standard library
and no renderer, since rendering is not byte-for-byte reproducible across
ImageMagick versions, but the recorded source is. Prints how many targets
it examined, and fails if that is none.

Making them needs ImageMagick with librsvg (`magick`) and Pillow.
"""

import hashlib
import io
import pathlib
import struct
import subprocess
import sys
import zlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCES = {"icon": "branding/icon.svg", "small": "branding/icon-small.svg"}
STAMP_KEY = "branding-source-sha256"

# Byte-for-byte copies: path -> source.
SVG_COPIES = {
    "docs/favicon.svg": "small",  # the website's browser-tab icon
}
# PNGs, as drawn (transparent outside the tile's rounded corners): path ->
# (source, edge in pixels).
PNGS = {
    # Plasma's widget explorer shows a package's screenshot in place of its
    # icon, at 128 pixels; metadata.json's Icon can only name a theme icon.
    "contents/screenshot.png": ("icon", 256),
    "docs/icon.png": ("icon", 256),  # the README and the website
}


def render(svg_path, edge):
    """SVG_PATH as an RGBA image EDGE pixels square: rendered large and
    downsampled, as the design was chosen from."""
    from PIL import Image
    png = subprocess.run(["magick", "-background", "none", "-density", "1536", str(svg_path),
                          "-resize", "%dx%d" % (edge, edge), "png:-"],
                         check=True, capture_output=True).stdout
    image = Image.open(io.BytesIO(png))
    image.load()
    if image.size != (edge, edge):
        sys.exit("make-icons: magick rendered %s, wanted %dx%d" % (image.size, edge, edge))
    return image.convert("RGBA")


def stamped_png(image, sha):
    """IMAGE as PNG bytes recording SHA, its source's hash."""
    from PIL.PngImagePlugin import PngInfo
    info = PngInfo()
    info.add_text(STAMP_KEY, sha)
    out = io.BytesIO()
    image.save(out, format="PNG", optimize=True, pnginfo=info)
    return out.getvalue()


# --- Reading back: the standard library only, for CI. ---

def png_facts(data):
    """(width, height, PNG colour type, the recorded source hash or None)."""
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG")
    position, size, colour, stamp = 8, None, None, None
    while position < len(data):
        length, kind = struct.unpack(">I4s", data[position:position + 8])
        body = data[position + 8:position + 8 + length]
        if kind == b"IHDR":
            width, height, _, colour = struct.unpack(">IIBB", body[:10])
            size = (width, height)
        elif kind in (b"tEXt", b"zTXt"):
            key, _, value = body.partition(b"\0")
            if key.decode("latin-1") == STAMP_KEY:
                stamp = (value if kind == b"tEXt" else zlib.decompress(value[1:])).decode("latin-1")
        elif kind == b"IEND":
            break
        position += 12 + length
    if size is None:
        raise ValueError("no IHDR")
    return size[0], size[1], colour, stamp


def check(root):
    """(targets examined, problems) for the targets under ROOT."""
    sources = {key: (root / path).read_bytes() for key, path in SOURCES.items()}
    shas = {key: hashlib.sha256(data).hexdigest() for key, data in sources.items()}
    examined = 0
    problems = []
    for path, key in SVG_COPIES.items():
        examined += 1
        target = root / path
        if not target.is_file():
            problems.append(path + ": missing")
        elif target.read_bytes() != sources[key]:
            problems.append("%s: differs from %s" % (path, SOURCES[key]))
    for path, (key, edge) in PNGS.items():
        examined += 1
        target = root / path
        if not target.is_file():
            problems.append(path + ": missing")
            continue
        try:
            width, height, colour, stamp = png_facts(target.read_bytes())
        except (ValueError, struct.error) as e:
            problems.append("%s: %s" % (path, e))
            continue
        if (width, height) != (edge, edge):
            problems.append("%s: %dx%d, wants %dx%d" % (path, width, height, edge, edge))
        if stamp != shas[key]:
            made_from = next((SOURCES[k] for k, sha in shas.items() if sha == stamp),
                             "an unrecorded source")
            problems.append("%s: made from %s, not today's %s" % (path, made_from, SOURCES[key]))
        if colour not in (4, 6):
            problems.append(path + ": no alpha channel, but the tile has transparent corners")
    return examined, problems


def report(examined, problems):
    for problem in problems:
        print("make-icons: " + problem, file=sys.stderr)
    if not examined:
        print("FAIL: no targets examined", file=sys.stderr)
        return 1
    if problems:
        print("FAIL: run scripts/make-icons.py and commit what it writes", file=sys.stderr)
        return 1
    print("OK: %d icon targets made from today's sources" % examined)
    return 0


def make(root):
    sources = {key: (root / path).read_bytes() for key, path in SOURCES.items()}
    for path, key in SVG_COPIES.items():
        (root / path).write_bytes(sources[key])
        print("wrote " + path)
    for path, (key, edge) in PNGS.items():
        sha = hashlib.sha256(sources[key]).hexdigest()
        data = stamped_png(render(root / SOURCES[key], edge), sha)
        (root / path).write_bytes(data)
        print("wrote %s (%d bytes)" % (path, len(data)))
    return report(*check(root))


def main(argv):
    if argv == ["--check"]:
        return report(*check(ROOT))
    if argv:
        print(__doc__.split("\n\n")[1], file=sys.stderr)
        return 2
    return make(ROOT)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
