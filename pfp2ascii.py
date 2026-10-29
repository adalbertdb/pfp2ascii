#!/usr/bin/env python3
"""Turn a profile picture into ASCII art.

The source can be a GitHub username, an image URL or a local file:

    python pfp2ascii.py adalbertdb
    python pfp2ascii.py https://example.com/me.jpg --cols 64
    python pfp2ascii.py me.png --svg me.svg

Works best with a portrait on a flat background: the backdrop is detected
from the corners and left blank, and the crop is tightened around the head.
"""

import argparse
import html
import io
import re
import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

RAMP = " .:-=+*#%@"


def load_image(source):
    if Path(source).exists():
        return Image.open(source)
    if re.fullmatch(r"[A-Za-z0-9-]{1,39}", source):
        source = f"https://avatars.githubusercontent.com/{source}?s=460"
    req = urllib.request.Request(source, headers={"User-Agent": "pfp2ascii"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return Image.open(io.BytesIO(r.read()))


def background_mask(rgb):
    """True where the pixel looks like the flat backdrop (sampled from the corners)."""
    h, w, _ = rgb.shape
    k = max(4, h // 20)
    corners = np.concatenate([
        rgb[:k, :k].reshape(-1, 3), rgb[:k, -k:].reshape(-1, 3),
        rgb[-k:, :k].reshape(-1, 3), rgb[-k:, -k:].reshape(-1, 3),
    ])
    # Bottom corners are often clothes, so only trust the top ones if they differ.
    top = np.concatenate([rgb[:k, :k].reshape(-1, 3), rgb[:k, -k:].reshape(-1, 3)])
    bg = np.median(top if np.abs(np.median(corners, 0) - np.median(top, 0)).sum() > 60 else corners, 0)
    return np.linalg.norm(rgb - bg, axis=2) < 70


def image_to_ascii(img, cols=56, ramp=RAMP, invert=False, keep_background=False, crop=True):
    img = ImageOps.exif_transpose(img).convert("RGB")
    fg = np.ones((img.height, img.width), bool) if keep_background else ~background_mask(np.asarray(img, dtype=float))
    if not fg.any():
        fg[:] = True

    if crop and not keep_background:
        # Crop to the head: its width comes from the top 60% of the picture so the
        # shoulders don't shrink the face, and the crop keeps a portrait ratio.
        ys, _ = np.nonzero(fg)
        _, hx = np.nonzero(fg[: int(img.height * 0.6)])
        if hx.size:
            hx0, hx1 = np.percentile(hx, [1, 99])
            pad = (hx1 - hx0) * 0.15
            x0, x1 = int(max(0, hx0 - pad)), int(min(img.width, hx1 + pad))
            y0 = int(np.percentile(ys, 0.5))
            y1 = int(min(img.height, y0 + (x1 - x0) * 1.25))
            img, fg = img.crop((x0, y0, x1, y1)), fg[y0:y1, x0:x1]

    rows = max(1, int(cols * img.height / img.width * 0.5))  # glyphs are ~2x taller than wide

    # Local contrast: sharpen, then subtract a blurred copy so uneven lighting
    # doesn't flatten one side of the face.
    gray = ImageOps.grayscale(img).filter(ImageFilter.UnsharpMask(3, 160, 2))
    local = np.asarray(gray, dtype=float) - 0.8 * np.asarray(gray.filter(ImageFilter.GaussianBlur(15)), dtype=float)

    # Equalize over the subject only (not the backdrop) so the whole ramp is used
    # for skin, eyes, hair... Bright -> dense glyphs, for light text on dark.
    values = np.sort(local[fg])
    equalized = np.searchsorted(values, local) / len(values)
    if invert:
        equalized = 1 - equalized
    density = np.asarray(Image.fromarray((equalized * 255).astype(np.uint8)).resize((cols, rows), Image.BOX), dtype=float) / 255
    mask = np.asarray(Image.fromarray(fg.astype(np.uint8) * 255).resize((cols, rows), Image.BOX), dtype=float) < 128

    lines = [
        "".join(" " if mask[y, x] else ramp[min(len(ramp) - 1, int(density[y, x] * len(ramp)))] for x in range(cols)).rstrip()
        for y in range(rows)
    ]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def to_svg(lines, fg="#c9d1d9", bg="#161b22", font_size=11):
    line_h, char_w = font_size * 1.25, font_size * 0.6
    width = round(max(len(l) for l in lines) * char_w + 30)
    height = round(len(lines) * line_h + 30)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}px" height="{height}px" '
        f'font-family="Consolas,monospace" font-size="{font_size}px">',
        "<style>text, tspan {white-space: pre;}</style>",
        f'<rect width="{width}px" height="{height}px" fill="{bg}" rx="15"/>',
        f'<text fill="{fg}">',
    ]
    for i, line in enumerate(lines):
        out.append(f'<tspan x="15" y="{round(15 + font_size + i * line_h, 2)}">{html.escape(line)}</tspan>')
    out += ["</text>", "</svg>"]
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="GitHub username, image URL or local image path")
    ap.add_argument("--cols", type=int, default=56, help="width in characters (default: 56)")
    ap.add_argument("--ramp", default=RAMP, help="glyphs ordered from sparse to dense")
    ap.add_argument("--invert", action="store_true", help="dark pixels -> dense glyphs (for dark text on light)")
    ap.add_argument("--keep-background", action="store_true", help="don't blank out the backdrop")
    ap.add_argument("--no-crop", action="store_true", help="don't crop around the head")
    ap.add_argument("-o", "--output", help="write the ASCII art to this .txt file instead of stdout")
    ap.add_argument("--svg", help="also write an SVG card to this path")
    args = ap.parse_args()

    lines = image_to_ascii(load_image(args.source), args.cols, args.ramp, args.invert,
                           args.keep_background, not args.no_crop)
    text = "\n".join(lines) + "\n"
    if args.output:
        Path(args.output).write_text(text)
    else:
        sys.stdout.write(text)
    if args.svg:
        Path(args.svg).write_text(to_svg(lines))


if __name__ == "__main__":
    main()
