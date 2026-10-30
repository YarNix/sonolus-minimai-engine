import hashlib
import re
import struct
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Iterable

from sonolus.script.level import BpmChange, Level, LevelData
from sonolus.script.metadata import Tag
from sonolus.build.collection import Asset
from sonolus.script.archetype import PlayArchetype

from minimai.lib.game import button_shift, get_button_iterator, get_sensor_iterator
from minimai.lib.hold import HoldKind
from minimai.lib.game import Sensor
from minimai.lib.touch import TouchKind
from minimai.lib.touch_hold import TouchHoldKind
from minimai.lib.note import NoteKind, is_star
from minimai.lib.slide import SlideKind, SlideTrackKind
from minimai.lib.layout import SLIDE_TRACK_POINTS
from minimai.level_builder import LevelBuilder, SlideTrackArg
from minimai.simai import read_maidata
from minimai.play.initialization import Initialization
from minimai.play import note, touch

def _build_silent_wav(duration_seconds: float = 60.0, sample_rate: int = 8000) -> bytes:
    num_samples = int(duration_seconds * sample_rate)
    data_size = num_samples  # 1 channel, 8-bit
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        1,  # channels
        sample_rate,
        sample_rate,  # byte rate = sample_rate * channels * bits/8
        1,  # block align
        8,  # bits per sample
        b"data",
        data_size,
    )
    return header + b"\x80" * data_size

def build_level(
    name: str,
    title: str,
    bgm: Asset | None = None,
    *,
    level_entities: Iterable[PlayArchetype]
):
    initialization = Initialization()
    entities: list[PlayArchetype] = [ initialization, *level_entities ]

    # level_entities may be a generator: inspect the materialised list, not the consumed generator.
    if not any(isinstance(e, BpmChange) for e in entities):
        entities.insert(1, BpmChange(
            beat = 0,
            bpm = 120
        ))
    
    return Level(
        name=name, 
        title=title,
        bgm=bgm if bgm is not None else _build_silent_wav(),
        data=LevelData(
            bgm_offset=0.0,
            entities=entities,
        ),
    )

def test_notes():
    builder = LevelBuilder()
    builder.set_bpm(120, division=4)
    for note_arch in note.NOTE_ARCHETYPES:
        for _, button in get_button_iterator():
            if is_star(note_arch.key):
                builder.add_star(note_arch.key, button, rotation_speed=button if button != 8 else 0)
            else:
                builder.add_note(note_arch.key, button)
    return builder.get_level()


def test_spin():
    builder = LevelBuilder()
    builder.parse_line(
        "(88.8){48}"
        "1b,2,3,4,5,6,7,8,1,2,3,4,"
        "6b,7,8,1,2,3,4,5,6,7,8,1,"
        "3b,4,5,6,7,8,1,2,3,4,5,6,"
        "8b,1,2,3,4,5,6,7,8,1,2,3,"
        "5b,6,7,8,1,2,3,4,5,6,7,8,"
        "2b,3,4,5,6,7,8,1,2,3,4,5,,"
        "{8},3/5,4,4,,"
        "{48}"
        "8b/4,7,6,5,4,3,2,1,8,7,6,5,"
        "3b,2,1,8,7,6,5,4,3,2,1,8,"
        "6b,5,4,3,2,1,8,7,6,5,4,3,"
        "1b,8,7,6,5,4,3,2,1,8,7,6,"
        "4b,3,2,1,8,7,6,5,4,3,2,1,"
        "7b,6,5,4,3,2,1,8,7,6,5,4,,"
        "{8},6/4,5,5,,"
        "{48}"
        "1b/5bx,2,3,4,5,6,7,8,1,"
        "2x/7b,6,5,4,3,2,1,8,7,"
        "6x/3b,4,5,6,7,8,"
        "1x/5b,4,3,2,1,8,7,6,5,"
        "4x/1b,2,3,4,5,6,7,8,1,"
        "2x/6b,5,4,3,2,1,"
        "8x/4b,5,6,7,8,1,2,3,4,"
        "5x/8b,7,6,5,4,3,2,1,8,"
        "7x/3b,4,5,6,7,8,,"
    )
    return builder.get_level()


