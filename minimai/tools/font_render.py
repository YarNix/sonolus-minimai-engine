"""Draw sprites from text: the center counter's glyphs, the preview's labels, and any others a config adds.

Usage: python -m minimai.tools.font_render <folder> [--config C] [--font F] [--scale S]

Needs Pillow (``uv sync --extra tools``). What is drawn, and how, is a config: the defaults are in
``tools/defaults/font_render.toml`` and ``--config`` is merged over them (docs/font_render.md). Every sprite of
every group in ``sprite_groups`` is written where the skin's default recipe reads it
(``CounterSkins/counter_combo_0.png``; ``<its name>.png`` when it has none), sized for the layout at one texture
px per skin px times ``scale``.
"""

from __future__ import annotations

import argparse
import json
import math
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from minimai.lib.layout import COUNTER_GLYPH_WIDTHS, COUNTER_LINE_HEIGHT, SKIN_RING_RADIUS_PX
from minimai.lib.skin import COUNTER_GLYPHS
from minimai.preview.layout import PREVIEW_LABEL_ASPECT, PREVIEW_SHAPE_LABEL_ASPECT
from minimai.tools.pack_config import merged, resolve
from minimai.tools.skin_pack import default_source_path

if TYPE_CHECKING:
    from PIL import Image, ImageFont

DEFAULTS_PATH = Path(__file__).parent / "defaults" / "font_render.toml"
# Properties each character can have of its own (from a glyph_style); the rest are the sprite's.
CHARACTER_KEYS = {
    "font",
    "font_index",
    "variation",
    "stretch_x",
    "skew",
    "bolden",
    "offset",
    "advance",
    "left",
    "right",
    "fill_counters",
    "fill_hooks",
    "shape",
    "power",
    "shape_size",
}
PREVIEW_LABEL_HEIGHT = 64


def layout_cells() -> dict[str, list[int]]:
    """The defaults' cell params, as lib/layout.py has them."""
    widths = {glyph: round(width * SKIN_RING_RADIUS_PX) for glyph, width in zip(COUNTER_GLYPHS, COUNTER_GLYPH_WIDTHS)}
    line = round(COUNTER_LINE_HEIGHT * SKIN_RING_RADIUS_PX)
    return {
        "counter_digit_cell": [widths["0"], line],
        "counter_dot_cell": [widths["Dot"], line],
        "counter_percent_cell": [widths["Percent"], line],
        "counter_sign_cell": [widths["Plus"], line],
        "counter_star_cell": [widths["Star"], line],
        "preview_label_cell": [round(PREVIEW_LABEL_HEIGHT * PREVIEW_LABEL_ASPECT), PREVIEW_LABEL_HEIGHT],
        "preview_shape_cell": [round(PREVIEW_LABEL_HEIGHT * PREVIEW_SHAPE_LABEL_ASPECT), PREVIEW_LABEL_HEIGHT],
    }


# ==== Masks =======================================================================================


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

    return morph(mask, radius, ImageChops.lighter) if radius > 0 else mask


def erode(mask, radius: float):
    from PIL import ImageChops

    return morph(mask, radius, ImageChops.darker) if radius > 0 else mask


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


def star_points(center: tuple[float, float], height: float, power: float) -> list[tuple[float, float]]:
    """A four-pointed star with curved-in sides (✧, an astroid), ``height`` tall."""
    shape = []
    for i in range(400):
        t = 2 * math.pi * i / 400
        x, y = math.cos(t), math.sin(t)
        shape.append((math.copysign(abs(x) ** power, x), math.copysign(abs(y) ** power, y)))
    r = height / 2
    return [(center[0] + r * x, center[1] - r * y) for x, y in shape]


# ==== Config ======================================================================================


def merge_groups(defaults: list, overrides: list) -> list:
    """``sprite_groups`` merged by name: a group of a known name merges into it, a new one is added."""
    result = [dict(group) for group in defaults]
    index = {group["name"]: i for i, group in enumerate(result)}
    for group in overrides:
        if group.get("name") in index:
            result[index[group["name"]]] = merged(result[index[group["name"]]], group)
        else:
            result.append(dict(group))
    return result


