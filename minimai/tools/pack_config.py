"""Pack configs: an optional ``pack.toml`` in a pack's source folder (or zip file), read the same way by
every pack tool. A missing file, section or key keeps the tool's default. The format is in docs/packs.md."""

import tomllib
import zipfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from minimai.tools.schema import ItemJson, LocalizableText

CONFIG_NAME = "pack.toml"
# Where a config's ``base`` is looked for when the source doesn't have it.
DEFAULTS_DIR = Path(__file__).parent / "defaults"
RESOURCES_DIR = Path(__file__).parent.parent.parent / "resources"


class PackFiles:
    """The files of a pack's source, a folder or a zip file, by their path inside it (``/``-separated). A zip
    whose files all sit in one top folder (as zipping a folder makes) is read from inside that folder."""

    def __init__(self, source: Path, suffixes: Iterable[str] | None = None):
        self.source = source
        self.archive: zipfile.ZipFile | None = None
        if source.is_dir():
            pairs = [(path.relative_to(source).as_posix(),) * 2 for path in sorted(source.rglob("*")) if path.is_file()]
        elif zipfile.is_zipfile(source):
            self.archive = zipfile.ZipFile(source)
            names = sorted(
                entry.filename
                for entry in self.archive.infolist()
                if not entry.is_dir() and not entry.filename.startswith("__MACOSX/")
            )
            tops = {name.split("/", 1)[0] for name in names}
            prefix = f"{tops.pop()}/" if len(tops) == 1 and all("/" in name for name in names) else ""
            pairs = [(name[len(prefix) :], name) for name in names]
        else:
            raise SystemExit(f"{source} is neither a folder nor a zip file")
        keep = None if suffixes is None else {suffix.lower() for suffix in suffixes}
        # Path inside the source -> the path in the folder or the zip entry.
        self.entries = {
            inside: stored for inside, stored in pairs if keep is None or PurePosixPath(inside).suffix.lower() in keep
        }
        self.by_path = {path.lower(): path for path in self.entries}

    def lookup(self, path: str) -> str | None:
        """The file at ``path`` (case-insensitive), or None."""
        return self.by_path.get(path.replace("\\", "/").lower())

    def read(self, path: str) -> bytes:
        stored = self.entries[path]
        if self.archive is not None:
            return self.archive.read(stored)
        return (self.source / stored).read_bytes()


def read_source_file(source: Path, name: str) -> bytes | None:
    """A file from a source folder or zip file, by its path inside it (case-insensitive in a zip). None when it
    isn't there."""
    if source.is_dir():
        path = source / name
        return path.read_bytes() if path.is_file() else None
    if zipfile.is_zipfile(source):
        files = PackFiles(source)
        found = files.lookup(name)
        return None if found is None else files.read(found)
    return None


def load_config(source: Path) -> dict:
    """The source's ``pack.toml`` as a dict, over its ``base`` configs; empty when there is none."""
    data = read_source_file(source, CONFIG_NAME)
    if data is None:
        return {}
    return with_bases(parse_config(data, str(source / CONFIG_NAME)), source, (CONFIG_NAME,))


