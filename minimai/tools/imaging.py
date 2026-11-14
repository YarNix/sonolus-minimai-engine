"""Image steps shared by the pack tools: fitting, cropping, painting, colour, cross sections and the sprite
sheet.

Pillow is an optional extra (``uv sync --extra tools``): each function imports it when it runs, so the
modules that use these can be imported without it.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, cast

from minimai.tools.pack_config import parse_color
from minimai.tools.schema import Color, Operations, Rect, Shape

if TYPE_CHECKING:
    from PIL import Image, ImageDraw


# ==== Steps =======================================================================================


def premultiplied_resize(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    from PIL import Image

    return image.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")


def fit_to_canvas(image: Image.Image, size: list[int], stretch: bool, name: str) -> Image.Image:
    """The source on a ``size`` canvas: resized to it (``stretch``), or centered on it at 1 px per px (cut or
    padded). A 0 keeps the source's size on that axis."""
    from PIL import Image

    width = int(size[0]) or image.width
    height = int(size[1]) or image.height
    if (width, height) == image.size:
        return image
    if stretch:
        return premultiplied_resize(image, (width, height))
    left = round((image.width - width) / 2)
    top = round((image.height - height) / 2)
    if left > 0 or top > 0:
        inside = Image.new("L", image.size, 0)
        inside.paste(255, (max(left, 0), max(top, 0), max(left, 0) + min(width, image.width), max(top, 0) + min(height, image.height)))
        cut = Image.composite(Image.new("L", image.size, 0), image.getchannel("A"), inside)
        if sum(cut.histogram()[9:]):
            print(f"{name}: the {image.width}x{image.height} source is cut to the {width}x{height} canvas (visible pixels lost)")
    return image.crop((left, top, left + width, top + height))


def box(rect: Rect, image: Image.Image) -> tuple[int, int, int, int]:
    """``[x, y, w, h]`` on ``image`` as (left, top, right, bottom): a negative x / y counts from the right /
    bottom edge, and a w / h of 0 or less reaches that far edge, less its size."""
    x, y, w, h = (int(part) for part in rect)
    if x < 0:
        x += image.width
    if y < 0:
        y += image.height
    if w <= 0:
        w += image.width - x
    if h <= 0:
        h += image.height - y
    if w <= 0 or h <= 0:
        raise ValueError(f"{rect} leaves nothing of a {image.width}x{image.height} image")
    return x, y, x + w, y + h


def paint_color(value: Color) -> tuple[int, int, int, int]:
    """``"#rrggbb"`` / ``"#rrggbbaa"``, or ``[r, g, b]`` / ``[r, g, b, a]`` in 0-255."""
    if isinstance(value, str):
        text = value.lstrip("#")
        if len(text) not in (6, 8):
            raise ValueError(f"Not a colour: {value!r}")
        parts = [int(text[i : i + 2], 16) for i in range(0, len(text), 2)]
    else:
        parts = [round(float(part)) for part in value]
        if len(parts) not in (3, 4):
            raise ValueError(f"Not a colour: {value!r}")
    r, g, b, a = parts + [255] * (4 - len(parts))
    return r, g, b, a


# Shapes are drawn this many times bigger and scaled down, so their edges are smooth.
PAINT_SUPERSAMPLE = 4


def turned(point: tuple[float, float], center: tuple[float, float], degrees: float) -> tuple[float, float]:
    """``point`` turned ``degrees`` clockwise (on screen) about ``center``."""
    a = math.radians(degrees)
    x, y = point[0] - center[0], point[1] - center[1]
    return center[0] + x * math.cos(a) - y * math.sin(a), center[1] + x * math.sin(a) + y * math.cos(a)


def on_circle(center: tuple[float, float], radius: float, degrees: float) -> tuple[float, float]:
    """The point ``radius`` from ``center`` at ``degrees`` clockwise from the top."""
    a = math.radians(degrees)
    return center[0] + radius * math.sin(a), center[1] - radius * math.cos(a)


def star_points(shape: Shape, center: tuple[float, float]) -> list[tuple[float, float]]:
    """A star's corners (or a regular polygon's, with no inner radius), the first pointing ``rotate`` degrees
    clockwise from the top."""
    rotate = float(shape.get("rotate", 0))
    radius = float(shape["radius"])
    if shape["shape"] == "regular":
        sides = int(shape["sides"])
        return [on_circle(center, radius, rotate + 360 * i / sides) for i in range(sides)]
    count = int(shape.get("tips", 5))
    inner = float(shape["inner"])
    return [on_circle(center, radius if i % 2 == 0 else inner, rotate + 180 * i / count) for i in range(2 * count)]