def load_config(path: Path | None) -> dict:
    """The defaults with the config at ``path`` merged over them; its fonts are relative to it."""
    with DEFAULTS_PATH.open("rb") as file:
        config = tomllib.load(file)
    stale = {key: value for key, value in layout_cells().items() if config["params"].get(key) != value}
    if stale:
        raise SystemExit(f"{DEFAULTS_PATH.name}: cells differ from the layout: {stale}")
    if path is None:
        return config
    with path.open("rb") as file:
        override = tomllib.load(file)
    relative_fonts(override, path.parent)
    groups = merge_groups(config.get("sprite_groups", []), override.pop("sprite_groups", []))
    config = merged(config, override)
    config["sprite_groups"] = groups
    cells = {key: value for key, value in layout_cells().items() if config["params"].get(key) != value}
    if cells:
        print(f"Cells that differ from the layout (the engine stretches those sprites): {cells}")
    return config


def relative_fonts(value, folder: Path):
    """Every ``font`` path in a config, made relative to ``folder``."""
    if isinstance(value, dict):
        for key, part in value.items():
            if key == "font" and isinstance(part, str) and part:
                value[key] = str(folder / part)
            else:
                relative_fonts(part, folder)
    elif isinstance(value, list):
        for part in value:
            relative_fonts(part, folder)


def look_properties(name: str, looks: Mapping, seen: tuple = ()) -> dict:
    """A look's properties, over the look it starts from."""
    if name in seen:
        raise SystemExit(f"Looks start from each other in a loop: {' -> '.join((*seen, name))}")
    if name not in looks:
        raise SystemExit(f"No look named {name!r}")
    look = dict(looks[name])
    parent = look.pop("look", None)
    return merged(look_properties(parent, looks, (*seen, name)), look) if parent else look


def sprite_list(sprites) -> list[dict]:
    """A group's ``sprites`` (after params): a list of sprites, or of lists of them."""
    result = []
    for item in [sprites] if isinstance(sprites, Mapping) else sprites:
        result.extend(sprite_list(item) if isinstance(item, list) else [dict(item)])
    return result


# A sprite's own: its lines can't set them.
SPRITE_ONLY_KEYS = {"cell", "scale", "supersample", "opacity", "brightness"}


def line_list(value, where: str) -> list[dict]:
    """``lines``: a list of line tables; a string is short for a line with that text, on its own or in the list."""
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        raise SystemExit(f"{where}: lines must be a string or a list")
    return [{"text": line} if isinstance(line, str) else dict(line) for line in value]


def merged_lines(*levels: list[dict]) -> list[dict]:
    """Lines merged by index: line i of each level over line i of the one before."""
    result: list[dict] = []
    for lines in levels:
        for i, line in enumerate(lines):
            if i < len(result):
                result[i] = merged(result[i], line)
            else:
                result.append(line)
    return result


def check_lines(name: str, props: Mapping):
    if "text" in props:
        raise SystemExit(f'{name}: text goes in lines: lines = "..." or lines = [{{ text = "..." }}]')
    lines = props.get("lines")
    if not lines:
        raise SystemExit(f"{name}: no lines")
    for i, line in enumerate(lines, 1):
        if line.get("skip"):
            continue
        if "text" not in line:
            raise SystemExit(f"{name}: line {i} has no text (skip = true leaves it out)")
        own = SPRITE_ONLY_KEYS & set(line)
        if own:
            raise SystemExit(f"{name}: line {i}: {', '.join(sorted(own))} can only be set for the whole sprite")


def sprite_lines(props: Mapping, styles: Mapping) -> list[tuple[int, dict, dict]]:
    """The lines drawn, each as (its index, its properties over the sprite's, its glyph styles)."""
    base = {key: value for key, value in props.items() if key != "lines"}
    result = []
    for i, line in enumerate(props["lines"]):
        if line.get("skip"):
            continue
        line = dict(line)
        line_styles = merged(styles, line.pop("glyph_style", {}))
        line_props = merged(base, line)
        if len(props["lines"]) > 1 and "name" in line_props:
            line_props["name"] = f"{line_props['name']} (line {i + 1})"
        result.append((i, line_props, line_styles))
    return result


