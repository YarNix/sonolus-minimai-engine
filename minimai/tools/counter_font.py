"""Draw the center counter's glyph sprites from a font.

Usage: python -m minimai.tools.counter_font <font> <folder> [--scale S]

Needs Pillow (``uv sync --extra tools``).
Writes ``Mai Counter <Colour> <Glyph>.png`` for every colour and glyph in ``COUNTER_COLOURS`` / ``COUNTER_GLYPHS``,
``Mai Counter <Colour> Life.png`` (the life counter's backdrop) for every colour,
and ``Mai Counter <Colour> <Header>.png`` for the headers in ``HEADERS``,
sized for the layout at one pixel per skin pixel (``--scale 2`` doubles them).
"""

import argparse
from pathlib import Path

from minimai.lib.layout import (
    COUNTER_DIGIT_HEIGHT,
    COUNTER_GLYPH_WIDTHS,
    COUNTER_LIFE_SIZE,
    COUNTER_LINE_HEIGHT,
    COUNTER_OUTLINE_WIDTH,
    SKIN_RING_RADIUS_PX,
)
from minimai.lib.skin import COUNTER_COLOURS, COUNTER_GLYPHS

# Drawn this many times bigger, then scaled down, for smooth edges.
SUPERSAMPLE = 4
CHARACTERS = {"Dot": ".", "Percent": "%", "Plus": "+", "Minus": "-"}
OUTLINE = (250, 242, 220)
# The filled-in counters, a little greyer than the outline.
COUNTER_FILL = (218, 214, 206)
# By COUNTER_COLOURS: the fill colour, its pattern ("checker", "stripes" or None) and its shine. A
# shine tints the glyph from its top left corner out to a part of its diagonal: lighter ("light")
# or darker ("dark").
FILLS = {
    "Yellow": ((250, 208, 40), "checker", ("light", 0.2)),
    "Pink": ((234, 58, 104), "stripes", None),
    "Green": ((64, 196, 92), None, None),
    "Silver": ((146, 154, 170), None, ("dark", 0.5)),
    "Blue": ((84, 176, 240), None, ("dark", 0.5)),
    "Red": ((228, 92, 78), None, None),
    "Gold": ((236, 162, 36), "checker", ("light", 0.2)),
}
# Shine: how far toward white or black the tint goes, and how long its edge fades, as parts of
# the glyph's diagonal.
SHINE_LIGHT = 0.45
SHINE_DARK = 0.72
SHINE_FADE = 0.12
# Sprites drawn without their colour's shine.
UNSHINED = ("Combo", "Achievement")
# The rest in skin px: the darker edge inside the fill.
EDGE_WIDTH = 1.0
EDGE_SHADE = 0.6
# Hook openings are filled in (see fill_hooks): the closing radius that bridges
# them, the narrowest room kept, and how much of a room's edge the glyph must make up.
HOOK_RADIUS = 9.0
ROOM_WIDTH = 3.0
ROOM_ENCLOSURE = 0.65
# Header words: the box (skin px), and the height of its flat capitals, outline included.
HEADERS = {"Combo": ((186, 52), 39), "Achievement": ((334, 52), 37)}
# Headers are heavier and wider than the digits: their strokes are thickened by this,
# and the word is stretched to fill its box but for this margin each side (outline included).
HEADER_BOLDEN = 1.75
HEADER_MARGIN = 4.5
# Patterns, a darker shade of whatever is under them: a checker of squares, and stripes.
CHECKER_SIZE = 5.5
CHECKER_SHADE = 0.9
STRIPE_PERIOD = 6.0
STRIPE_SHADE = 0.9
# The life backdrop, in skin px from its center (COUNTER_LIFE_SIZE square)
LIFE_RING_OUTER = 135
LIFE_RING_INNER = 93
LIFE_RING_RIM = 6.0
LIFE_LIGHT_STRIP = 7.0
LIFE_MARK_GAP = 5.0
LIFE_DEEP_SHADE = 0.75
LIFE_MARK_LIGHT = (240, 236, 238)
LIFE_BACKDROP = (8, 4, 4, 220)
LIFE_BRIGHTNESS = 0.68
LIFE_HEART_WIDTHS = {"Green": 147, "Yellow": 115, "Red": 0, "Silver": 0}
# The other colours (not used by the life counter).
LIFE_HEART_WIDTH = 147
LIFE_HEART_DROP = 8
# The heart
LIFE_HEART_WARM = (255, 236, 80)
LIFE_HEART_TOP_WARMTH = 0.3
LIFE_HEART_BOTTOM_DEPTH = 0.6
LIFE_HEART_SHADE = 0.82
LIFE_HEART_ALPHA = 255
LIFE_HEART_RIM = 0.06
LIFE_HEART_BEVEL = 0.16
LIFE_HEART_BEVEL_FADE = 0.08
LIFE_HEART_BEVEL_LIGHT = 0.15