def shape_copies(shape: Shape, image: Image.Image) -> list[Shape]:
    """The shape, or its ``repeat`` copies: ``count`` of them, each turned ``rotate`` degrees (default an even
    share of a turn) clockwise about ``center`` (default the image's center) from the one before."""
    repeat = shape.get("repeat")
    if not repeat:
        return [shape]
    count = int(repeat["count"])
    step = float(repeat.get("rotate", 360 / count))
    px, py = repeat.get("center", (image.width / 2, image.height / 2))
    pivot = (float(px), float(py))
    copies = []
    for i in range(count):
        degrees = step * i
        copy = cast(Shape, {key: value for key, value in shape.items() if key != "repeat"})
        if shape["shape"] in ("line", "polygon"):
            copy["points"] = [list(turned((float(x), float(y)), pivot, degrees)) for x, y in shape["points"]]
        if shape["shape"] in ("circle", "arc", "star", "regular"):
            cx, cy = shape.get("center", (image.width / 2, image.height / 2))
            copy["center"] = list(turned((float(cx), float(cy)), pivot, degrees))
        if shape["shape"] in ("star", "regular"):
            copy["rotate"] = float(shape.get("rotate", 0)) + degrees
        if shape["shape"] == "arc":
            copy["start"], copy["end"] = float(shape["start"]) + degrees, float(shape["end"]) + degrees
        if shape["shape"] == "rect":
            raise ValueError("a rect can't repeat turned; use a polygon")
        copies.append(copy)
    return copies


def draw_shape(draw: ImageDraw.ImageDraw, shape: Shape, image: Image.Image, color: tuple[int, int, int, int]):
    """One shape on the supersampled layer."""
    s = PAINT_SUPERSAMPLE
    fill = bool(shape.get("fill", False))
    width = float(shape.get("width", 1))
    # Outlines are drawn inside the edge, or centered on it.
    centered = shape.get("align", "inside") == "center"
    kind = shape["shape"]
    cx, cy = shape.get("center", (image.width / 2, image.height / 2))
    center = (float(cx), float(cy))

    def scaled(points):
        return [(float(x) * s - 0.5, float(y) * s - 0.5) for x, y in points]

    def stroke(points, closed: bool):
        """A centered line through ``points`` with rounded joins (and round ends, when ``cap`` asks)."""
        points = scaled(points)
        if closed:
            points = points + points[:2]
        draw.line(points, fill=color, width=round(width * s), joint="curve")
        if not closed and shape.get("cap") == "round":
            r = width * s / 2
            for x, y in (points[0], points[-1]):
                draw.ellipse((x - r, y - r, x + r, y + r), fill=color)

    if kind == "line":
        stroke(shape["points"], bool(shape.get("closed", False)))
    elif kind == "rect":
        left, top, right, bottom = box(shape.get("rect", [0, 0, 0, 0]), image)
        grow = width / 2 if centered and not fill else 0
        corners = ((left - grow) * s, (top - grow) * s, (right + grow) * s - 1, (bottom + grow) * s - 1)
        radius = float(shape.get("radius", 0)) * s
        outline = dict(fill=color) if fill else dict(outline=color, width=round(width * s))
        if radius:
            draw.rounded_rectangle(corners, radius=radius + grow * s, **outline)
        else:
            draw.rectangle(corners, **outline)
    elif kind in ("circle", "arc"):
        r = float(shape["radius"]) + (width / 2 if centered and not fill else 0)
        cx, cy = center
        corners = ((cx - r) * s, (cy - r) * s, (cx + r) * s - 1, (cy + r) * s - 1)
        if kind == "circle":
            outline = dict(fill=color) if fill else dict(outline=color, width=round(width * s))
            draw.ellipse(corners, **outline)
        else:
            # Degrees clockwise from the top; Pillow's start from the right.
            start, end = float(shape["start"]), float(shape["end"])
            if fill:
                draw.pieslice(corners, start - 90, end - 90, fill=color)
            else:
                draw.arc(corners, start - 90, end - 90, fill=color, width=round(width * s))
                if shape.get("cap") == "round":
                    mid = float(shape["radius"]) + (0 if centered else -width / 2)
                    for degrees in (start, end):
                        x, y = on_circle(center, mid, degrees)
                        rr = width * s / 2
                        draw.ellipse((x * s - rr, y * s - rr, x * s + rr, y * s + rr), fill=color)
    elif kind in ("polygon", "star", "regular"):
        points = shape["points"] if kind == "polygon" else star_points(shape, center)
        if fill:
            draw.polygon(scaled(points), fill=color)
        elif centered:
            stroke(points, closed=True)
        else:
            draw.polygon(scaled(points), outline=color, width=round(width * s))
    else:
        raise ValueError(f"Unknown shape {kind!r}")


