"""Build a Minimai skin pack in ``resources/skins/<name>`` from a skin folder or zip file.

Usage: python -m minimai.tools.skin_pack <name> <source> (or ``python main.py skin ...``).
Needs Pillow (``uv sync --extra tools``).

Every sprite has a recipe: a source file in the folder and the steps that turn it into the sprite. The
defaults are in ``tools/defaults/skin.toml``; the source's ``pack.toml`` is merged over them. The format,
the lookup order and the steps are in docs/packs.md.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import tomllib
from collections.abc import Mapping
from functools import cache
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, cast

from minimai.lib.layout import (
    EACH_LINE_SIZE,
    FAST_LATE_SIZE,
    HOLD_END_POINT_SIZE,
    HOLD_WIDTH,
    JUDGE_TEXT_SIZE,
    LINE_SIZE,
    NOTE_SIZE,
    RING_SPRITE_SIZE,
    SKIN_RING_RADIUS_PX,
    SLIDE_OK_SIZES,
    SLIDE_PATH_SIZE,
    TOUCH_FAN_SIZE,
    TOUCH_HOLD_BORDER_SIZE,
    TOUCH_JUST_BORDER_SIZE,
    TOUCH_OVERLAP_BORDER_SIZE,
    TOUCH_POINT_SIZE,
    WIFI_SLIDE_PATH_SIZES,
)
from minimai.lib.skin import COUNTER_ACHIEVEMENTS, COUNTER_GRADES, BaseSkin
from minimai.tools.imaging import (
    apply_levels,
    apply_operations,
    apply_tint,
    build_sheet,
    fit_to_canvas,
    premultiplied_resize,
)
from minimai.tools.pack_config import (
    RESOURCES_DIR,
    PackFiles,
    get_item_info,
    item_json,
    load_config,
    merged,
    resolve,
)
from minimai.tools.schema import CanvasStage, SkinConfig, SkinData, SourceStage, SpriteRecipe, Transform

# Pillow is an optional extra (uv sync --extra tools): the image functions import it when they run.
if TYPE_CHECKING:
    from PIL import Image

SKINS_DIR = RESOURCES_DIR / "skins"
DEFAULTS_PATH = Path(__file__).parent / "defaults" / "skin.toml"
# Sprites the skin packs though the engine doesn't draw them yet: the counter's header words.
EXTRA_SPRITES = (
    "Mai Counter Header Combo",
    *(f"Mai Counter Header Combo {grade}" for grade in COUNTER_GRADES),
    *(f"Mai Counter Header Achievement {achievement}" for achievement in COUNTER_ACHIEVEMENTS),
)
SPRITE_NAMES: list[str] = [*BaseSkin._sprites_, *EXTRA_SPRITES]


def px(value) -> list[int]:
    """A layout size (ring units, a number or a Vec2) in skin px."""
    if isinstance(value, (int, float)):
        size = round(value * SKIN_RING_RADIUS_PX)
        return [size, size]
    return [round(value.x * SKIN_RING_RADIUS_PX), round(value.y * SKIN_RING_RADIUS_PX)]


# The defaults' cell params, as lib/layout.py has them.
LAYOUT_CELLS = {
    "note_cell": px(NOTE_SIZE),
    "ring_cell": [round(RING_SPRITE_SIZE * SKIN_RING_RADIUS_PX)] * 2,
    "line_cell": px(LINE_SIZE),
    "each_ring_line_cell": px(EACH_LINE_SIZE),
    "touch_point_cell": px(TOUCH_POINT_SIZE),
    "touch_fan_cell": px(TOUCH_FAN_SIZE),
    "touch_overlap_border_cell": px(TOUCH_OVERLAP_BORDER_SIZE),
    "touch_just_border_cell": px(TOUCH_JUST_BORDER_SIZE),
    "slide_path_cell": px(SLIDE_PATH_SIZE),
    **{f"wifi_slide_path_{i + 1}_cell": px(size) for i, size in enumerate(WIFI_SLIDE_PATH_SIZES)},
    "hold_cell": [px(HOLD_WIDTH)[0], 0],
    "hold_end_point_cell": px(HOLD_END_POINT_SIZE),
    "touch_hold_border_cell": px(TOUCH_HOLD_BORDER_SIZE),
    "judge_text_cell": px(JUDGE_TEXT_SIZE),
    "fast_late_cell": px(FAST_LATE_SIZE),
    "slide_ok_curve_cell": px(SLIDE_OK_SIZES[0]),
    "slide_ok_straight_cell": px(SLIDE_OK_SIZES[1]),
    "slide_ok_wifi_cell": px(SLIDE_OK_SIZES[2]),
}


@cache
def default_recipes() -> Mapping[str, SpriteRecipe]:
    with DEFAULTS_PATH.open("rb") as file:
        return tomllib.load(file)["sprites"]


def default_source_path(name: str) -> str:
    """Where a skin source keeps a sprite, as its default recipe reads it (``CounterSkins/...``), so the tools that
    draw sprites write them where the skin finds them. A sprite with no default recipe is ``<name>.png``."""
    path = default_recipes().get(name, {}).get("source")
    if isinstance(path, Mapping):
        path = path.get("path")
    if isinstance(path, list):
        path = path[0] if path else None
    return path if isinstance(path, str) and path else f"{name}.png"


def load_defaults() -> SkinConfig:
    with DEFAULTS_PATH.open("rb") as file:
        defaults = tomllib.load(file)
    names = set(defaults["sprites"])
    if names != set(SPRITE_NAMES):
        raise SystemExit(
            f"{DEFAULTS_PATH.name} is out of step with BaseSkin (and EXTRA_SPRITES): "
            f"missing {sorted(set(SPRITE_NAMES) - names)}, unknown {sorted(names - set(SPRITE_NAMES))}"
        )
    stale = {key: value for key, value in LAYOUT_CELLS.items() if defaults["params"].get(key) != value}
    if stale:
        raise SystemExit(f"{DEFAULTS_PATH.name}: cells differ from lib/layout.py: {stale}")
    return defaults


CORNERS = [f"{axis}{i}" for i in range(1, 5) for axis in "xy"]


def sparse_transform(transform: Transform | None) -> Transform:
    """A transform with only its non-zero weights (Sonolus reads a missing weight as 0), every corner
    listed; identity when there is none."""
    if not transform:
        return {corner: {corner: 1} for corner in CORNERS}
    return {
        row: {column: weight for column in CORNERS if (weight := transform.get(row, {}).get(column, 0))}
        for row in CORNERS
    }


# ==== Touch hold border bars ======================================================================


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


# ==== Recipes =====================================================================================


def source_stage(source) -> dict:
    """A recipe's ``source``; a plain path (or list of paths) is short for ``{ path = ... }``."""
    if source is None:
        return {}
    if isinstance(source, (str, list)):
        return {"path": source}
    return dict(source)


