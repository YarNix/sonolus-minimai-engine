"""Build a Minimai effect pack in ``resources/effects/<name>`` from a folder or zip file of clips.

Usage: python -m minimai.tools.effect_pack <name> <source> (or ``python main.py effect ...``).

Every clip has a recipe: its sources and the edits that make the clip. The defaults are in
``tools/defaults/effect.toml``; the source's ``pack.toml`` is merged over them. The format is in
docs/packs.md.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import struct
import tomllib
import zipfile
import zlib
from collections.abc import Mapping
from pathlib import Path, PurePosixPath

from minimai.lib.effect import TOUCH_HOLD_CHARGE_DURATION, Effects
from minimai.tools import audio
from minimai.tools.pack_config import (
    RESOURCES_DIR,
    PackFiles,
    get_item_info,
    item_json,
    load_config,
    merged,
    resolve,
    resolved_params,
)
from minimai.tools.schema import ClipRecipe, ClipSource, EffectConfig

EFFECTS_DIR = RESOURCES_DIR / "effects"
DEFAULTS_PATH = Path(__file__).parent / "defaults" / "effect.toml"
AUDIO_SUFFIXES = {".wav", ".mp3", ".ogg", ".flac"}
ENGINE_CLIPS = set(Effects._effects_)
RECIPE_KEYS = set(ClipRecipe.__annotations__)
SOURCE_KEYS = set(ClipSource.__annotations__)
# Clip keys that edit it; a clip with none of them and one plain source isn't decoded.
CLIP_EDITS = RECIPE_KEYS - {"sources", "format", "skip"}
# A mix of several sources, when neither the clip nor the pack sets a format.
MIX_FORMAT = "mp3"


def load_defaults() -> EffectConfig:
    with DEFAULTS_PATH.open("rb") as file:
        defaults = tomllib.load(file)
    unknown = sorted(set(defaults["clips"]) - ENGINE_CLIPS)
    if unknown:
        raise SystemExit(f"{DEFAULTS_PATH.name} has clips the engine doesn't play: {unknown}")
    if defaults["params"]["riser_loop_start"] != TOUCH_HOLD_CHARGE_DURATION:
        raise SystemExit(f"{DEFAULTS_PATH.name}: riser_loop_start differs from TOUCH_HOLD_CHARGE_DURATION")
    return defaults


def get_audio_suffix(data: bytes) -> str:
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return ".wav"
    if data[:4] == b"OggS":
        return ".ogg"
    if data[:4] == b"fLaC":
        return ".flac"
    if data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0):
        return ".mp3"
    raise ValueError("Unknown audio format")


def build_thumbnail(size: int = 64) -> bytes:
    """A plain dark square PNG."""
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))

    row = b"\x00" + bytes((0x20, 0x20, 0x28)) * size
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(row * size))
        + chunk(b"IEND", b"")
    )


class SourceFiles(PackFiles):
    """The audio files of the source (any depth), found by path or by stem (case-insensitive)."""

    def __init__(self, source: Path, files: Mapping[str, str]):
        super().__init__(source, AUDIO_SUFFIXES)
        self.files = {key.replace("\\", "/").lower(): value for key, value in files.items()}
        self.by_stem: dict[str, str] = {}
        for path in self.entries:
            self.by_stem.setdefault(PurePosixPath(path).stem.lower(), path)
        self.used: set[str] = set()

    def find(self, path: str | list[str]) -> str | None:
        """The file a recipe ``path`` names: a path with an audio suffix, or a file stem."""
        for candidate in [path] if isinstance(path, str) else path:
            key = candidate.replace("\\", "/").lower()
            key = self.files.get(key, candidate).replace("\\", "/").lower()
            found = self.by_path.get(key) if PurePosixPath(key).suffix in AUDIO_SUFFIXES else self.by_stem.get(key)
            if found is not None:
                self.used.add(found)
                return found
        return None

    def exact(self, name: str) -> str | None:
        """A file whose stem is exactly a clip's name."""
        for path in self.entries:
            if PurePosixPath(path).stem == name:
                return path
        return None


def source_list(sources) -> list[ClipSource]:
    """A recipe's ``sources`` as tables: a path is short for one source, and in a list each path is short
    for ``{ path = ... }``."""
    if isinstance(sources, str):
        sources = [sources]
    return [{"path": source} if isinstance(source, str) else dict(source) for source in sources]