def test_hold():
    builder = LevelBuilder()
    builder.set_bpm(120, division=4)
    # At 120 BPM: 0.6 beat = 18 frames (no body check), 0.9 beat = 27 frames
    lengths = (0, 0.6, 0.9, 2)
    for kind in HoldKind:
        for _, button in get_button_iterator():
            builder.add_hold(kind, button, lengths[(button - 1) % len(lengths)])
        builder.advance(2)

    # BPM change inside a hold: 2 beats at 120, then 2 beats at 60 (3 s in total).
    builder.add_hold(HoldKind.NORM_HOLD, 1, 4)
    builder.advance(1)
    builder.set_bpm(60)
    builder.advance(3)
    builder.set_bpm(120)
    builder.advance(2)

    # A tap on the same lane during a hold must still be catchable.
    builder.add_hold(HoldKind.NORM_HOLD, 3, 4)
    builder.add_note(NoteKind.NORM_TAP, 3)
    builder.add_note(NoteKind.NORM_TAP, 3)
    builder.advance(4)

    # simai: each holds, EX / break holds, a zero-length hold and a seconds length.
    builder.parse_line(
        "1h[2:1]/5h[2:1],,,,"
        "3bh[4:3],,,,4xh[4:1],,6bxh[4:1],,8h,,"
        "2h[#1.5],,,,"
    )
    return builder.get_level()


def test_touch_hold():
    builder = LevelBuilder()
    builder.set_bpm(120, division=4)
    # At 120 BPM: 0.9 beat = 27 frames (no body check), then 1 and 2 beats.
    lengths = (0, 0.9, 1, 2)
    sensors = (Sensor.C, Sensor.B1, Sensor.E3, Sensor.A5, Sensor.D7)
    for kind in TouchHoldKind:
        for index, sensor in enumerate(sensors):
            builder.add_touch_hold(kind, sensor, lengths[index % len(lengths)])
            builder.advance(1)
        builder.advance(2)

    # A touch on the same sensor during a touch hold must still be catchable.
    builder.add_touch_hold(TouchHoldKind.NORM_TOUCH_HOLD, Sensor.C, 4)
    builder.add_touch(TouchKind.NORM_TOUCH, Sensor.C)
    builder.add_touch(TouchKind.NORM_TOUCH, Sensor.C)
    builder.advance(4)

    # simai: each touch holds, break, zero-length, firework flag, a seconds length.
    builder.parse_line(
        "Ch[2:1]/B5h[2:1],,,,"
        "E2bh[4:3],,,,Ch,,Chf[4:1],,"
        "D4h[#1.5],,,,"
    )

    for i in range(8):
        builder.add_touch_hold(TouchKind.EACH_TOUCH, Sensor.E1 + i, 5)
        builder.same_line()

    return builder.get_level()


def test_touch():
    builder = LevelBuilder()
    builder.set_bpm(120, division=4)
    for touch_arch in touch.TOUCH_ARCHETYPES:
        for _, sensor in get_sensor_iterator():
            builder.add_touch(touch_arch.key, sensor)
    return builder.get_level()


SLIDE_KIND_CYCLE = (SlideKind.NORMAL_SLIDE, SlideKind.EACH_SLIDE, SlideKind.BREAK_SLIDE)
SLIDE_TEST_TRACKS = [track for track in SlideTrackKind if track not in (
    SlideTrackKind.NONE, SlideTrackKind.FAN_L, SlideTrackKind.FAN_C, SlideTrackKind.FAN_R,
)]
SLIDE_TRACK_GROUPS = ("CIRCLE", "LINE", "CENTER", "LOOP_IN", "LOOP_OUT", "REFLECT", "ZIG_ZAG", "FAN")


def get_longest_track(group: str) -> SlideTrackKind:
    tracks = [track for track in SLIDE_TEST_TRACKS if track.name == group or track.name.startswith(group + "_")]
    return max(tracks, key=lambda track: len(SLIDE_TRACK_POINTS[track]))


