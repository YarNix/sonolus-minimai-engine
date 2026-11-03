"""Draw the touch feedback's skin sprites: the ring and the petal.

Usage: python -m minimai.tools.touch_feedback_art <folder> [--size N]

Needs Pillow (``uv sync --extra tools``). Writes ``touch_feedback_ring.png`` (N x N, default 256)
and ``touch_feedback_petal.png`` (N/4 x N/2), white, for the skin sprites ``Mai Touch Feedback
Ring`` and ``Mai Touch Feedback Petal``.

The ring is faint in the middle and brightens outward into a thin rim at TOUCH_FEEDBACK_RING_RIM
of its half size, with a little glow past it. The petal is a droplet pointing up (out from the
feedback's center), wider at its inner end.
"""

import argparse
from pathlib import Path

from minimai.lib.layout import TOUCH_FEEDBACK_RING_RIM

# Drawn this many times bigger, then scaled down, for smooth edges.
SUPERSAMPLE = 4
# Ring alpha inside the rim: GRADIENT_BASE in the middle, rising by GRADIENT_RISE toward the rim.
GRADIENT_BASE = 0.15
GRADIENT_RISE = 0.4
GRADIENT_POWER = 2.5
# Rim and glow widths, as parts of the half size.
RIM_WIDTH = 0.018
GLOW_WIDTH = 0.04
# The petal's inner end is this much wider than a plain ellipse; its outer end that much narrower.
PETAL_TAPER = 0.3


def ring_alpha(d: float) -> float:
    """``d``: distance from the center as a part of the half size."""
    import math

    x = d / TOUCH_FEEDBACK_RING_RIM
    gradient = GRADIENT_BASE + GRADIENT_RISE * min(x, 1) ** GRADIENT_POWER if x <= 1 else 0.0
    rim = math.exp(-0.5 * ((d - TOUCH_FEEDBACK_RING_RIM) / RIM_WIDTH) ** 2)
    glow = 0.3 * math.exp(-max(d - TOUCH_FEEDBACK_RING_RIM, 0) / GLOW_WIDTH) if d > TOUCH_FEEDBACK_RING_RIM else 0.0
    return min(1.0, gradient + rim + glow) if d < 1 else 0.0


def draw_ring(size: int):
    from PIL import Image

    big = size * SUPERSAMPLE
    half = big / 2
    alpha = Image.new("L", (big, big))
    pixels = alpha.load()
    # Only the radial profile matters: fill each pixel from a lookup by distance.
    table = [round(255 * ring_alpha(i / 1000)) for i in range(1001)]
    for y in range(big):
        dy = (y + 0.5 - half) / half
        for x in range(big):
            dx = (x + 0.5 - half) / half
            d = (dx * dx + dy * dy) ** 0.5
            pixels[x, y] = table[min(round(d * 1000), 1000)]
    ring = Image.new("RGBA", (big, big), (255, 255, 255, 0))
    ring.putalpha(alpha)
    return ring.resize((size, size), Image.LANCZOS)


def draw_petal(width: int, height: int):
    from PIL import Image, ImageFilter

    big_w, big_h = width * SUPERSAMPLE, height * SUPERSAMPLE
    alpha = Image.new("L", (big_w, big_h))
    pixels = alpha.load()
    margin = 0.08
    for py in range(big_h):
        # v: -1 at the inner (bottom) end, 1 at the outer (top) end.
        v = 1 - 2 * (py + 0.5) / big_h
        v /= 1 - margin
        if abs(v) >= 1:
            continue
        half_width = (1 - v * v) ** 0.5 * (1 - PETAL_TAPER * v) / (1 + PETAL_TAPER) * (1 - margin)
        for px in range(big_w):
            u = 2 * (px + 0.5) / big_w - 1
            if abs(u) < half_width:
                pixels[px, py] = 255
    alpha = alpha.filter(ImageFilter.GaussianBlur(SUPERSAMPLE * 0.8))
    petal = Image.new("RGBA", (big_w, big_h), (255, 255, 255, 0))
    petal.putalpha(alpha)
    return petal.resize((width, height), Image.LANCZOS)


def draw_art(folder: Path, size: int):
    try:
        import PIL  # noqa: F401
    except ImportError as error:
        raise SystemExit("Pillow is needed: uv sync --extra tools") from error
    folder.mkdir(parents=True, exist_ok=True)
    draw_ring(size).save(folder / "touch_feedback_ring.png")
    draw_petal(size // 4, size // 2).save(folder / "touch_feedback_petal.png")
    print(f"Ring ({size} x {size}) and petal ({size // 4} x {size // 2}) written to {folder}")


def main():
    parser = argparse.ArgumentParser(description="Draw the touch feedback's skin sprites.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--size", type=int, default=256, help="the ring's side in px")
    args = parser.parse_args()
    draw_art(args.folder, args.size)


if __name__ == "__main__":
    main()