def check_recipe(name: str, recipe: Mapping):
    """Warns about keys the packer doesn't know, so an old or misspelt config doesn't go unnoticed."""
    unknown = [key for key in recipe if key not in RECIPE_KEYS]
    for i, source in enumerate(source_list(recipe.get("sources", []))):
        unknown += [f"sources[{i}].{key}" for key in source if key not in SOURCE_KEYS]
    if unknown:
        print(f"{name}: unknown keys (ignored): {', '.join(unknown)}")


def recipe_for(name: str, files: SourceFiles, defaults: EffectConfig, config: EffectConfig) -> ClipRecipe:
    """The default recipe, or an exact-name file as it is, with the source's pack.toml entry on top."""
    exact = files.exact(name)
    recipe = {"sources": exact} if exact is not None else defaults["clips"].get(name, {})
    return merged(recipe, config.get("clips", {}).get(name, {}))


def is_plain(recipe: ClipRecipe, sources: list[ClipSource]) -> bool:
    return len(sources) == 1 and set(sources[0]) == {"path"} and not CLIP_EDITS & set(recipe)


def build_source(source: ClipSource, data: bytes, label: str) -> audio.Audio:
    """One source, decoded and edited up to its speed change (which needs the clip's rate)."""
    clip = audio.decode(data, label)
    # On the whole file, before the trim, so a loop's crossfade joins filtered audio and stays seamless.
    clip = audio.filtered(
        clip, highpass=source.get("highpass"), lowpass=source.get("lowpass"), slope=int(source.get("slope", 12))
    )
    if "trim" in source:
        start, length = source["trim"]
        if "loop" in source:
            clip = audio.loop_trim(clip, start, length, source["loop"])
        else:
            clip = audio.trim(clip, start, length)
    elif "loop" in source:
        raise ValueError("loop needs a trim")
    if source.get("reverse"):
        clip = audio.reverse(clip)
    return clip


def output_format(value) -> str:
    """A ``format`` value: one of the encoders' formats, or "" (null or "" alike) for none."""
    if value is None or value == "":
        return ""
    if not isinstance(value, str) or value.lower() not in audio.ENCODERS:
        raise ValueError(f"format must be one of {', '.join(audio.ENCODERS)} or \"\", not {value!r}")
    return value.lower()


def build_clip(name: str, recipe: ClipRecipe, files: SourceFiles, pack_format: str) -> tuple[bytes, str] | None:
    """The clip's file (bytes, suffix), or None when a source file is missing. Its format is the clip's,
    else the pack's, else the source's for a single source and ``MIX_FORMAT`` for a mix."""
    sources = source_list(recipe.get("sources", []))
    if not sources:
        raise ValueError("no sources")
    found = [files.find(source["path"]) for source in sources]
    paths = [path for path in found if path is not None]
    if len(paths) < len(found):
        return None
    source_format = get_audio_suffix(files.read(paths[0]))[1:] if len(paths) == 1 else ""
    target = output_format(recipe.get("format")) or pack_format or source_format or MIX_FORMAT
    if is_plain(recipe, sources):
        data = files.read(paths[0])
        if target != source_format:
            data = audio.convert(data, target, f"Converting {paths[0]} to {target}")
        return data, f".{target}"

    clips = [build_source(source, files.read(path), path) for source, path in zip(sources, paths)]
    rate = int(recipe.get("rate", max(clip.rate for clip in clips)))
    count = int(recipe.get("channels", max(min(len(clip.channels), 2) for clip in clips)))
    parts = []
    for source, clip in zip(sources, clips):
        clip = audio.resample(clip, rate, float(source.get("speed", 1.0)))
        if "fade" in source:
            fade_in, fade_out = source["fade"]
            clip = audio.fade(clip, fade_in, fade_out, source.get("curve", "linear"))
        clip = audio.gain(clip, float(source.get("gain", 1.0)))
        clip = audio.to_channels(clip, count, float(source.get("pan", 0.0)))
        parts.append((clip, float(source.get("at", 0.0))))
    result = audio.mix(parts, recipe.get("duration"))

    silence = recipe.get("trim_silence", False)
    if silence is not False:
        result = audio.trim_silence(result, -60.0 if silence is True else float(silence))
    if "fade" in recipe:
        fade_in, fade_out = recipe["fade"]
        result = audio.fade(result, fade_in, fade_out, recipe.get("curve", "linear"))
    result = audio.gain(result, float(recipe.get("gain", 1.0)))
    if "normalize" in recipe:
        result = audio.normalize(result, float(recipe["normalize"]))
    clipped = audio.clipped(result)
    if clipped:
        print(f"{name}: {clipped} samples past full scale were clipped; lower its gain or normalize it")
    return audio.encode(result, target), f".{target}"


