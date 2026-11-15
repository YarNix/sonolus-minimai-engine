"""What the build and the drawing tools leave behind, and removing it (``python main.py clean``).

- Caches: the chart folders' converted audio (``tmp/resource_levels``) and the backgrounds made from them
  (``resources/backgrounds/level-<folder>``). The next build makes them again.
- Drawn sprites: the files art and font_render wrote into a folder, listed in its ``.drawn.json``. Only the
  listed files go, so a skin source's own sprites stay.
"""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Iterable, Iterator
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
# The chart folders' converted audio, kept between builds.
AUDIO_CACHE_DIR = PROJECT_DIR / "tmp" / "resource_levels"
# Backgrounds made from the chart folders, as resource items the levels name; remade on every build.
BACKGROUNDS_DIR = PROJECT_DIR / "resources" / "backgrounds"
BACKGROUND_PREFIX = "level-"
BACKGROUND_SUBTITLE = "Made from a chart folder"
# The list of drawn sprites in a folder: {tool: [paths inside the folder]}.
DRAWN_MANIFEST = ".drawn.json"
# Folders not searched for drawn sprites.
SKIPPED_DIRS = {".git", ".venv", "venv", "node_modules", "build", "dist", "tmp", "__pycache__"}


def is_level_background(folder: Path) -> bool:
    """Whether a background item folder was made from a chart folder (so it can be removed)."""
    if not folder.name.startswith(BACKGROUND_PREFIX):
        return False
    try:
        item = json.loads((folder / "item.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return isinstance(item, dict) and item.get("subtitle") == {"en": BACKGROUND_SUBTITLE}


def read_drawn(folder: Path) -> dict[str, list[str]]:
    try:
        data = json.loads((folder / DRAWN_MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {
        tool: [path for path in paths if isinstance(path, str)]
        for tool, paths in data.items()
        if isinstance(paths, list)
    }


def record_drawn(folder: Path, tool: str, paths: Iterable[Path]):
    """Adds the files ``tool`` wrote into ``folder`` to its manifest. Earlier runs' files stay listed, so a sprite
    a config no longer draws is still cleaned."""
    drawn = read_drawn(folder)
    listed = set(drawn.get(tool, []))
    listed.update(path.relative_to(folder).as_posix() for path in paths)
    drawn[tool] = sorted(listed)
    (folder / DRAWN_MANIFEST).write_text(json.dumps(drawn, indent=4) + "\n", encoding="utf-8")


def find_drawn(roots: Iterable[Path]) -> Iterator[Path]:
    """The folders under ``roots`` with a drawn sprite manifest."""
    for root in roots:
        if (root / DRAWN_MANIFEST).is_file():
            yield root
        for current, dirs, files in os.walk(root):
            dirs[:] = sorted(name for name in dirs if name not in SKIPPED_DIRS and not name.startswith("."))
            for name in dirs:
                folder = Path(current) / name
                if (folder / DRAWN_MANIFEST).is_file():
                    yield folder


def remove_file(path: Path, dry_run: bool) -> bool:
    if not path.is_file():
        return False
    if not dry_run:
        path.unlink()
    return True


def remove_tree(path: Path, dry_run: bool) -> bool:
    if not path.is_dir():
        return False
    if not dry_run:
        shutil.rmtree(path)
    return True


def clean_drawn(folder: Path, dry_run: bool = False) -> int:
    """Removes the sprites listed in ``folder``'s manifest, the folders they leave empty, and the manifest;
    returns how many files went."""
    count = 0
    parents: set[Path] = set()
    root = folder.resolve()
    for paths in read_drawn(folder).values():
        for path in paths:
            target = (folder / path).resolve()
            # A manifest only reaches inside its own folder.
            if root not in target.parents:
                continue
            if remove_file(target, dry_run):
                count += 1
                parents.update(parent for parent in target.parents if root in parent.parents)
    if not dry_run:
        for parent in sorted(parents, key=lambda path: len(path.parts), reverse=True):
            if parent.is_dir() and not any(parent.iterdir()):
                parent.rmdir()
    remove_file(folder / DRAWN_MANIFEST, dry_run)
    return count


def clean_caches(dry_run: bool = False) -> list[Path]:
    """Removes the converted audio and the chart folders' backgrounds; returns what went."""
    removed = [AUDIO_CACHE_DIR] if remove_tree(AUDIO_CACHE_DIR, dry_run) else []
    if BACKGROUNDS_DIR.is_dir():
        for folder in sorted(BACKGROUNDS_DIR.iterdir()):
            if folder.is_dir() and is_level_background(folder) and remove_tree(folder, dry_run):
                removed.append(folder)
    return removed


def clean(folders: list[Path], *, caches: bool = True, drawn: bool = True, dry_run: bool = False):
    """``main.py clean``: the caches, and the drawn sprites in ``folders`` (default: anywhere in the project)."""
    verb = "Would remove" if dry_run else "Removed"
    if caches:
        removed = clean_caches(dry_run)
        for path in removed:
            print(f"{verb} {display(path)}")
        if not removed:
            print("No caches")
    if drawn:
        found = list(find_drawn(folders or [PROJECT_DIR]))
        for folder in found:
            count = clean_drawn(folder, dry_run)
            print(f"{verb} {count} drawn sprite{'s' if count != 1 else ''} from {display(folder)}")
        if not found:
            print("No drawn sprites")


def display(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_DIR).as_posix()
    except ValueError:
        return str(path)