def paint(image: Image.Image, shapes: list[Shape]) -> Image.Image:
    """``shapes`` drawn over ``image`` in order (``order`` sorts them). Coordinates are px from the top-left
    corner, on pixel edges: pixel (0, 0) spans 0-1, so its center is (0.5, 0.5)."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    s = PAINT_SUPERSAMPLE
    for shape in sorted(shapes, key=lambda shape: float(shape.get("order", 0))):
        color = paint_color(shape.get("color", "#ffffff"))
        layer = Image.new("RGBA", (image.width * s, image.height * s))
        draw = ImageDraw.Draw(layer)
        for copy in shape_copies(shape, image):
            draw_shape(draw, copy, image, color)
        layer = layer.convert("RGBa")
        if shape.get("blur"):
            layer = layer.filter(ImageFilter.GaussianBlur(float(shape["blur"]) * s))
        layer = layer.resize(image.size, Image.Resampling.BOX).convert("RGBA")
        if shape.get("erase"):
            # Clears what the shape covers (as much as its alpha) instead of drawing over it.
            kept = ImageChops.invert(layer.getchannel("A"))
            image = image.copy()
            image.putalpha(ImageChops.multiply(image.getchannel("A"), kept))
        else:
            image = Image.alpha_composite(image, layer)
    return image


def rotated(image: Image.Image, degrees: float, expand: bool) -> Image.Image:
    """Turned ``degrees`` counterclockwise about its center; ``expand`` grows the image to fit, otherwise it
    keeps its size and the corners are cut."""
    from PIL import Image

    if degrees % 360 == 0:
        return image
    if degrees % 90 == 0 and (expand or image.width == image.height):
        turns = {90: Image.Transpose.ROTATE_90, 180: Image.Transpose.ROTATE_180, 270: Image.Transpose.ROTATE_270}
        return image.transpose(turns[int(degrees) % 360])
    turned = image.convert("RGBa").rotate(degrees, Image.Resampling.BICUBIC, expand=expand)
    return turned.convert("RGBA")


def apply_operations(image: Image.Image, stage: Operations, expand: bool) -> Image.Image:
    """A stage's ``crop``, ``paint``, ``flip`` and ``rotate``, in that order."""
    from PIL import Image

    if "crop" in stage:
        image = image.crop(box(stage["crop"], image))
    if "paint" in stage:
        image = paint(image, stage["paint"])
    if "flip" in stage:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT if stage["flip"] == "x" else Image.Transpose.FLIP_TOP_BOTTOM)
    if "rotate" in stage:
        image = rotated(image, float(stage["rotate"]), expand)
    return image


def apply_levels(image: Image.Image, multiply: float, add: float) -> Image.Image:
    from PIL import Image

    r, g, b, a = image.split()
    table = [max(0, min(255, round(v * multiply + add))) for v in range(256)]
    return Image.merge("RGBA", (r.point(table), g.point(table), b.point(table), a))


def apply_tint(image: Image.Image, color: Color) -> Image.Image:
    from PIL import Image

    tint = parse_color(color)
    r, g, b, a = image.split()
    channels = [channel.point([round(v * part) for v in range(256)]) for channel, part in zip((r, g, b), tint)]
    return Image.merge("RGBA", (*channels, a))



# ==== Cross sections ==============================================================================


def find_band_radius(image: Image.Image, normal: tuple[float, float]) -> float:
    """The distance from the image's center to the middle of the widest opaque band along ``normal``
    (where alpha crosses half), to the nearest half pixel."""
    from PIL import Image

    cx, cy = image.width / 2, image.height / 2
    steps = int(math.hypot(cx, cy) * 4)
    # The alpha along the normal, bilinear, every quarter pixel.
    line = image.getchannel("A").transform(
        (steps, 1), Image.Transform.AFFINE, (normal[0] / 4, 0, cx, normal[1] / 4, 0, cy), Image.Resampling.BILINEAR
    )
    profile = [line.getpixel((i, 0)) for i in range(steps)]
    best = None
    best_width = 0.0
    start = None
    for i in range(1, steps):
        before, after = profile[i - 1], profile[i]
        crossing = (i - 1 + (127.5 - before) / (after - before)) / 4 if before != after else i / 4
        if before < 127.5 <= after:
            start = crossing
        elif before >= 127.5 > after and start is not None:
            if crossing - start > best_width:
                best_width, best = crossing - start, (start + crossing) / 2
            start = None
    if best is None:
        raise ValueError("no opaque band to cut across")
    return round(best * 2) / 2