def expand_groups(config: Mapping) -> list[tuple[str, dict, dict, str]]:
    """Every sprite as (file name, its properties, the glyph styles that apply to it, its group's name).
    ``lines`` merge by index (the group's, then the sprite's), each written out as a table."""
    params = dict(config.get("params", {}))
    # Params may use other params.
    for _ in range(8):
        resolved = {key: resolve(value, params) for key, value in params.items()}
        if resolved == params:
            break
        params = resolved
    looks = resolve(config.get("looks", {}), params)
    defaults = resolve(config.get("defaults", {}), params)
    glyph_style = resolve(config.get("glyph_style", {}), params)
    result = []
    for group in config.get("sprite_groups", []):
        group: dict = resolve(dict(group), params)
        if group.get("skip"):
            continue
        base = dict(defaults)
        if config.get("font"):
            base["font"] = config["font"]
        if "look" in group:
            base = merged(base, look_properties(group.pop("look"), looks))
        sprites = sprite_list(group.pop("sprites", []))
        name = group.pop("name")
        group_styles = group.pop("glyph_style", {})
        base_lines = line_list(base.pop("lines", []), name)
        group_lines = line_list(group.pop("lines", []), name)
        group = merged(base, group)
        for sprite in sprites:
            sprite_styles = sprite.pop("glyph_style", {})
            sprite_name = name.format(sprite=sprite["name"])
            lines = merged_lines(base_lines, group_lines, line_list(sprite.pop("lines", []), sprite_name))
            props = merged(group, sprite)
            if props.get("skip"):
                continue
            props["lines"] = lines
            check_lines(sprite_name, props)
            styles = merged(merged(glyph_style, group_styles), sprite_styles)
            result.append((sprite_name, props, styles, name))
    return result


# ==== Rendering ===================================================================================


class Fonts:
    def __init__(self):
        self.cache: dict = {}
        self.warned: set[str] = set()

    def get(self, props: Mapping, px: float) -> ImageFont.FreeTypeFont:
        """The character's font at its size: ``size.ink_height`` (skin px) for the reference's ink, or
        ``size.em``."""
        size = props.get("size", {})
        key = json.dumps([props.get("font"), props.get("font_index", 0), props.get("variation"), size, px], sort_keys=True)
        if key in self.cache:
            return self.cache[key]
        path = props.get("font")
        if not path:
            raise ValueError("no font")
        index = int(props.get("font_index", 0))
        if "em" in size:
            points = round(float(size["em"]) * px)
        else:
            probe = self.load(path, index, 1000, props)
            _, top, _, bottom = probe.getbbox(str(size.get("reference", "1")), anchor="ls")
            points = round(1000 * float(size["ink_height"]) * px / (bottom - top))
        font = self.cache[key] = self.load(path, index, points, props)
        return font

    def load(self, path: str, index: int, points: int, props: Mapping):
        from PIL import ImageFont

        font = ImageFont.truetype(path, points, index=index)
        variation = props.get("variation")
        if isinstance(variation, str):
            font.set_variation_by_name(variation)
        elif variation:
            axes = font.get_variation_axes()
            names = [str(axis["name"], "utf-8") if isinstance(axis["name"], bytes) else str(axis["name"]) for axis in axes]
            values = [axis["default"] for axis in axes]
            for axis, value in variation.items():
                matches = [i for i, name in enumerate(names) if name.lower() == axis.lower()]
                if not matches:
                    raise ValueError(f"the font has no {axis!r} axis (it has {', '.join(names)})")
                values[matches[0]] = value
            font.set_variation_by_axes(values)
        return font

    def features(self, props: Mapping) -> list[str] | None:
        from PIL import features

        wanted = props.get("features")
        if not wanted:
            return None
        if not features.check("raqm"):
            if "raqm" not in self.warned:
                print("OpenType features need Pillow built with Raqm; drawing without them")
                self.warned.add("raqm")
            return None
        return list(wanted)


def character_props(props: Mapping, styles: Mapping, character: str) -> dict:
    """A character's properties: the sprite's, then its glyph style."""
    own = {key: value for key, value in props.items() if key in CHARACTER_KEYS}
    style = styles.get(character, {})
    unknown = set(style) - CHARACTER_KEYS
    if unknown:
        print(f"glyph_style {character!r}: not character properties (ignored): {', '.join(sorted(unknown))}")
    return merged(own, {key: value for key, value in style.items() if key in CHARACTER_KEYS})


def transformed(mask, matrix: tuple[float, ...]):
    """``mask`` through the forward affine ``matrix`` (a, b, c, d, e, f: x' = a x + b y + c, y' = d x + e y + f)."""
    from PIL import Image

    a, b, c, d, e, f = matrix
    det = a * e - b * d
    inverse = (e / det, -b / det, (b * f - c * e) / det, -d / det, a / det, (c * d - a * f) / det)
    return mask.transform(mask.size, Image.Transform.AFFINE, inverse, Image.Resampling.BICUBIC)