def test_slide():
    builder = LevelBuilder()
    builder.set_bpm(160)
    group_tracks = [get_longest_track(group) for group in SLIDE_TRACK_GROUPS]

    # Headless, unmirrored and mirrored, per track group
    for index, track in enumerate(group_tracks):
        kind = SLIDE_KIND_CYCLE[index % 3]
        button = button_shift(1, index * 3)
        for mirrored in (False, True):
            builder.add_slide_headless(kind, track, mirrored, button, 2)
            builder.same_line()
            builder.advance(3)

    # With a star head, per track group
    for index, track in enumerate(group_tracks):
        builder.add_slide(SLIDE_KIND_CYCLE[index % 3], track, False, button_shift(1, index * 3), 2)
        builder.same_line()
        builder.advance(3)

    # No wait, no travel time
    builder.add_slide(SlideKind.NORMAL_SLIDE, SlideTrackKind.LINE_5, False, 1, 0, wait_time=0)
    builder.same_line()
    builder.advance(3)

    # Long wait and long travel ending together, plus a long Wi-Fi
    builder.add_slide(SlideKind.EACH_SLIDE, SlideTrackKind.LINE_5, False, 1, 2, wait_time=16)
    builder.same_line()
    builder.add_slide(SlideKind.EACH_SLIDE, SlideTrackKind.CIRCLE_1, False, 3, 16, wait_time=2)
    builder.same_line()
    builder.add_slide(SlideKind.EACH_WIFI_SLIDE, SlideTrackKind.FAN, False, 6, 16, wait_time=2)
    return builder.get_level()


def test_slide_tracks():
    """Every single-track variation, instant: no wait, no travel time, speed 100."""
    builder = LevelBuilder()
    builder.set_bpm(120)
    # Next slide only after the previous one's too-late time (end + 0.6 s).
    spacing = builder.seconds_to_beats(1)
    for kind in SLIDE_KIND_CYCLE:
        for track in SLIDE_TEST_TRACKS:
            for mirrored in (False, True):
                builder.add_slide_headless(kind, track, mirrored, 1, 0, wait_time=0, speed=100)
                builder.same_line()
                builder.advance(spacing)
    return builder.get_level()


def test_connected_slide():
    builder = LevelBuilder()
    builder.set_bpm(120, division=1)
    builder.advance(2)

    # 1-4>7
    builder.add_slides(
        SlideKind.NORMAL_SLIDE, 1,
        SlideTrackArg(SlideTrackKind.LINE_4), SlideTrackArg(SlideTrackKind.CIRCLE_4),
        total_slide_time=3,
    )
    builder.advance(2)
    # 1>2>3: 3 areas in total -> head [skip, no], tail [no, skip]
    builder.add_slides(
        SlideKind.BREAK_SLIDE, 1,
        SlideTrackArg(SlideTrackKind.CIRCLE_2), SlideTrackArg(SlideTrackKind.CIRCLE_2),
        total_slide_time=2,
    )
    builder.advance(2)
    # 1-3<1-5 with a mirrored middle
    builder.add_slides(
        SlideKind.EACH_SLIDE, 1,
        SlideTrackArg(SlideTrackKind.LINE_3), SlideTrackArg(SlideTrackKind.CIRCLE_3, True), SlideTrackArg(SlideTrackKind.LINE_5),
        total_slide_time=4,
    )
    builder.advance(4)
    # 1-5 then a Wi-Fi as the final slide
    builder.add_slides(
        SlideKind.NORMAL_SLIDE, 1,
        SlideTrackArg(SlideTrackKind.LINE_5), SlideTrackArg(SlideTrackKind.FAN),
        total_slide_time=3,
    )
    builder.advance(3)
    # Wi-Fi head: C -> 5-7, L -> 6>8 (longer path), R not continued
    builder.add_slides(
        SlideKind.NORMAL_SLIDE, 1,
        SlideTrackArg(SlideTrackKind.FAN, sub_tracks=(SlideTrackArg(SlideTrackKind.CIRCLE_3, slide_time=3.5), None)),
        SlideTrackArg(SlideTrackKind.LINE_3),
        total_slide_time=3,
    )
    builder.advance(2)
    # Through every sensor: 1>1 rides the A and D ring, 1p1 the B and E ring, 1-5 crosses C
    builder.add_slides(
        SlideKind.EACH_SLIDE, 1,
        SlideTrackArg(SlideTrackKind.CIRCLE_1), SlideTrackArg(SlideTrackKind.LOOP_IN_1), SlideTrackArg(SlideTrackKind.LINE_5),
        total_slide_time=12,
    )
    return builder.get_level()