def cross_section(
    image: Image.Image, side: int, width: int = 8, length: int = 52, radius: float | str = "auto"
) -> Image.Image:
    """A ``width`` x ``length`` strip across side ``side`` (1-4 clockwise from the top-right) of a touch hold
    border, at the side's middle: across it from the outside in, and along it clockwise."""
    from PIL import Image

    width, length = int(width), int(length)
    angle = math.radians(45 - 90 * (side - 1))
    # Image y points down.
    normal = (math.cos(angle), -math.sin(angle))
    tangent = (-normal[1], normal[0])
    r0 = find_band_radius(image, normal) if radius == "auto" else float(radius)
    cx, cy = image.width / 2, image.height / 2
    # Output (X, Y) -> input: center + normal * (r0 - (Y - length / 2)) + tangent * (X - width / 2).
    data = (
        tangent[0], -normal[0], cx + normal[0] * (r0 + length / 2) - tangent[0] * width / 2,
        tangent[1], -normal[1], cy + normal[1] * (r0 + length / 2) - tangent[1] * width / 2,
    )
    strip = image.convert("RGBa").transform((width, length), Image.Transform.AFFINE, data, Image.Resampling.BILINEAR)
    return strip.convert("RGBA")


# ==== Sprite sheet ================================================================================


def pack_rects(sizes: list[tuple[int, int]], side: int) -> list[tuple[int, int]] | None:
    """Skyline bottom-left packing of ``sizes`` (tallest first) in a ``side`` square; None if they don't fit."""
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i][1], -sizes[i][0]))
    # Segments (x, y, width) of the skyline, left to right.
    skyline = [(0, 0, side)]
    places: list[tuple[int, int] | None] = [None] * len(sizes)
    for i in order:
        w, h = sizes[i]
        best = None
        for start in range(len(skyline)):
            x = skyline[start][0]
            if x + w > side:
                break
            y = 0
            covered = 0
            end = start
            while covered < w:
                y = max(y, skyline[end][1])
                covered += skyline[end][2]
                end += 1
            if y + h <= side and (best is None or (y + h, x) < (best[1] + h, best[0])):
                best = (x, y, start, end)
        if best is None:
            return None
        x, y, start, end = best
        places[i] = (x, y)
        right = x + w
        last_x, last_y, last_w = skyline[end - 1]
        tail = [(right, last_y, last_x + last_w - right)] if last_x + last_w > right else []
        skyline[start:end] = [(x, y + h, w), *tail]
        merged_line = []
        for segment in skyline:
            if merged_line and merged_line[-1][1] == segment[1]:
                px_, py, pw = merged_line[-1]
                merged_line[-1] = (px_, py, pw + segment[2])
            else:
                merged_line.append(segment)
        skyline = merged_line
    return places


def build_sheet(images: list[Image.Image], padding: int, max_size: int) -> tuple[Image.Image, list[tuple[int, int]]]:
    """The sprites on one square power-of-two texture, each with its edge repeated ``padding`` px around it
    (so filtering doesn't pick up its neighbours). Returns the texture and each sprite's (x, y)."""
    from PIL import Image

    sizes = [(image.width + 2 * padding, image.height + 2 * padding) for image in images]
    side = 256
    while True:
        places = pack_rects(sizes, side)
        if places is not None:
            break
        side *= 2
        if side > max_size:
            raise ValueError(f"the sprites don't fit a {max_size} px texture")
    sheet = Image.new("RGBA", (side, side))
    origins = []
    for image, (x, y) in zip(images, places):
        sheet.paste(edge_padded(image, padding) if padding else image, (x, y))
        origins.append((x + padding, y + padding))
    return sheet, origins


def edge_padded(image: Image.Image, padding: int) -> Image.Image:
    """``image`` with its edge pixels repeated ``padding`` px outward."""
    from PIL import Image

    w, h = image.size
    result = Image.new("RGBA", (w + 2 * padding, h + 2 * padding))
    result.paste(image, (padding, padding))
    for i in range(padding):
        result.paste(image.crop((0, 0, w, 1)), (padding, i))
        result.paste(image.crop((0, h - 1, w, h)), (padding, h + padding + i))
    for i in range(padding):
        result.paste(result.crop((padding, 0, padding + 1, h + 2 * padding)), (i, 0))
        result.paste(result.crop((w + padding - 1, 0, w + padding, h + 2 * padding)), (w + padding + i, 0))
    return result