class SpriteRenderer:
    def __init__(self, fonts: Fonts):
        self.fonts = fonts
        self.mask_cache: dict = {}

    def run(self, props: Mapping, styles: Mapping, size: tuple[int, int], px: float, shrunk: int = 0):
        """Each character's raw (antialiased) mask on a ``size`` canvas, laid out in the line's ``box`` (default
        the whole canvas), and its properties."""
        from PIL import Image, ImageDraw

        text = str(props.get("text", ""))
        case = props.get("case", "")
        text = text.upper() if case == "upper" else text.lower() if case == "lower" else text
        features = self.fonts.features(props)
        width, height = size
        # The box the line is laid out in, in canvas px.
        if "box" in props:
            bx, by, bw, bh = (float(part) * px for part in props["box"])
        else:
            bx, by, bw, bh = 0, 0, width, height
        characters = [(character, character_props(props, styles, character)) for character in text]
        # The reference's ink height sets the baseline (centered on the cell) and a shape's size.
        size_rule = props.get("size", {})
        reference_height = float(size_rule.get("ink_height", 0)) * px
        if not reference_height:
            font = self.fonts.get(props, px)
            _, top, _, bottom = font.getbbox(str(size_rule.get("reference", "1")), anchor="ls")
            reference_height = bottom - top

        # Pen positions: each character's advance, with the font's kerning to the one before.
        tracking = float(props.get("tracking", 0)) * px
        pairs = props.get("kerning", {})
        placed = []
        pen = 0.0
        previous = None
        for i, (character, own) in enumerate(characters):
            sized = merged(own, {"size": props.get("size", {})})
            if own.get("shape"):
                font, advance = None, reference_height * float(own.get("shape_size", 1))
            else:
                font = self.fonts.get(sized, px)
                advance = font.getlength(character, features=features)
                if previous and previous[1] is font:
                    pair = font.getlength(previous[0] + character, features=features)
                    pen += pair - font.getlength(previous[0], features=features) - advance
            if previous:
                pen += float(pairs.get(previous[0] + character, 0)) * px + tracking
            if "advance" in own:
                advance = float(own["advance"]) * px
            pen += float(own.get("left", 0)) * px
            placed.append((character, own, font, pen, advance))
            pen += advance + float(own.get("right", 0)) * px
            previous = (character, font)
        run_width = pen

        margin = float(props.get("margin", 0)) * px
        align_x, align_y = props.get("align_x", "advance"), props.get("align_y", "reference")
        x0 = bx + (bw - run_width) / 2
        if align_x == "left":
            x0 = bx + margin
        elif align_x == "right":
            x0 = bx + bw - margin - run_width
        baseline = by + (bh + reference_height) / 2
        if align_y == "baseline":
            baseline = by + float(props.get("baseline", 0)) * px

        # A run to fit is drawn whole on a canvas of its own width, then resized into the cell.
        fitting = props.get("fit") == "width"
        # Other text is drawn with room on both sides, a whole number of px, so what overflows the cell is
        # still there to measure; it's cropped back to the cell at the end.
        if fitting:
            canvas_width = max(width, math.ceil(run_width + 4 * reference_height))
            # Its ink is cropped, so it starts on a whole pixel, wherever that is.
            shift = math.floor((canvas_width - run_width) / 2) - x0
        else:
            pad = math.ceil(run_width + reference_height)
            canvas_width, shift = width + 2 * pad, pad

        # Text whose characters are all alike, laid out by the font alone and filled as a whole, is drawn in
        # one call, as the font places it.
        own_keys = {"offset", "advance", "left", "right", "stretch_x", "skew", "shape"}
        as_one = (
            props.get("fill_scope") == "sprite"
            and placed
            and not tracking
            and not pairs
            and all(own == placed[0][1] and font is placed[0][2] for _, own, font, _, _ in placed)
            and not own_keys & set(placed[0][1])
        )

        def draw(dx: float, dy: float):
            if as_one:
                mask = Image.new("L", (canvas_width, height))
                ImageDraw.Draw(mask).text(
                    (x0 + shift + dx, baseline + dy), "".join(c for c, *_ in placed), font=placed[0][2], fill=255,
                    anchor="ls", features=features,
                )
                return [(mask, placed[0][1])]
            masks = []
            for character, own, font, x, advance in placed:
                ox, oy = (float(part) * px for part in own.get("offset", (0, 0)))
                mask = Image.new("L", (canvas_width, height))
                left = x0 + shift + x + dx + ox
                if own.get("shape") == "star":
                    center = (left + advance / 2, by + bh / 2 + dy + oy)
                    star_height = reference_height * float(own.get("shape_size", 1))
                    ImageDraw.Draw(mask).polygon(star_points(center, star_height, float(own.get("power", 3))), fill=255)
                elif own.get("shape"):
                    raise ValueError(f"unknown shape {own['shape']!r}")
                else:
                    ImageDraw.Draw(mask).text(
                        (left, baseline + dy + oy), character, font=font, fill=255, anchor="ls", features=features
                    )
                # Stretch and slant about the character's origin on the baseline.
                sx, slant = float(own.get("stretch_x", 1)), math.tan(math.radians(float(own.get("skew", 0))))
                matrix = (sx, -slant, left * (1 - sx) + slant * (baseline + dy), 0.0, 1.0, 0.0)
                if matrix != (1.0, 0.0, 0.0, 0.0, 1.0, 0.0):
                    mask = transformed(mask, matrix)
                masks.append((mask, own))
            return masks

        def union_box(masks):
            from PIL import ImageChops

            union = Image.new("L", (canvas_width, height))
            for mask, _ in masks:
                union = ImageChops.lighter(union, mask)
            return union.getbbox()

        masks = draw(0, 0)
        dx = dy = 0.0
        if align_x == "ink" or align_y == "ink":
            box = union_box(masks)
            if box:
                left, top, right, bottom = box
                # A run to fit is centered on its own canvas; it's cropped to its ink anyway.
                middle = canvas_width / 2 if fitting else shift + bx + bw / 2
                dx = middle - (left + right) / 2 if align_x == "ink" else 0
                dy = by + bh / 2 - (top + bottom) / 2 if align_y == "ink" else 0
                masks = draw(dx, dy)
        if not fitting and props.get("overflow", "shrink") in ("shrink", "shrink_group"):
            # The ink the outlines grow from: the masks are cut at half.
            box = union_box([(mask.point(lambda v: 255 if v >= 128 else 0), own) for mask, own in masks])
            boldest = max((float(own.get("bolden", 0)) for _, own in masks), default=0)
            room = (sum(float(layer["width"]) for layer in props.get("outlines", [])) + boldest) * px
            if box:
                # What gets cut is what the outlines take past the box's sides.
                ink = box[2] - box[0]
                available = bw - 2 * room
                past_left = shift + bx - (box[0] - room)
                past_right = box[2] + room - (shift + bx + bw)
                if (past_left > 0 or past_right > 0) and ink <= available:
                    # It fits: moved back inside.
                    masks = draw(dx + max(past_left, 0) - max(past_right, 0), dy)
                elif (past_left > 0 or past_right > 0) and ink > 0 and available > 0 and shrunk < 4:
                    # Smaller by the overshoot, then measured again: font sizes are whole points.
                    factor = min(available / ink, 1) * 0.99
                    size_rule = dict(props.get("size", {}))
                    for key in ("ink_height", "em"):
                        if key in size_rule:
                            size_rule[key] = float(size_rule[key]) * factor
                    if "ink_height" not in size_rule and "em" not in size_rule:
                        size_rule["ink_height"] = reference_height / px * factor
                    return self.run(merged(props, {"size": size_rule}), styles, size, px, shrunk + 1)
        self.final_size = props.get("size", {})
        if shrunk and props.get("name") and props.get("overflow", "shrink") == "shrink":
            print(f"  {props['name']}: shrunk to {size_value(props['size']):.1f} px to fit its cell")
        if fitting:
            box = union_box(masks)
            if box:
                left, right = box[0], box[2]
                boldest = max((float(own.get("bolden", 0)) for _, own in masks), default=0)
                outline = sum(float(layer["width"]) for layer in props.get("outlines", []))
                target = round(bw - 2 * (margin + (outline + boldest) * px))
                fitted = []
                for mask, own in masks:
                    run = mask.crop((left, 0, right, height)).resize((target, height), Image.Resampling.LANCZOS)
                    cell = Image.new("L", size)
                    cell.paste(run, (round(bx + (bw - target) / 2), 0))
                    fitted.append((cell, own))
                masks = fitted
        else:
            masks = [(mask.crop((shift, 0, shift + width, height)), own) for mask, own in masks]
        return masks

    def masks(self, props: Mapping, styles: Mapping, size: tuple[int, int], px: float):
        """The fill, the filled-in silhouette and each outline, cropped to the cell."""
        from PIL import Image, ImageChops, ImageOps

        key = json.dumps([{k: v for k, v in props.items() if k not in PAINT_KEYS}, styles, size, px], sort_keys=True)
        if key in self.mask_cache:
            return self.mask_cache[key]
        outlines = [float(layer["width"]) * px for layer in props.get("outlines", [])]
        characters = self.run(props, styles, size, px)
        # "sprite": holes and hooks are filled once, on the combined text, with the sprite's settings.
        whole = props.get("fill_scope", "character") == "sprite"
        settings = [props] if whole else [own for _, own in characters]
        hook_room = max((float(own["fill_hooks"]["radius"]) for own in settings if own.get("fill_hooks")), default=0)
        shadow = props.get("shadow") or {}
        shadow_room = (abs(float(shadow.get("blur", 0))) * 3 + max(map(abs, shadow.get("offset", (0, 0))))) * px if shadow else 0
        # Room round the cell, so the dilations don't wrap round its edges.
        margin = int(hook_room * px + sum(outlines) + shadow_room + max(
            (float(own.get("bolden", 0)) for _, own in characters), default=0) * px) + 2
        full = (size[0] + 2 * margin, size[1] + 2 * margin)
        fill, solid = Image.new("L", full), Image.new("L", full)
        for raw, own in characters:
            ink = raw.point(lambda v: 255 if v >= 128 else 0)
            box = ink.getbbox()
            if not box:
                continue
            # Each character on its own box with the margin round it: the same result as on the whole
            # canvas, with far less to flood-fill.
            part = ImageOps.expand(ink.crop(box), margin)
            part = dilate(part, float(own.get("bolden", 0)) * px)
            shape = part if whole else filled_in(part, own, px)
            for target, layer in ((fill, part), (solid, shape)):
                placed = Image.new("L", full)
                placed.paste(layer, box[:2])
                target.paste(ImageChops.lighter(target, placed))
        if whole:
            box = fill.getbbox()
            if box:
                # The text's box with the margin round it, as for a character.
                region = (max(box[0] - margin, 0), max(box[1] - margin, 0), min(box[2] + margin, full[0]), min(box[3] + margin, full[1]))
                solid = Image.new("L", full)
                solid.paste(filled_in(fill.crop(region), props, px), region[:2])
        layers = []
        reach = 0.0
        for width in outlines:
            reach += width
            layers.append(dilate(solid, reach))
        outer = layers[-1] if layers else solid
        bbox = outer.getbbox()
        if bbox and props.get("overflow", "shrink") != "cut" and (bbox[0] < margin or bbox[2] > margin + size[0]):
            print(f"  {props.get('name')}: wider than its cell, the sides are cut off")
        silhouette = outer
        box = (margin, margin, margin + size[0], margin + size[1])
        result = (fill.crop(box), solid.crop(box), [layer.crop(box) for layer in layers], silhouette, margin)
        self.mask_cache[key] = result
        return result

    def shrunk_size(self, props: Mapping, styles: Mapping) -> dict:
        """A line's ``size`` once shrunk to fit its box."""
        supersample = int(props.get("supersample", 4))
        scale = float(props.get("scale", 1))
        size = tuple(round(float(side) * scale) * supersample for side in props["cell"])
        self.run(props, styles, size, scale * supersample)
        return dict(self.final_size)

    def render(self, props: Mapping, styles: Mapping) -> Image.Image:
        from PIL import Image

        supersample = int(props.get("supersample", 4))
        scale = float(props.get("scale", 1))
        px = scale * supersample
        if "cell" not in props:
            raise ValueError("no cell")
        cell = props["cell"]
        size = tuple(round(float(side) * scale) * supersample for side in cell)
        # Each line painted on the whole cell, over the ones before it.
        image = None
        for _, line, line_styles in sprite_lines(props, styles):
            fill, solid, layers, silhouette, margin = self.masks(line, line_styles, size, px)
            painted = paint(fill, solid, layers, line, px)
            shadow = line.get("shadow")
            if shadow:
                painted = with_shadow(painted, silhouette, margin, shadow, px)
            image = painted if image is None else Image.alpha_composite(image, painted)
        if image is None:
            image = Image.new("RGBA", size)
        return finish(image, props, supersample)