def test_simai():
    builder = LevelBuilder()
    builder.parse_line(
        "(120){4}"
        "1,2b,3x,12,4/5h[4:1],1$,2$$,,"
        "1-5[4:1],,2b-6[4:1]b,,3x/7-3[8:3]*-1[8:3],,"
        "1-4q7-2[1:2],,,,,,,,"
        "1-4[2:1]q7[2:1]-2[1:1],,,,,,,,,"
        "1?-5[2:1],,,1@>4[4:1],,1V35[4:1],,1w5[4:2],,,"
        "1-5[160#8:3],,1-5[1##1],,"
        "C/B1/E8,A1,D3b,Cf,{#0.25}1`2`3,,,,"
        "{4}1w5-1[2:1]~^1,,,,1w5-1[2:1]~4^1~6^1,,,,1w5w1[4:1]~6^1[4:1],,,,1w5-1[2:1]~^1w5~~~-1,,,,"
        # Lengths are fixed times: 4 quarter notes at 120 = 2 s, across a drop to 60 and back.
        "(120)7h[4:4]/3-7[4:4],(60),,(120),,,,"
        "E"
    )
    return builder.get_level()


def test_each():
    builder = LevelBuilder()
    builder.parse_line(
        "(120){2},,"
        # Each lines: 1 to 4 buttons apart both ways round, a chain of three, same button (no line).
        "1/2,1/3,1/4,1/5,1/6,8/2,1/3/5,1/1,"
        # Tap + hold, hold + hold, star heads, break / EX members.
        "1/5h[4:1],,1h[4:1]/4h[4:1],,1-5[4:1]/3,,1b/3x,,"
        # Touch groups: B1 B2 C together, E1 alone, A3 with D4 and E4.
        "B1/B2/C/E5,,A3/D4/E4,,"
        # Touch hold body group: C B1 B2 held together, with a touch in the head group.
        "Ch[2:1]/B1h[2:1]/B2h[2:1]/B3,,,,"
        "E"
    )
    return builder.get_level()

def test_touch_overlap():
    builder = LevelBuilder()
    builder.parse_line(
        "(120){8},,,,,,,,"
        # C: up to four visible at once (the "2" border in each / break colour, then the "3").
        "C,C/E1,Cb,C,,,,,,,,,"
        # B1: two at once (tie broken by chart order), a touch hold doesn't count.
        "B1/B1,B1h[2:1],B1,,,,,,,,"
        "E"
    )
    return builder.get_level()

## Levels from simai chart folders in resources/levels (see: resources/levels/README.md)
LEVELS_DIR = Path(__file__).parent.parent / "resources" / "levels"
# Converted audio, kept between builds
AUDIO_CACHE_DIR = Path(__file__).parent.parent / "tmp" / "resource_levels"


def build_resource_levels(levels_dir: Path = LEVELS_DIR) -> Iterator[Level]:
    """One level per chart of every song folder in ``levels_dir`` (sorted by folder name).

    A folder that doesn't match the layout is skipped.
    Without imageio-ffmpeg, folders with an mp3/wav track are built without a preview and the others are skipped.
    """
    if not levels_dir.is_dir():
        return
    folders = sorted(path for path in levels_dir.iterdir() if path.is_dir())
    if not folders:
        return
    try:
        import imageio_ffmpeg  # noqa: F401
        has_ffmpeg = True
    except ImportError:
        has_ffmpeg = False
        print("imageio-ffmpeg isn't installed (uv sync --extra levels): "
              "chart levels get no preview, and only mp3 tracks are used.")
    for folder in folders:
        yield from build_song_levels(folder, has_ffmpeg=has_ffmpeg)