def file_name(clip: str) -> str:
    """A clip's file name in audio.zip: ``Mai Break Critical Hit`` -> ``mai_break_critical_hit``."""
    return re.sub(r"[^a-z0-9]+", "_", clip.lower()).strip("_")


def pack_effect(name: str, source: Path, *, effects_dir: Path = EFFECTS_DIR) -> Path:
    """Build the pack from ``source`` (folder or zip) and return its folder."""
    defaults = load_defaults()
    source_config: EffectConfig = load_config(source)
    config: EffectConfig = merged(defaults, source_config)
    config["params"] = resolved_params(config.get("params", {}))
    info = get_item_info(name, source, config)
    unknown = sorted(set(source_config.get("clips", {})) - ENGINE_CLIPS)
    if unknown:
        print(f"Clips the engine doesn't play (ignored): {', '.join(unknown)}")
    if config["params"]["riser_loop_start"] != TOUCH_HOLD_CHARGE_DURATION:
        print(f"riser_loop_start isn't {TOUCH_HOLD_CHARGE_DURATION}, when the engine swaps to the sustain")
    try:
        pack_format = output_format(config.get("format"))
    except ValueError as error:
        raise SystemExit(f"pack.toml: {error}") from error
    files = SourceFiles(source, config["files"])

    # Clip name -> its file in audio.zip; clips with the same data share one file.
    entries: dict[str, str] = {}
    audio_files: dict[str, bytes] = {}
    by_data: dict[bytes, str] = {}
    built_recipes: dict[str, tuple[bytes, str] | None] = {}
    missing = []
    names = [*defaults["clips"], *sorted(ENGINE_CLIPS - set(defaults["clips"]))]
    for clip in names:
        recipe = recipe_for(clip, files, defaults, source_config)
        if not recipe or recipe.get("skip"):
            continue
        check_recipe(clip, recipe)
        recipe = resolve(recipe, config["params"])
        # The same recipe (another clip's fallback) is built once.
        key = json.dumps(recipe, sort_keys=True)
        try:
            if key not in built_recipes:
                built_recipes[key] = build_clip(clip, recipe, files, pack_format)
            built = built_recipes[key]
        except Exception as error:
            print(f"{clip}: {error}")
            built = None
        if built is None:
            missing.append(clip)
            continue
        data, suffix = built
        if data not in by_data:
            by_data[data] = f"{file_name(clip)}{suffix}"
            audio_files[by_data[data]] = data
        entries[clip] = by_data[data]
    if missing:
        print(f"Missing clips (the engine falls back or stays silent): {', '.join(missing)}")
    unused = sorted(set(files.entries) - files.used)
    if unused:
        print(f"Files no clip uses: {', '.join(unused)}")
    if not entries:
        raise SystemExit("No Minimai clips to pack")

    folder = effects_dir / name
    folder.mkdir(parents=True, exist_ok=True)
    item = item_json(5, info)
    (folder / "item.json").write_text(json.dumps(item, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    data = {"clips": [{"name": clip, "filename": filename} for clip, filename in entries.items()]}
    (folder / "data.json").write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, clip_data in audio_files.items():
            archive.writestr(filename, clip_data)
    (folder / "audio.zip").write_bytes(output.getvalue())
    (folder / "thumbnail.png").write_bytes(info.thumbnail or build_thumbnail())
    shared = f" ({len(entries) - len(audio_files)} sharing another's file)" if len(audio_files) < len(entries) else ""
    print(f"{len(entries)} clips{shared}")
    return folder


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("name", help="the pack's folder name in resources/effects")
    parser.add_argument("source", type=Path, help="zip file or folder with the clips (and pack.toml)")


def main():
    parser = argparse.ArgumentParser(description="Build a Minimai effect pack from clips.")
    add_arguments(parser)
    args = parser.parse_args()
    print(f"Effect pack written to {pack_effect(args.name, args.source)}")


if __name__ == "__main__":
    main()