def filled_in(mask, settings: Mapping, px: float):
    """``mask`` with its holes (``fill_counters``) or its holes and hook openings (``fill_hooks``) filled in."""
    hooks = settings.get("fill_hooks")
    if hooks:
        return fill_hooks(mask, float(hooks["radius"]) * px, float(hooks["room_width"]) * px, float(hooks["enclosure"]))
    if settings.get("fill_counters"):
        return fill_holes(mask)
    return mask


def size_value(size_rule: Mapping) -> float:
    return float(size_rule.get("ink_height", size_rule.get("em", 0)))


# Properties that only change the paint, not the masks.
PAINT_KEYS = {"fill", "counter_fill", "shine", "pattern", "edge", "opacity", "brightness", "name"}


# ==== Paint =======================================================================================


def rgb(value) -> tuple[int, ...]:
    return tuple(int(part) for part in value)


def shade(colour: tuple[int, ...], factor: float) -> tuple[int, ...]:
    return tuple(round(c * factor) for c in colour)


def lighten(colour: tuple[int, ...], amount: float) -> tuple[int, ...]:
    return tuple(round(c + (255 - c) * amount) for c in colour)


def shine_mask(fill, reach: float, fade: float):
    """An L mask, full at the fill's top left corner, fading out ``reach`` of the way along its
    diagonal (over ``fade``)."""
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
    low, high = (reach - fade / 2) * 255, (reach + fade / 2) * 255
    mask.paste(diagonal.point(lambda v: round(255 * min(max((high - v) / (high - low), 0), 1))), box)
    return mask


