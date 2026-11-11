import argparse
import zipfile
from pathlib import Path

AUDIO_SUFFIXES = {".wav", ".mp3", ".ogg", ".flac"}
THUMBNAIL_SUFFIXES = {".png", ".jpg", ".jpeg"}
RISER_STEM = "touch_hold_riser"
# Amplitude factors (0.5 is half, -6 dB) for clips louder than the rest: the guide and the slides.
CLIP_GAINS = {
    "answer": 0.75,
    "slide": 0.5,
    "slide_break_start": 0.5,
    "slide_break_slide": 0.5,
}
# Clips mixed into one (after the gains), so fewer sounds play at once. The sources are kept as clips
# of their own too: scheduled sounds play them apart.
CLIP_MIXES = {
    "break_critical_hit": ("break_tap", "break"),
    "slide_break_end_critical": ("slide_break_slide", "break"),
}


def read_source(source: Path) -> tuple[dict[str, bytes], bytes | None]:
    """Audio files by stem, and the thumbnail if there is one, from a folder or a zip file (any depth)."""
    clips: dict[str, bytes] = {}
    thumbnail = None

    def add(path: Path, read):
        nonlocal thumbnail
        suffix = path.suffix.lower()
        if suffix in AUDIO_SUFFIXES:
            clips[path.stem] = read()
        elif suffix in THUMBNAIL_SUFFIXES and path.stem.lower() == "thumbnail":
            thumbnail = read()

    if source.is_dir():
        for path in sorted(source.rglob("*")):
            if path.is_file():
                add(path, path.read_bytes)
    elif zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            for entry in archive.infolist():
                if not entry.is_dir():
                    add(Path(entry.filename), lambda: archive.read(entry))
    else:
        raise SystemExit(f"{source} is neither a folder nor a zip file")
    return clips, thumbnail


def build_effect(name: str, source: Path, *, author: str, description: str, thumbnail: Path | None):
    from minimai.effect_packer import CLIP_NAMES, pack_effect
    from minimai.tools.clip_gain import scale_wav
    from minimai.tools.clip_mix import mix_wavs
    from minimai.tools.riser_cut import cut_riser

    clips, found_thumbnail = read_source(source)
    riser = next((stem for stem in clips if stem.lower() == RISER_STEM), None)
    if riser is not None:
        try:
            clips["touch_hold_start"], clips["touch_hold_sustain"] = cut_riser(clips[riser])
        except Exception as error:
            print(f"Skipping the riser ({riser}): {error}")
        del clips[riser]
    for stem in clips:
        gain = CLIP_GAINS.get(stem.lower())
        if gain is not None:
            try:
                clips[stem] = scale_wav(clips[stem], gain)
            except Exception as error:
                print(f"Not changing the volume of {stem}: {error}")
    stems = {stem.lower(): stem for stem in clips}
    mixed_sources = set()
    for target, sources in CLIP_MIXES.items():
        if not all(source in stems for source in sources):
            print(f"Skipping {target}: needs {', '.join(sources)}")
            continue
        try:
            clips[target] = mix_wavs(*(clips[stems[source]] for source in sources))
            mixed_sources.update(sources)
        except Exception as error:
            print(f"Skipping {target}: {error}")
    for source in mixed_sources - set(CLIP_NAMES):
        del clips[stems[source]]
    folder = pack_effect(
        name,
        clips,
        author=author,
        description=description,
        thumbnail=thumbnail if thumbnail is not None else found_thumbnail,
    )
    print(f"Effect pack written to {folder}")


def main():
    parser = argparse.ArgumentParser(description="Minimai tools")
    commands = parser.add_subparsers(dest="command", required=True)
    effect = commands.add_parser("effect", help="build an effect pack from a zip file or folder of clips")
    effect.add_argument("name", help="the pack's folder name in resources/effects")
    effect.add_argument("source", type=Path, help="zip file or folder with the clips")
    effect.add_argument("--author", default="Unknown")
    effect.add_argument("--desc", default="", help="the pack's description")
    effect.add_argument("--thumbnail", type=Path, help="image file; overrides a thumbnail in the source")
    args = parser.parse_args()

    if args.command == "effect":
        build_effect(args.name, args.source, author=args.author, description=args.desc, thumbnail=args.thumbnail)


if __name__ == "__main__":
    main()