def skin_px(value: float) -> float:
    return value * SKIN_RING_RADIUS_PX


def window_max(mask, low: int, high: int, combine):
    """``combine`` of the mask shifted right by every offset from ``low`` to ``high``, by doubling."""
    from PIL import ImageChops

    result, covered = mask, 1
    while covered * 2 <= high - low + 1:
        result = combine(result, ImageChops.offset(result, covered, 0))
        covered *= 2
    if covered < high - low + 1:
        result = combine(result, ImageChops.offset(result, high - low + 1 - covered, 0))
    return ImageChops.offset(result, low, 0)


def morph(mask, radius: float, combine):
    """Dilate (``ImageChops.lighter``) or erode (``darker``) by a disk, a row of it at a time."""
    from PIL import ImageChops

    result = mask
    r = int(radius)
    for y in range(-r, r + 1):
        half = int((radius * radius - y * y) ** 0.5)
        row = window_max(mask, -half, half, combine)
        result = combine(result, ImageChops.offset(row, 0, y))
    return result


def dilate(mask, radius: float):
    from PIL import ImageChops

    return morph(mask, radius, ImageChops.lighter)


def erode(mask, radius: float):
    from PIL import ImageChops

    return morph(mask, radius, ImageChops.darker)


def fill_holes(mask):
    """Everything not reachable from the border (the mask has a clear margin)."""
    from PIL import ImageChops, ImageDraw

    outside = mask.copy()
    ImageDraw.floodfill(outside, (0, 0), 128)
    return ImageChops.invert(outside.point(lambda v: 255 if v == 128 else 0))