RECIPE_KEYS = set(SpriteRecipe.__annotations__)
STAGE_KEYS = {"source": set(SourceStage.__annotations__), "canvas": set(CanvasStage.__annotations__)}


def check_recipe(name: str, recipe: Mapping):
    """Warns about keys the packer doesn't know, so an old or misspelt config doesn't go unnoticed."""
    unknown = [key for key in recipe if key not in RECIPE_KEYS]
    for stage, keys in STAGE_KEYS.items():
        if isinstance(recipe.get(stage), Mapping):
            unknown += [f"{stage}.{key}" for key in recipe[stage] if key not in keys]
    if unknown:
        print(f"{name}: unknown keys (ignored): {', '.join(unknown)}")


class SourceFiles(PackFiles):
    """The PNGs of the source (any depth), found by path (case-insensitive)."""

    def __init__(self, source: Path, files: Mapping[str, str]):
        super().__init__(source, {".png"})
        self.files = {key.replace("\\", "/").lower(): value for key, value in files.items()}
        self.by_stem: dict[str, str] = {}
        for path in self.entries:
            self.by_stem.setdefault(PurePosixPath(path).stem, path)

    def find(self, source) -> str | None:
        for candidate in [source] if isinstance(source, str) else source:
            key = candidate.replace("\\", "/").lower()
            found = self.lookup(self.files.get(key, candidate))
            if found is not None:
                return found
        return None

    def exact(self, name: str) -> str | None:
        """A PNG named exactly after a sprite."""
        return self.by_stem.get(name)