def parse_config(data: bytes, label: str) -> dict:
    try:
        return tomllib.loads(data.decode("utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise SystemExit(f"{label}: {error}") from error


def with_bases(config: dict, source: Path, chain: tuple[str, ...]) -> dict:
    """``config`` merged over its ``base``: a config file (or a list of them, each over the one before) looked
    for in the source, then in ``tools/defaults``. A base may have a base of its own."""
    bases = config.pop("base", None) or []
    result: dict = {}
    for base in [bases] if isinstance(bases, str) else bases:
        if not isinstance(base, str) or not base:
            raise SystemExit(f"{chain[-1]}: base must be a config file or a list of them, not {base!r}")
        if base in chain:
            raise SystemExit(f"Configs are each other's base in a loop: {' -> '.join((*chain, base))}")
        data = read_source_file(source, base)
        label = f"{source / base}"
        if data is None and (DEFAULTS_DIR / base).is_file():
            data, label = (DEFAULTS_DIR / base).read_bytes(), str(DEFAULTS_DIR / base)
        if data is None:
            raise SystemExit(f"{chain[-1]}: base {base} is neither in {source} nor in {DEFAULTS_DIR}")
        result = merged(result, with_bases(parse_config(data, label), source, (*chain, base)))
    return merged(result, config)


def merged(defaults: Mapping, overrides: Mapping) -> dict:
    """``defaults`` with ``overrides`` on top; nested tables merge key by key."""
    result = dict(defaults)
    for key, value in overrides.items():
        if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
            result[key] = merged(result[key], value)
        else:
            result[key] = value
    return result


def resolve(value, params: Mapping):
    """``"$name"`` -> the param, ``"-$name"`` -> the param negated (recursively in lists and tables)."""
    if isinstance(value, str) and value.startswith(("$", "-$")):
        negate = value.startswith("-")
        key = value.lstrip("-")[1:]
        if key not in params:
            raise ValueError(f"Unknown param {value}")
        return -params[key] if negate else params[key]
    if isinstance(value, list):
        return [resolve(part, params) for part in value]
    if isinstance(value, Mapping):
        return {key: resolve(part, params) for key, part in value.items()}
    return value


def parse_color(value) -> tuple[float, float, float]:
    """``"#rrggbb"``, or ``[r, g, b]`` in 0-255 (or 0-1 when no part is over 1), to 0-1 floats."""
    if isinstance(value, str):
        text = value.lstrip("#")
        if len(text) != 6:
            raise ValueError(f"Not a colour: {value!r}")
        return tuple(int(text[i : i + 2], 16) / 255 for i in (0, 2, 4))
    parts = tuple(float(part) for part in value)
    if len(parts) != 3:
        raise ValueError(f"Not a colour: {value!r}")
    if any(part > 1 for part in parts):
        parts = tuple(part / 255 for part in parts)
    return parts


def check_text(value, key: str) -> LocalizableText:
    """``value`` if it's a string or a {language: string} table."""
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping) and value and all(isinstance(k, str) and isinstance(v, str) for k, v in value.items()):
        return dict(value)
    raise SystemExit(f"[item] {key} must be a string or a table of strings by language, not {value!r}")


@dataclass
class ItemInfo:
    title: LocalizableText
    subtitle: LocalizableText = "Minimai"
    author: LocalizableText = "Unknown"
    description: LocalizableText = ""
    tags: list[LocalizableText] = field(default_factory=list)
    # The image's bytes, or None for a generated one.
    thumbnail: bytes | None = None


def get_item_info(name: str, source: Path, config: Mapping) -> ItemInfo:
    """The item's info: the config's ``[item]``, then the defaults (the title defaults to the pack's name)."""
    item = config.get("item", {})
    info = ItemInfo(title=check_text(item.get("title", name), "title"))
    for key in ("subtitle", "author", "description"):
        if key in item:
            setattr(info, key, check_text(item[key], key))
    info.tags = [check_text(tag, "tags") for tag in item.get("tags", [])]
    if "thumbnail" in item:
        info.thumbnail = read_source_file(source, item["thumbnail"])
        if info.thumbnail is None:
            print(f"Thumbnail {item['thumbnail']} not found; using a generated one")
    else:
        for candidate in ("thumbnail.png", "thumbnail.jpg", "thumbnail.jpeg"):
            info.thumbnail = read_source_file(source, candidate)
            if info.thumbnail is not None:
                break
    return info


def item_json(version: int, info: ItemInfo, name: str | None = None) -> ItemJson:
    """item.json with the texts as the config gives them: a string stays a string, a table stays a table."""
    item: ItemJson = {
        "version": version,
        "title": info.title,
        "subtitle": info.subtitle,
        "author": info.author,
        "tags": [{"title": tag} for tag in info.tags],
        "description": info.description,
    }
    if name is not None:
        item = {"name": name, **item}
    return item
