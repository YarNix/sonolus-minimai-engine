"""Draw the firework's skin sprites: the rays in every hue and the pale ball.

Usage: python -m minimai.tools.firework_art <folder> [--scale S]

Needs Pillow (``uv sync --extra tools``). Writes ``firework_ray_1.png`` .. ``firework_ray_12.png``
(Ray 1 is red, then every 30 degrees of hue) and ``firework_ball_pale.png``, for the skin sprites
``Mai Firework Ray 1..12`` and ``Mai Firework Ball Pale``. ``--scale 2`` draws them twice as big.

A ray is a wedge, its tip at the bottom middle of the image (the firework's center) and its wide
end at the top, sized for FIREWORK_RAY_SIZE at scale 1 (one skin pixel per pixel). As in the
reference, the ray is a dark shade of its hue, and halftone dots of the full colour grow along it
until they merge into a solid bright end. It fades in from the tip and out at the end (the
reference cuts its rays off at the screen's circle; Sonolus can't).
"""

import argparse
import colorsys
from pathlib import Path

from minimai.lib.firework import FIREWORK_HUES
from minimai.lib.layout import FIREWORK_RAY_SIZE, SKIN_RING_RADIUS_PX

# Drawn this many times bigger, then scaled down, for smooth edges.
SUPERSAMPLE = 4
SATURATION = 0.8
VALUE = 0.92
# The ray's dark shade, as a part of the full colour's value.
DARK_VALUE = 0.45
# Along the ray, from the tip (0) to the end (1).
FADE_IN_END = 0.15
FADE_OUT_START = 0.88
# Dots start (as points) here and grow until they merge here; solid bright after.
DOTS_START = 0.3
DOTS_MERGED = 0.82
# Skin pixels between dots (a staggered grid); a dot this big, times the spacing, touches its
# neighbours.
DOT_SPACING = 13
DOT_MERGED_RADIUS = 0.62
PALE_BALL_SIZE = 512
PALE_BALL_COLOR = (255, 238, 246)
PALE_BALL_ALPHA = 0.9


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def length_alpha(u: float) -> float:
    return smoothstep(u / FADE_IN_END) * (1 - smoothstep((u - FADE_OUT_START) / (1 - FADE_OUT_START)))


def draw_ray_masks(width: int, height: int):
    """The ray's alpha, and where it shows the full colour (the rest is the dark shade), each
    ``width`` x ``height`` pixels, drawn big and scaled down."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    s = SUPERSAMPLE
    w, h = width * s, height * s
    wedge = Image.new("L", (w, h), 0)
    ImageDraw.Draw(wedge).polygon([(w / 2, h), (0, 0), (w, 0)], fill=255)

    # Supersampled pixels per skin pixel.
    px = s * height / (FIREWORK_RAY_SIZE.y * SKIN_RING_RADIUS_PX)
    spacing = DOT_SPACING * px
    light = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(light)
    merged_y = h * (1 - DOTS_MERGED)
    draw.rectangle((0, 0, w, merged_y), fill=255)
    # Rows of dots from where they merge back toward the tip, each a little smaller.
    row = 0
    y = merged_y
    while y < h * (1 - DOTS_START):
        u = 1 - y / h
        radius = DOT_MERGED_RADIUS * spacing * smoothstep((u - DOTS_START) / (DOTS_MERGED - DOTS_START))
        x = w / 2 + (spacing / 2 if row % 2 else 0)
        while x - spacing > 0:
            x -= spacing
        while x < w:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
            x += spacing
        y += spacing * 0.87
        row += 1

    fade = Image.new("L", (1, h))
    for py in range(h):
        fade.putpixel((0, py), round(255 * length_alpha(1 - (py + 0.5) / h)))
    fade = fade.resize((w, h))

    alpha = ImageChops.multiply(wedge, fade).filter(ImageFilter.GaussianBlur(s / 2))
    light = light.filter(ImageFilter.GaussianBlur(s / 3))
    return alpha.resize((width, height), Image.LANCZOS), light.resize((width, height), Image.LANCZOS)


def ray_color(index: int, value: float = 1.0) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(index / FIREWORK_HUES, SATURATION, VALUE * value)
    return round(r * 255), round(g * 255), round(b * 255)


def draw_pale_ball(size: int):
    """A soft white-pink ball, fading out from the middle to the edge."""
    from PIL import Image

    small = Image.new("L", (size, size))
    for y in range(size):
        for x in range(size):
            d = ((x + 0.5 - size / 2) ** 2 + (y + 0.5 - size / 2) ** 2) ** 0.5 / (size / 2)
            small.putpixel((x, y), round(255 * PALE_BALL_ALPHA * (1 - smoothstep((d - 0.1) / 0.9))))
    ball = Image.new("RGBA", (size, size), PALE_BALL_COLOR + (0,))
    ball.putalpha(small)
    return ball


def draw_art(folder: Path, scale: float = 1.0):
    try:
        from PIL import Image
    except ImportError as error:
        raise SystemExit("Pillow is needed: uv sync --extra tools") from error

    folder.mkdir(parents=True, exist_ok=True)
    width = round(FIREWORK_RAY_SIZE.x * SKIN_RING_RADIUS_PX * scale)
    height = round(FIREWORK_RAY_SIZE.y * SKIN_RING_RADIUS_PX * scale)
    alpha, light = draw_ray_masks(width, height)
    for i in range(FIREWORK_HUES):
        ray = Image.composite(
            Image.new("RGB", (width, height), ray_color(i)),
            Image.new("RGB", (width, height), ray_color(i, DARK_VALUE)),
            light,
        ).convert("RGBA")
        ray.putalpha(alpha)
        ray.save(folder / f"firework_ray_{i + 1}.png")
    draw_pale_ball(round(PALE_BALL_SIZE * scale)).save(folder / "firework_ball_pale.png")
    print(f"{FIREWORK_HUES} rays ({width} x {height}) and the pale ball written to {folder}")


def main():
    parser = argparse.ArgumentParser(description="Draw the firework's skin sprites.")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--scale", type=float, default=1.0, help="2 draws them twice as big")
    args = parser.parse_args()
    draw_art(args.folder, args.scale)


if __name__ == "__main__":
    main()