def recipe_for(name: str, files: SourceFiles, defaults: SkinConfig, config: SkinConfig) -> SpriteRecipe:
    """The default recipe, or an exact-name file as it is, with the source's pack.toml entry on top. The
    entry's ``source`` replaces the whole default ``source`` (its crop and paint belong to the default file);
    the other tables merge key by key."""
    default = defaults["sprites"][name]
    exact = files.exact(name)
    if exact is not None:
        recipe = {"source": {"path": exact}}
        for key in ("transform", "skip"):
            if key in default:
                recipe[key] = default[key]
    else:
        recipe = dict(default)
    entry = dict(config.get("sprites", {}).get(name, {}))
    if "source" in entry:
        recipe["source"] = source_stage(entry.pop("source"))
    else:
        recipe["source"] = source_stage(recipe.get("source"))
    return merged(recipe, entry)


def build_sprite(name: str, recipe: SpriteRecipe, files: SourceFiles) -> Image.Image | None:
    """The sprite's image, or None when its source file is missing."""
    from PIL import Image

    # recipe_for has made it a table.
    source = cast(SourceStage, recipe["source"])
    canvas = recipe.get("canvas", {})
    size = [int(part) for part in canvas.get("size", [0, 0])]
    if "path" in source:
        path = files.find(source["path"])
        if path is None:
            return None
        image = apply_operations(Image.open(io.BytesIO(files.read(path))).convert("RGBA"), source, expand=True)
        image = fit_to_canvas(image, size, bool(canvas.get("stretch", False)), name)
    else:
        if set(source) & {"crop", "paint", "flip", "rotate"}:
            raise ValueError("source operations need a source path")
        if not all(size):
            raise ValueError("without a source path, the canvas needs a size")
        # Transparent white, so filtering at painted edges doesn't darken them.
        image = Image.new("RGBA", (size[0], size[1]), (255, 255, 255, 0))
    image = apply_operations(image, canvas, expand=False)
    if "cross_section" in recipe:
        image = cross_section(image, **recipe["cross_section"])
    if "tint" in recipe:
        image = apply_tint(image, recipe["tint"])
    if "levels" in recipe:
        image = apply_levels(image, recipe["levels"].get("multiply", 1.0), recipe["levels"].get("add", 0.0))
    scale = float(recipe.get("scale", 1.0))
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    if size != image.size:
        image = premultiplied_resize(image, size)
    return image


# ==== Pack ========================================================================================


def report_missing(missing: Mapping[str, SpriteRecipe]):
    """The sprites left out, grouped by their source folder."""
    if not missing:
        return
    groups: dict[str, list[str]] = {}
    for name, recipe in missing.items():
        path = cast(SourceStage, recipe["source"]).get("path", "")
        source = path if isinstance(path, str) else path[0]
        groups.setdefault(source.rpartition("/")[0] or "(top folder)", []).append(name)
    print(f"Missing sprites ({len(missing)}), by source folder:")
    for folder, names in groups.items():
        listed = ", ".join(names) if len(names) <= 6 else f"{', '.join(names[:3])}, ... ({len(names)})"
        print(f"  {folder}: {listed}")