def build_song_levels(folder: Path, *, has_ffmpeg: bool = True) -> Iterator[Level]:
    """The levels of one song folder; named ``<folder>``, or ``<folder>-<N>`` when it has several charts."""
    # Helpers
    def get_float_or_None(maidata: dict[str, str], key: str) -> float | None:
        try:
            return float(maidata[key].strip())
        except (KeyError, ValueError):
            return None
    def parse_rating(text: str) -> float:
        # 13 -> 13
        # 13+ -> 13
        # 13.7 -> 13.7
        # 0 when there's no number
        m = re.match(r"\s*(\d+(?:\.\d+)?)(\+?)", text)
        if m is None:
            return 0
        rating = float(m.group(1))
        return int(rating) if rating.is_integer() else rating

    maidata_path = folder / "maidata.txt"
    track = resolve_file(folder, "track", (".mp3", ".ogg", ".wav"))
    if not maidata_path.is_file() or track is None:
        missing = [
            name for name, found in (("maidata.txt", maidata_path.is_file()), ("track.mp3/.ogg/.wav", track)) if not found
        ]
        print(f"Skipping chart folder {folder}: no {' or '.join(missing)}.")
        return
    no_conversion = track.suffix.lower() == ".mp3" or track.suffix.lower() == ".wav"
    if not no_conversion and not has_ffmpeg:
        print(f"Skipping chart folder {folder}: {track.name} needs imageio-ffmpeg.")
        return
    cover = resolve_file(folder, "bg", (".png", ".jpg", ".jpeg"))

    text = maidata_path.read_text(encoding="utf-8-sig")
    maidata = read_maidata(text)
    charts = sorted(
        (int(m.group(1)) for key, value in maidata.items() if (m := re.fullmatch(r"inote_(\d+)", key)) and value.strip()),
    )
    if not charts:
        print(f"Skipping chart folder {folder}: maidata.txt has no &inote_N chart.")
        return

    bgm = track if no_conversion else convert_audio(track, [])
    preview = None
    demo_seek = get_float_or_None(maidata, "demo_seek")
    if demo_seek is not None and has_ffmpeg:
        # 30 s from the demo point, fading out over the last 3 s.
        preview = convert_audio(track, ["-ss", f"{demo_seek}", "-t", "30", "-af", "afade=t=out:st=27:d=3"])
    tags = [Tag(maidata[key].strip()) for key in ("genre", "wholebpm") if maidata.get(key, "").strip()]

    for chart in charts:
        builder = LevelBuilder()
        try:
            builder.parse_maidata(text, chart)
            entities = [Initialization(), *builder.get_level()]
        except Exception as error:
            raise ValueError(f"{maidata_path}: &inote_{chart}: {error}") from error
        # The chart starts &first seconds into the track.
        first = get_float_or_None(maidata, f"first_{chart}")
        if first is None:
            first = get_float_or_None(maidata, "first") or 0.0
        yield Level(
            name=folder.name if len(charts) == 1 else f"{folder.name}-{chart}",
            title=maidata.get("title", "").strip() or folder.name,
            artists=maidata.get("artist", "").strip() or "Unknown",
            author=maidata.get(f"des_{chart}", "").strip() or maidata.get("des", "").strip() or "Unknown",
            rating=parse_rating(maidata.get(f"lv_{chart}", "")),
            cover=cover,
            bgm=bgm,
            preview=preview,
            data=LevelData(bgm_offset=first, entities=entities),
            description=maidata.get("des", "").strip() or None,
            tags=tags,
        )

def resolve_file(folder: Path, stem: str, suffixes: tuple[str, ...]) -> Path | None:
    for suffix in suffixes:
        for path in (folder / f"{stem}{suffix}", folder / f"{stem}{suffix.upper()}"):
            if path.is_file():
                return path
    return None

def convert_audio(source: Path, args: list[str]) -> Path:
    """``source`` through ffmpeg ``args`` to mp3. The result is kept in ``AUDIO_CACHE_DIR`` and reused
    while the source file (path, size, modified time) and ``args`` stay the same."""
    stat = source.stat()
    key_text = "\0".join([str(source.resolve()), str(stat.st_size), str(stat.st_mtime_ns), *args])
    key = hashlib.sha256(key_text.encode()).hexdigest()[:16]
    output = AUDIO_CACHE_DIR / f"{source.parent.name}-{key}.mp3"
    if not output.is_file():
        import imageio_ffmpeg

        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(".part.mp3")
        subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(source), *args,
             "-vn", "-codec:a", "libmp3lame", "-q:a", "2", str(temporary)],
            check=True,
        )
        temporary.replace(output)
    return output


levels = [
    build_level("test-notes", "Test Notes", level_entities=test_notes()),
    build_level("test-spin", "Test Spin", level_entities=test_spin()),
    build_level("test-hold", "Test Hold", level_entities=test_hold()),
    build_level("test-touch", "Test Touch", level_entities=test_touch()),
    build_level("test-touch-hold", "Test Touch Hold", level_entities=test_touch_hold()),
    build_level("test-slide", "Test Slide", level_entities=test_slide()),
    build_level("test-slide-tracks", "Test Slide Tracks", level_entities=test_slide_tracks()),
    build_level("test-connected-slide", "Test Connected Slide", level_entities=test_connected_slide()),
    build_level("test-simai", "Test Simai", level_entities=test_simai()),
    build_level("test-each", "Test Each", level_entities=test_each()),
    build_level("test-touch-overlap", "Test Touch Overlap", level_entities=test_touch_overlap()),
    *build_resource_levels(),
]