def pattern_mask(size: tuple[int, int], kind: str, step: float):
    """An L mask of where the pattern goes: a checker of ``step`` squares, or ``\\`` stripes ``step`` apart."""
    from PIL import Image, ImageDraw

    mask = Image.new("L", size)
    draw = ImageDraw.Draw(mask)
    if kind == "checker":
        for row in range(int(size[1] / step) + 1):
            for column in range(row % 2, int(size[0] / step) + 1, 2):
                draw.rectangle((column * step, row * step, (column + 1) * step - 1, (row + 1) * step - 1), fill=255)
    elif kind == "stripes":
        offset = -float(size[1])
        while offset < size[0]:
            draw.polygon(
                [(offset, 0), (offset + step / 2, 0), (offset + step / 2 + size[1], size[1]), (offset + size[1], size[1])],
                fill=255,
            )
            offset += step
    else:
        raise ValueError(f"unknown pattern {kind!r}")
    return mask


def paint(fill, solid, layers: list, props: Mapping, px: float):
    """The masks painted: outlines (outermost first), the filled-in counters, the fill (with its shine and
    pattern) and its edge."""
    from PIL import Image, ImageChops

    base = rgb(props.get("fill", (255, 255, 255)))
    body = Image.new("RGB", fill.size, base)
    shine = props.get("shine")
    if shine:
        amount = float(shine["amount"])
        tint = lighten(base, amount) if shine.get("tone", "light") == "light" else shade(base, 1 - amount)
        body.paste(tint, mask=shine_mask(fill, float(shine["reach"]), float(shine.get("fade", 0.12))))
    pattern = props.get("pattern")
    if pattern:
        darker = ImageChops.multiply(body, Image.new("RGB", fill.size, (round(255 * float(pattern["shade"])),) * 3))
        body.paste(darker, mask=pattern_mask(fill.size, pattern["kind"], float(pattern["size"]) * px))
    outlines = props.get("outlines", [])
    background = rgb(outlines[0]["color"]) if outlines else base
    image = Image.new("RGBA", fill.size, background + (0,))
    for layer, outline in reversed(list(zip(layers, outlines))):
        image.paste(rgb(outline["color"]) + (255,), mask=layer)
    if props.get("counter_fill"):
        image.paste(rgb(props["counter_fill"]) + (255,), mask=ImageChops.subtract(solid, fill))
    image.paste(body, mask=fill)
    edge = props.get("edge")
    if edge:
        rim = ImageChops.subtract(fill, erode(fill, float(edge["width"]) * px))
        image.paste(shade(base, float(edge["shade"])) + (255,), mask=rim)
    return image