def build_thumbnail(images: Mapping[str, Image.Image]) -> Image.Image:
    from PIL import Image

    thumbnail = Image.new("RGBA", (128, 128), (32, 32, 40, 255))
    for name in ("Mai Normal Note", "Mai Normal Star", "Mai Ring"):
        if name in images:
            preview = images[name].copy()
            preview.thumbnail((120, 120))
            thumbnail.alpha_composite(preview, ((128 - preview.width) // 2, (128 - preview.height) // 2))
            break
    return thumbnail


def pack_skin(name: str, source: Path, *, skins_dir: Path = SKINS_DIR) -> Path:
    """Build the pack from ``source`` (folder or zip) and return its folder."""
    try:
        from PIL import Image
    except ImportError as error:
        raise SystemExit("Pillow is needed: uv sync --extra tools") from error

    defaults = load_defaults()
    source_config: SkinConfig = load_config(source)
    config: SkinConfig = merged(defaults, source_config)
    info = get_item_info(name, source, config)
    unknown = sorted(set(source_config.get("sprites", {})) - set(SPRITE_NAMES))
    if unknown:
        print(f"Not Minimai sprites (ignored): {', '.join(unknown)}")
    params = config["params"]
    files = SourceFiles(source, config["files"])

    images: dict[str, Image.Image] = {}
    transforms: dict[str, Transform] = {}
    missing: dict[str, SpriteRecipe] = {}
    for sprite in SPRITE_NAMES:
        recipe = recipe_for(sprite, files, defaults, source_config)
        if recipe.get("skip"):
            continue
        check_recipe(sprite, recipe)
        recipe = resolve(recipe, params)
        try:
            image = build_sprite(sprite, recipe, files)
        except Exception as error:
            print(f"{sprite}: {error}")
            image = None
        if image is None:
            missing[sprite] = recipe
            continue
        images[sprite] = image
        transforms[sprite] = sparse_transform(recipe.get("transform"))
    report_missing(missing)
    if not images:
        raise SystemExit(f"No sprites in {source}")

    texture = config["texture"]
    # Sprites with the same pixels share one place on the texture.
    slots: dict[str, int] = {}
    unique: dict[tuple, int] = {}
    pictures: list[Image.Image] = []
    for sprite, image in images.items():
        key = (image.size, image.tobytes())
        if key not in unique:
            unique[key] = len(pictures)
            pictures.append(image)
        slots[sprite] = unique[key]
    try:
        sheet, origins = build_sheet(pictures, int(texture["padding"]), int(texture["max_size"]))
    except ValueError as error:
        raise SystemExit(f"{error.args[0].capitalize()}; raise [texture] max_size or scale them down") from error
    data: SkinData = {
        "width": sheet.width,
        "height": sheet.height,
        "interpolation": bool(texture["interpolation"]),
        "sprites": [
            {
                "name": sprite,
                "x": origins[slots[sprite]][0],
                "y": origins[slots[sprite]][1],
                "w": image.width,
                "h": image.height,
                "transform": transforms[sprite],
            }
            for sprite, image in images.items()
        ],
    }

    target = skins_dir / name
    target.mkdir(parents=True, exist_ok=True)
    item = item_json(4, info, name)
    (target / "item.json").write_text(json.dumps(item, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    (target / "data.json").write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
    sheet.save(target / "texture.png")
    if info.thumbnail is not None:
        output = io.BytesIO()
        Image.open(io.BytesIO(info.thumbnail)).convert("RGBA").save(output, "PNG")
        (target / "thumbnail.png").write_bytes(output.getvalue())
    else:
        build_thumbnail(images).save(target / "thumbnail.png")
    shared = f" ({len(images) - len(pictures)} sharing another's pixels)" if len(pictures) < len(images) else ""
    print(f"{len(images)} of {len(SPRITE_NAMES)} sprites{shared} on a {sheet.width} px texture")
    return target


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("name", help="the pack's folder name in resources/skins")
    parser.add_argument("source", type=Path, help="the skin folder or zip file (and its pack.toml)")


def main():
    parser = argparse.ArgumentParser(description="Build a Minimai skin pack from a skin folder or zip file.")
    add_arguments(parser)
    args = parser.parse_args()
    print(f"Skin pack written to {pack_skin(args.name, args.source)}")


if __name__ == "__main__":
    main()
