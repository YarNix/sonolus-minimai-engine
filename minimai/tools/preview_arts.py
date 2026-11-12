"""Draw the preview's skin sprites: the each line, and the sensor group marks and slide shape labels from a font.

Usage: python -m minimai.tools.preview_arts <folder> [--font FONT] [--height N]

Needs Pillow (``uv sync --extra tools``). Writes ``Mai Preview Each Line.png``: a horizontal band
in the each colour, the same all along so it can be stretched to any length. With ``--font``,
also ``Mai Preview Label <Label>.png`` for every label in ``PREVIEW_GROUP_LABELS``: a grey letter
(the printed lane numbers' colour) with a dark outline, centered in an image
``PREVIEW_LABEL_ASPECT`` wide per unit of height (N px tall, default 64), and
``Mai Preview Shape <Name>.png`` for every slide shape in ``PREVIEW_SHAPE_LABELS``: the simai
shape in a light grey with the same outline, left-aligned in an image ``PREVIEW_SHAPE_LABEL_ASPECT``
wide per unit of height. Both are sized so a capital fills the same part of the image, so the
shapes keep one baseline. Without a font, the labels are skipped.
"""

import argparse
from pathlib import Path

from minimai.lib.skin import PREVIEW_GROUP_LABELS, PREVIEW_SHAPE_LABELS
from minimai.preview.layout import PREVIEW_LABEL_ASPECT, PREVIEW_SHAPE_LABEL_ASPECT

# Drawn this many times bigger, then scaled down, for smooth edges.
SUPERSAMPLE = 4
# The group marks: the printed lane numbers' grey. The shape labels: lighter, to stand out on the slides.
GROUP_FILL = (128, 128, 128, 255)
SHAPE_FILL = (215, 215, 215, 255)
OUTLINE = (20, 20, 24, 255)
# Outline width and capital height, as parts of the image height. The shape labels' letters are
# smaller, to leave room for the descenders of p and q.
OUTLINE_WIDTH = 0.08
GROUP_LETTER_HEIGHT = 0.8
SHAPE_LETTER_HEIGHT = 0.5
# The shape labels' baseline, from the top, as a part of the image height.
SHAPE_BASELINE = 0.68

EACH_LINE_SIZE = (16, 16)
EACH_LINE_COLOR = (255, 222, 64)
# Across the band, as parts of its height: solid in the middle, fading out to the edges.
EACH_LINE_CORE = 0.5


def draw_label(
    font_path: str, text: str, height: int, aspect: float, letter_height: float, fill: tuple, centered: bool
):
    from PIL import Image, ImageDraw, ImageFont

    big_h = height * SUPERSAMPLE
    big_w = round(big_h * aspect)
    stroke = round(big_h * OUTLINE_WIDTH)
    # Size the font so the cap height fills letter_height of the image.
    font = ImageFont.truetype(font_path, big_h)
    l, t, r, b = font.getbbox("H")
    font = ImageFont.truetype(font_path, round(big_h * big_h * letter_height / (b - t)))
    image = Image.new("RGBA", (big_w, big_h), (0, 0, 0, 0))
    # Centered, or left-aligned on a baseline that leaves room for descenders.
    position = (big_w / 2, big_h / 2) if centered else (stroke, big_h * SHAPE_BASELINE)
    ImageDraw.Draw(image).text(
        position, text, font=font, fill=fill, anchor="mm" if centered else "ls", stroke_width=stroke, stroke_fill=OUTLINE
    )
    return image.resize((round(height * aspect), height), Image.LANCZOS)


def draw_each_line():
    from PIL import Image

    width, height = EACH_LINE_SIZE
    line = Image.new("RGBA", (width, height), EACH_LINE_COLOR + (0,))
    for y in range(height):
        # 0 at the middle, 1 at the edges.
        d = abs((y + 0.5) / height * 2 - 1)
        fade = (d - EACH_LINE_CORE) / (1 - EACH_LINE_CORE)
        alpha = 1 - max(0.0, min(1.0, fade))
        for x in range(width):
            line.putpixel((x, y), EACH_LINE_COLOR + (round(255 * alpha),))
    return line


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--font", help="draw the group marks and shape labels with this font (skipped without one)")
    parser.add_argument("--height", type=int, default=64, help="label height in pixels")
    args = parser.parse_args()
    args.folder.mkdir(parents=True, exist_ok=True)
    draw_each_line().save(args.folder / "Mai Preview Each Line.png")
    if args.font:
        for label in PREVIEW_GROUP_LABELS:
            draw_label(args.font, label, args.height, PREVIEW_LABEL_ASPECT, GROUP_LETTER_HEIGHT, GROUP_FILL, True).save(
                args.folder / f"Mai Preview Label {label}.png"
            )
        for name, shape in PREVIEW_SHAPE_LABELS:
            draw_label(args.font, shape, args.height, PREVIEW_SHAPE_LABEL_ASPECT, SHAPE_LETTER_HEIGHT, SHAPE_FILL, False).save(
                args.folder / f"Mai Preview Shape {name}.png"
            )


if __name__ == "__main__":
    main()