def components(mask):
    """Each 8-connected part of a 0 / 255 mask, as its own mask."""
    from PIL import ImageDraw

    marked = mask.copy()
    parts = []
    start = marked.tobytes().find(255)
    while start >= 0:
        ImageDraw.floodfill(marked, (start % mask.width, start // mask.width), 128)
        part = marked.point(lambda v: 255 if v == 128 else 0)
        marked.paste(0, mask=part)
        parts.append(part)
        start = marked.tobytes().find(255, start)
    return parts


def fill_hooks(fill, radius: float, width: float, enclosure: float):
    """The fill with its counters and hook openings filled in.

    A closing bridges a hook's opening and fills the room behind it, but it also fills every
    concave corner (the inside of a 7, the gaps in a %) and the wide open bays (below a 2's
    hook). The closing's additions are split into rooms a disk of ``width`` fits in; a room is
    kept if the glyph makes up at least ``enclosure`` of its edge, together with the bridge
    beside it. Thin wedges have no room, and open bays are mostly edged by the outside."""
    from PIL import Image, ImageChops

    solid = fill_holes(fill)
    added = ImageChops.subtract(fill_holes(erode(dilate(solid, radius), radius)), solid)
    kept = Image.new("L", fill.size)
    for room in components(dilate(erode(added, width), width)):
        edge = ImageChops.subtract(dilate(room, 2), room)
        if ImageChops.multiply(edge, solid).histogram()[255] >= enclosure * edge.histogram()[255]:
            kept = ImageChops.lighter(kept, room)
    added = ImageChops.multiply(added, dilate(kept, width))
    return fill_holes(ImageChops.lighter(solid, added))


def star_mask(size: tuple[int, int], height: float):
    """A four-pointed star with curved-in sides (✧), centered, ``height`` tall."""
    import math

    from PIL import Image, ImageDraw

    mask = Image.new("L", size)
    # An astroid.
    power = 3
    shape = []
    for i in range(400):
        t = 2 * math.pi * i / 400
        x, y = math.cos(t), math.sin(t)
        shape.append((math.copysign(abs(x) ** power, x), math.copysign(abs(y) ** power, y)))
    r = height / 2
    cx, cy = size[0] / 2, size[1] / 2
    ImageDraw.Draw(mask).polygon([(cx + r * x, cy - r * y) for x, y in shape], fill=255)
    return mask


class GlyphRenderer:
    def __init__(self, font_path: Path, scale: float):
        self.font_path = font_path
        self.px = scale * SUPERSAMPLE
        self.outline = skin_px(COUNTER_OUTLINE_WIDTH) * self.px
        self.line_height = self.texture_px(COUNTER_LINE_HEIGHT)
        # Flat-topped digits fill this much without their outline; size the font to it with "1".
        self.fill_height = skin_px(COUNTER_DIGIT_HEIGHT) * self.px - 2 * self.outline
        self.font = self.sized_font("1", self.fill_height)
        self.baseline = (self.line_height + self.fill_height) / 2

    def texture_px(self, size: float) -> int:
        """A layout size in supersampled texture px, a whole number of output px."""
        return round(skin_px(size) * self.px / SUPERSAMPLE) * SUPERSAMPLE

    def sized_font(self, reference: str, height: float):
        """The font at the size where ``reference``'s ink is ``height`` tall."""
        from PIL import ImageFont

        probe = ImageFont.truetype(str(self.font_path), 1000)
        left, top, right, bottom = probe.getbbox(reference, anchor="ls")
        return ImageFont.truetype(str(self.font_path), round(1000 * height / (bottom - top)))

    def glyph_masks(self, glyph: str, cell_width: float):
        """The fill, the solid silhouette and the outlined shape, as L masks."""
        from PIL import Image, ImageDraw

        width = self.texture_px(cell_width)
        if glyph == "Star":
            fill = star_mask((width, self.line_height), self.fill_height)
        else:
            fill = Image.new("L", (width, self.line_height))
            character = CHARACTERS.get(glyph, glyph)
            # The advance is centered, not the ink: the font's own offsets (a "1" sits left) stay.
            x = (width - self.font.getlength(character)) / 2
            ImageDraw.Draw(fill).text((x, self.baseline), character, font=self.font, fill=255, anchor="ls")
            if glyph in ("Plus", "Minus"):
                # Measured on the ink: Pillow's bbox ends a "-" at the baseline.
                _, top, _, bottom = fill.getbbox()
                y = self.baseline + self.line_height / 2 - (top + bottom) / 2
                fill = Image.new("L", (width, self.line_height))
                ImageDraw.Draw(fill).text((x, y), character, font=self.font, fill=255, anchor="ls")
        return self.shape(glyph, fill)

    def header_masks(self, header: str, size: tuple[float, float], cap_height: float):
        """As glyph_masks, for a header word in its box, its flat capitals ``cap_height`` tall
        (outline included). Both in skin px."""
        from PIL import Image, ImageDraw

        width, height = (round(side * self.px / SUPERSAMPLE) * SUPERSAMPLE for side in size)
        bolden = HEADER_BOLDEN * self.px
        cap = cap_height * self.px - 2 * self.outline - 2 * bolden
        font = self.sized_font("H", cap)
        text = header.upper()
        word = Image.new("L", (round(font.getlength(text)) + 4, height))
        ImageDraw.Draw(word).text((2, (height + cap) / 2), text, font=font, fill=255, anchor="ls")
        word = word.crop((word.getbbox()[0], 0, word.getbbox()[2], height))
        ink_width = width - 2 * (HEADER_MARGIN * self.px + self.outline + bolden)
        word = word.resize((round(ink_width), height), Image.Resampling.LANCZOS)
        pad = int(bolden) + 1
        fill = Image.new("L", (width + 2 * pad, height + 2 * pad))
        fill.paste(word, (pad + round((width - word.width) / 2), pad))
        fill = dilate(fill.point(lambda v: 255 if v >= 128 else 0), bolden)
        return self.shape(header, fill.crop((pad, pad, pad + width, pad + height)))

    def shape(self, name: str, fill):
        from PIL import ImageOps

        width, height = fill.size
        # Room round the box, so the dilations don't wrap round its edges.
        margin = int(HOOK_RADIUS * self.px + self.outline) + 2
        fill = ImageOps.expand(fill.point(lambda v: 255 if v >= 128 else 0), margin)
        solid = fill_hooks(fill, HOOK_RADIUS * self.px, ROOM_WIDTH * self.px, ROOM_ENCLOSURE)
        outlined = dilate(solid, self.outline)
        bbox = outlined.getbbox()
        if bbox and (bbox[0] < margin or bbox[2] > margin + width):
            print(f"  {name}: wider than its box, the sides are cut off")
        box = (margin, margin, margin + width, margin + height)
        return fill.crop(box), solid.crop(box), outlined.crop(box)


def pattern(size: tuple[int, int], kind: str, px: float):
    """An L mask of where the pattern goes."""
    from PIL import Image, ImageDraw

    mask = Image.new("L", size)
    draw = ImageDraw.Draw(mask)
    if kind == "checker":
        side = CHECKER_SIZE * px
        for row in range(int(size[1] / side) + 1):
            for column in range(row % 2, int(size[0] / side) + 1, 2):
                draw.rectangle((column * side, row * side, (column + 1) * side - 1, (row + 1) * side - 1), fill=255)
    else:
        period = STRIPE_PERIOD * px
        offset = -float(size[1])
        while offset < size[0]:
            draw.polygon(
                [(offset, 0), (offset + period / 2, 0), (offset + period / 2 + size[1], size[1]), (offset + size[1], size[1])],
                fill=255,
            )
            offset += period
    return mask


def shade(colour: tuple[int, int, int], factor: float) -> tuple[int, int, int]:
    return tuple(round(c * factor) for c in colour)


def lighten(colour: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(c + (255 - c) * amount) for c in colour)


def shine_mask(fill, reach: float):
    """An L mask, full at the fill's top left corner, fading out ``reach`` of the way along its
    diagonal (over SHINE_FADE)."""
    from PIL import Image, ImageChops

    mask = Image.new("L", fill.size)
    box = fill.getbbox()
    if not box:
        return mask
    size = (box[2] - box[0], box[3] - box[1])
    across = Image.linear_gradient("L").rotate(90).resize(size)
    down = Image.linear_gradient("L").resize(size)
    # 0 at the top left, 255 at the bottom right.
    diagonal = ImageChops.add(across, down, scale=2)
    low, high = (reach - SHINE_FADE / 2) * 255, (reach + SHINE_FADE / 2) * 255
    mask.paste(diagonal.point(lambda v: round(255 * min(max((high - v) / (high - low), 0), 1))), box)
    return mask


def paint(fill, solid, outlined, colour: str, px: float, shines: bool = True):
    from PIL import Image, ImageChops

    base, kind, shine = FILLS[colour]
    body = Image.new("RGB", fill.size, base)
    if shine and shines:
        tone, reach = shine
        tint = lighten(base, SHINE_LIGHT) if tone == "light" else shade(base, SHINE_DARK)
        body.paste(tint, mask=shine_mask(fill, reach))
    if kind:
        pattern_shade = CHECKER_SHADE if kind == "checker" else STRIPE_SHADE
        darker = ImageChops.multiply(body, Image.new("RGB", fill.size, (round(255 * pattern_shade),) * 3))
        body.paste(darker, mask=pattern(fill.size, kind, px))
    image = Image.new("RGBA", fill.size, OUTLINE + (0,))
    image.paste(OUTLINE + (255,), mask=outlined)
    image.paste(COUNTER_FILL + (255,), mask=ImageChops.subtract(solid, fill))
    image.paste(body, mask=fill)
    edge = ImageChops.subtract(fill, erode(fill, EDGE_WIDTH * px))
    image.paste(shade(base, EDGE_SHADE) + (255,), mask=edge)
    return image


def heart_points(width: float, center: tuple[float, float]) -> list[tuple[float, float]]:
    """A heart ``width`` wide, its bounding box centered on ``center`` (image coordinates)."""
    import math

    points = []
    for i in range(400):
        t = 2 * math.pi * i / 400
        points.append((16 * math.sin(t) ** 3, 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)))
    xs, ys = [x for x, _ in points], [y for _, y in points]
    scale = width / (max(xs) - min(xs))
    middle = (max(ys) + min(ys)) / 2
    return [(center[0] + x * scale, center[1] - (y - middle) * scale) for x, y in points]


def deep_shade(colour: tuple[int, int, int]) -> tuple[int, int, int]:
    """The colour multiplied by itself and darkened: green stays green, yellow turns orange."""
    return tuple(round(v * v / 255 * LIFE_DEEP_SHADE) for v in colour)


def mix(colour: tuple[int, int, int], other: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(a + (b - a) * amount) for a, b in zip(colour, other))


def draw_life(colour: str, px: float):
    """The life counter's backdrop in ``colour``, at ``px`` texture px per skin px."""
    import math

    from PIL import Image, ImageDraw

    base = FILLS[colour][0]
    side = round(skin_px(COUNTER_LIFE_SIZE) * px / SUPERSAMPLE) * SUPERSAMPLE
    c = side / 2
    image = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def disc(radius: float):
        return (c - radius * px, c - radius * px, c + radius * px, c + radius * px)

    def ring(outer: float, inner: float):
        mask = Image.new("L", (side, side))
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse(disc(outer), fill=255)
        mask_draw.ellipse(disc(inner), fill=0)
        return mask

    deep = deep_shade(base)
    draw.ellipse(disc(LIFE_RING_INNER), fill=LIFE_BACKDROP)
    draw.ellipse(disc(LIFE_RING_OUTER), outline=deep + (255,), width=round((LIFE_RING_OUTER - LIFE_RING_INNER) * px))
    # The marks between the rims, the coloured ones centered on the buttons (22.5° off the top).
    marks = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    mark_draw = ImageDraw.Draw(marks)
    for i in range(16):
        start = -90 - 11.25 + 22.5 * i
        colour_mark = base if i % 2 else LIFE_MARK_LIGHT
        mark_draw.pieslice(disc(LIFE_RING_OUTER), start, start + 22.5, fill=colour_mark + (255,))
    image.paste(marks, mask=ring(LIFE_RING_OUTER - LIFE_RING_RIM, LIFE_RING_INNER + LIFE_RING_RIM))
    strip_outer = LIFE_RING_OUTER - LIFE_RING_RIM
    image.paste(LIFE_MARK_LIGHT + (255,), mask=ring(strip_outer, strip_outer - LIFE_LIGHT_STRIP))
    # Dividers between the marks, through the strip.
    for i in range(16):
        angle = math.radians(-90 - 11.25 + 22.5 * i)
        inner, outer = LIFE_RING_INNER * px, LIFE_RING_OUTER * px
        draw.line(
            [(c + inner * math.cos(angle), c + inner * math.sin(angle)), (c + outer * math.cos(angle), c + outer * math.sin(angle))],
            fill=deep + (255,),
            width=round(LIFE_MARK_GAP * px),
        )
    width = LIFE_HEART_WIDTHS.get(colour, LIFE_HEART_WIDTH)
    if width:
        heart_side = round(width * 1.2 * px)
        heart = draw_heart(base, width * px, heart_side)
        image.alpha_composite(heart, (round(c - heart_side / 2), round(c + LIFE_HEART_DROP * px - heart_side / 2)))
    red, green, blue, alpha = image.split()
    red, green, blue = (band.point(lambda v: round(v * LIFE_BRIGHTNESS)) for band in (red, green, blue))
    return Image.merge("RGBA", (red, green, blue, alpha))


def draw_heart(base: tuple[int, int, int], width: float, side: int):
    """A heart ``width`` wide (texture px) in the middle of a ``side`` square: a shade of ``base``,
    darker toward its point, then shaded from its border in."""
    from PIL import Image, ImageDraw

    heart_center = (side / 2, side / 2)
    heart = Image.new("L", (side, side))
    ImageDraw.Draw(heart).polygon(heart_points(width, heart_center), fill=LIFE_HEART_ALPHA)
    top = shade(mix(base, LIFE_HEART_WARM, LIFE_HEART_TOP_WARMTH), LIFE_HEART_SHADE)
    bottom = shade(mix(base, deep_shade(base), LIFE_HEART_BOTTOM_DEPTH), LIFE_HEART_SHADE)
    # Top to bottom over the heart itself.
    _, box_top, _, box_bottom = heart.getbbox()
    gradient = Image.new("L", (side, side))
    gradient.paste(255, (0, box_bottom, side, side))
    gradient.paste(Image.linear_gradient("L").resize((side, box_bottom - box_top)), (0, box_top))
    body = Image.composite(Image.new("RGB", (side, side), bottom), Image.new("RGB", (side, side), top), gradient)
    # How far in: nested hearts, each smaller one drawn over the last.
    depth = Image.new("L", (side, side))
    depth_draw = ImageDraw.Draw(depth)
    steps = round(width / 4)
    for step in range(steps):
        depth_draw.polygon(heart_points(width * (1 - step / steps), heart_center), fill=round(255 * step / steps))
    body = shade_heart(body, depth, deep_shade(base))
    image = body.convert("RGBA")
    image.putalpha(heart)
    return image


def shade_heart(body, depth, deep: tuple[int, int, int]):
    """``depth`` 0 at the heart's border to 255 at its center: a rim in ``deep``, then a light bevel
    fading into the body."""
    from PIL import Image

    def bevel(value: int) -> float:
        d = value / 255
        if d < LIFE_HEART_BEVEL:
            return LIFE_HEART_BEVEL_LIGHT
        return LIFE_HEART_BEVEL_LIGHT * max(1 - (d - LIFE_HEART_BEVEL) / LIFE_HEART_BEVEL_FADE, 0)

    light = depth.point(lambda v: round(255 * bevel(v)))
    rim = depth.point(lambda v: 255 if v / 255 < LIFE_HEART_RIM else 0)
    body = Image.composite(Image.new("RGB", body.size, (255, 255, 255)), body, light)
    return Image.composite(Image.new("RGB", body.size, deep), body, rim)


def draw_counter_font(font_path: Path, folder: Path, scale: float):
    try:
        from PIL import Image
    except ImportError as error:
        raise SystemExit("Pillow is needed: uv sync --extra tools") from error
    folder.mkdir(parents=True, exist_ok=True)
    renderer = GlyphRenderer(font_path, scale)
    shapes = [(glyph, renderer.glyph_masks(glyph, width)) for glyph, width in zip(COUNTER_GLYPHS, COUNTER_GLYPH_WIDTHS, strict=True)]
    for header, (size, cap_height) in HEADERS.items():
        shapes.append((header, renderer.header_masks(header, size, cap_height)))
    for name, (fill, solid, outlined) in shapes:
        for colour in COUNTER_COLOURS:
            image = paint(fill, solid, outlined, colour, renderer.px, name not in UNSHINED)
            size = (image.width // SUPERSAMPLE, image.height // SUPERSAMPLE)
            image = image.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")
            image.save(folder / f"Mai Counter {colour} {name}.png")
    for colour in COUNTER_COLOURS:
        image = draw_life(colour, renderer.px)
        size = (image.width // SUPERSAMPLE, image.height // SUPERSAMPLE)
        image = image.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")
        image.save(folder / f"Mai Counter {colour} Life.png")
    print(f"{len(COUNTER_COLOURS) * (len(shapes) + 1)} sprites written to {folder}")


def main():
    parser = argparse.ArgumentParser(description="Draw the center counter's glyph sprites.")
    parser.add_argument("font", type=Path, help="a .ttf / .otf")
    parser.add_argument("folder", type=Path)
    parser.add_argument("--scale", type=float, default=1, help="texture px per skin px")
    args = parser.parse_args()
    draw_counter_font(args.font, args.folder, args.scale)


if __name__ == "__main__":
    main()
