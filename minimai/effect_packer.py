"""Build a Minimai effect pack in ``resources/effects/<name>`` from clips

Clips are packed as given: no conversion.
"""

import io
import json
import struct
import zipfile
import zlib
from collections.abc import Mapping
from pathlib import Path

from minimai.lib.effect import Effects

EFFECTS_DIR = Path(__file__).parent.parent / "resources" / "effects"

# Clip file stem (lowercase) to the clip name the engine plays.
CLIP_NAMES: dict[str, str] = {
    "tap_perfect": "#PERFECT",
    "tap_great": "#GREAT",
    "tap_good": "#GOOD",
    "tap_ex": "#PERFECT_ALTERNATIVE",
    "break_tap": "Mai Break Hit",
    "break": "Mai Break Critical",
    # break_tap and break mixed.
    "break_critical_hit": "Mai Break Critical Hit",
    "touch": "Mai Touch Hit",
    "touch_hanabi": "Mai Firework",
    # Cut from touch_hold_riser.
    "touch_hold_start": "Mai Touch Hold Start",
    "touch_hold_sustain": "Mai Touch Hold Sustain",
    "slide": "Mai Slide",
    "slide_break_start": "Mai Break Slide",
    "slide_break_slide": "Mai Break Slide End",
    # slide_break_slide and break mixed.
    "slide_break_end_critical": "Mai Break Slide End Critical",
    "answer": "Mai Guide",
    "answer_clock": "Mai Count In",
}

assert set(CLIP_NAMES.values()) <= set(Effects._effects_), "CLIP_NAMES names a clip the engine doesn't play"


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


def pack_effect(
    name: str,
    clips: Mapping[str, Path | bytes],
    *,
    title: str | None = None,
    author: str = "Unknown",
    description: str = "",
    thumbnail: Path | bytes | None = None,
    effects_dir: Path = EFFECTS_DIR,
) -> Path:
    """Write the pack and return its folder. ``clips`` maps a clip file stem (any case) to the file
    or its bytes; stems not in ``CLIP_NAMES`` are skipped with a message, missing ones are listed."""
    entries: list[tuple[str, str, bytes]] = []
    for stem, source in clips.items():
        key = stem.lower()
        if key not in CLIP_NAMES:
            print(f"Skipping {stem}: not a Minimai clip.")
            continue
        data = source.read_bytes() if isinstance(source, Path) else source
        entries.append((CLIP_NAMES[key], f"{key}{get_audio_suffix(data)}", data))
    missing = sorted(set(CLIP_NAMES) - {stem.lower() for stem in clips})
    if missing:
        print(f"Missing clips (the engine falls back or stays silent): {', '.join(missing)}")
    if not entries:
        raise ValueError("No Minimai clips to pack")
    order = list(CLIP_NAMES.values())
    entries.sort(key=lambda entry: order.index(entry[0]))

    folder = effects_dir / name
    folder.mkdir(parents=True, exist_ok=True)
    item = {
        "version": 5,
        "title": {"en": title or name},
        "subtitle": {"en": "Minimai"},
        "author": {"en": author},
        "tags": [],
        "description": {"en": description},
    }
    (folder / "item.json").write_text(json.dumps(item, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    data = {"clips": [{"name": clip_name, "filename": filename} for clip_name, filename, _ in entries]}
    (folder / "data.json").write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")

    audio = io.BytesIO()
    with zipfile.ZipFile(audio, "w", zipfile.ZIP_DEFLATED) as archive:
        for _, filename, clip in entries:
            archive.writestr(filename, clip)
    (folder / "audio.zip").write_bytes(audio.getvalue())

    if isinstance(thumbnail, Path):
        thumbnail = thumbnail.read_bytes()
    (folder / "thumbnail.png").write_bytes(thumbnail or build_thumbnail())
    return folder
