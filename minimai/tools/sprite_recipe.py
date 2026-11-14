"""Sprite recipes, the same for the skin and particle packs: a source file (or none) and the steps that turn it
into a sprite's image. The format is in docs/packs.md (the skin's ``[sprites]``).

Pillow is an optional extra (``uv sync --extra tools``): build_sprite imports it when it runs.
"""

from __future__ import annotations

import io
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, cast

from minimai.tools.imaging import (
    apply_levels,
    apply_operations,
    apply_tint,
    cross_section,
    fit_to_canvas,
    premultiplied_resize,
)
from minimai.tools.pack_config import PackFiles, merged
from minimai.tools.schema import CanvasStage, ImageRecipe, SourceStage

if TYPE_CHECKING:
    from PIL import Image

# The keys every recipe has; a pack adds its own (the skin's transform, a particle sprite's fallback).
IMAGE_RECIPE_KEYS = frozenset(ImageRecipe.__annotations__)
STAGE_KEYS = {"source": set(SourceStage.__annotations__), "canvas": set(CanvasStage.__annotations__)}


class SourceFiles(PackFiles):
    """The PNGs of the source (any depth), found by path (case-insensitive), through ``[files]``."""

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


def source_stage(source) -> dict:
    """A recipe's ``source``; a plain path (or list of paths) is short for ``{ path = ... }``."""
    if source is None:
        return {}
    if isinstance(source, (str, list)):
        return {"path": source}
    return dict(source)


def recipe_table(entry) -> dict:
    """A recipe; a plain path (or list of paths) is short for ``{ source = ... }``."""
    if entry is None:
        return {}
    if isinstance(entry, (str, list)):
        return {"source": entry}
    return dict(entry)


def combined_recipe(default, exact: str | None, entry, kept: Iterable[str]) -> dict:
    """The default recipe, or an exact-name file as it is (keeping the default's ``kept`` keys), with the
    source's pack.toml entry on top. The entry's ``source`` replaces the whole default ``source`` (its crop and
    paint belong to the default file); the other tables merge key by key."""
    default = recipe_table(default)
    if exact is not None:
        recipe = {"source": {"path": exact}}
        for key in kept:
            if key in default:
                recipe[key] = default[key]
    else:
        recipe = default
    entry = recipe_table(entry)
    if "source" in entry:
        recipe["source"] = source_stage(entry.pop("source"))
    else:
        recipe["source"] = source_stage(recipe.get("source"))
    return merged(recipe, entry)


def check_recipe(name: str, recipe: Mapping, keys: Iterable[str] = IMAGE_RECIPE_KEYS):
    """Warns about keys the packer doesn't know, so an old or misspelt config doesn't go unnoticed."""
    keys = set(keys)
    unknown = [key for key in recipe if key not in keys]
    for stage, stage_keys in STAGE_KEYS.items():
        if isinstance(recipe.get(stage), Mapping):
            unknown += [f"{stage}.{key}" for key in recipe[stage] if key not in stage_keys]
    if unknown:
        print(f"{name}: unknown keys (ignored): {', '.join(unknown)}")


def build_sprite(name: str, recipe: ImageRecipe, files: SourceFiles) -> Image.Image | None:
    """The sprite's image, or None when its source file is missing."""
    from PIL import Image

    # combined_recipe has made it a table.
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


def report_missing(missing: Mapping[str, ImageRecipe]):
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