def with_shadow(image, silhouette, margin: int, shadow: Mapping, px: float):
    """``image`` over a shadow of its silhouette: ``offset`` and ``blur`` in skin px, ``color`` with alpha."""
    from PIL import Image, ImageChops, ImageFilter

    color = rgb(shadow.get("color", (0, 0, 0, 128)))
    alpha = color[3] if len(color) > 3 else 255
    dx, dy = (round(float(part) * px) for part in shadow.get("offset", (0, 0)))
    mask = ImageChops.offset(silhouette, dx, dy).filter(ImageFilter.GaussianBlur(float(shadow.get("blur", 0)) * px))
    mask = mask.crop((margin, margin, margin + image.width, margin + image.height)).point(lambda v: v * alpha // 255)
    layer = Image.new("RGBA", image.size, color[:3] + (0,))
    layer.putalpha(mask)
    return Image.alpha_composite(layer, image)


def finish(image, props: Mapping, supersample: int):
    """Scaled down, then its opacity and brightness."""
    from PIL import Image

    size = (image.width // supersample, image.height // supersample)
    image = image.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    brightness, opacity = float(props.get("brightness", 1)), float(props.get("opacity", 1))
    if brightness != 1 or opacity != 1:
        red, green, blue, alpha = image.split()
        red, green, blue = (band.point(lambda v: round(v * brightness)) for band in (red, green, blue))
        alpha = alpha.point(lambda v: round(v * opacity))
        image = Image.merge("RGBA", (red, green, blue, alpha))
    return image


# ==== Main ========================================================================================


def shrink_groups(sprites: list, renderer: SpriteRenderer) -> list:
    """Lines with ``overflow = "shrink_group"`` take the size the group's widest line at the same index shrinks
    to."""
    smallest: dict[tuple[str, int], dict] = {}
    original: dict[tuple[str, int], float] = {}
    for name, props, styles, group in sprites:
        if "cell" not in props:
            continue
        for i, line, line_styles in sprite_lines(merged(props, {"name": name}), styles):
            if line.get("overflow") != "shrink_group":
                continue
            key = (group, i)
            original.setdefault(key, size_value(line.get("size", {})))
            try:
                size_rule = renderer.shrunk_size(line, line_styles)
            except ValueError:
                continue
            if key not in smallest or size_value(size_rule) < size_value(smallest[key]):
                smallest[key] = size_rule
    result = []
    for name, props, styles, group in sprites:
        lines = list(props.get("lines", []))
        for i, line in enumerate(lines):
            if (group, i) in smallest and not line.get("skip"):
                lines[i] = merged(line, {"size": smallest[(group, i)], "overflow": "shrink"})
        result.append((name, merged(props, {"lines": lines}), styles, group))
    for (group, i), size_rule in smallest.items():
        if size_value(size_rule) < original[(group, i)]:
            line = f" line {i + 1}" if (group, 1) in original else ""
            print(f"  {group.format(sprite='*')}{line}: shrunk to {size_value(size_rule):.1f} px, so every sprite fits")
    return result


def render_all(folder: Path, config: Mapping) -> int:
    """Writes every sprite into ``folder``; returns how many."""
    try:
        import PIL  # noqa: F401
    except ImportError as error:
        raise SystemExit("Pillow is needed: uv sync --extra tools") from error
    folder.mkdir(parents=True, exist_ok=True)
    renderer = SpriteRenderer(Fonts())
    count = 0
    fontless: list[str] = []
    sprites = expand_groups(config)
    sprites = shrink_groups(sprites, renderer)
    # Sprites drawn alike (a display group in its fallback colour's look) are drawn once.
    drawn: dict[str, Image.Image] = {}
    for name, props, styles, _ in sprites:
        key = json.dumps([props, styles], sort_keys=True)
        props = merged(props, {"name": name})
        try:
            if key not in drawn:
                drawn[key] = renderer.render(props, styles)
            image = drawn[key]
        except ValueError as error:
            if str(error) == "no font":
                fontless.append(name)
                continue
            raise SystemExit(f"{name}: {error}") from error
        path = folder / default_source_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path)
        count += 1
    if fontless:
        print(f"No font (set font, or pass --font): {len(fontless)} sprites skipped, e.g. {fontless[0]}")
    return count


def main():
    parser = argparse.ArgumentParser(description="Draw sprites from text.")
    parser.add_argument("folder", type=Path, help="where the sprites go")
    parser.add_argument("--config", type=Path, help="a TOML config merged over the defaults")
    parser.add_argument("--font", type=Path, help="the font of every group that doesn't name its own")
    parser.add_argument("--scale", type=float, help="texture px per skin px, for every group")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.font is not None:
        config["font"] = str(args.font)
    if args.scale is not None:
        config["defaults"] = merged(config.get("defaults", {}), {"scale": args.scale})
        for group in config.get("sprite_groups", []):
            group.pop("scale", None)
    count = render_all(args.folder, config)
    print(f"{count} sprites written to {args.folder}")


if __name__ == "__main__":
    main()
