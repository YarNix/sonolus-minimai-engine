import struct
from typing import Iterable

from sonolus.script.level import BpmChange, Level, LevelData
from sonolus.build.collection import Asset
from sonolus.script.archetype import PlayArchetype

from minimai.lib.game import get_button_iterator, get_sensor_iterator
from minimai.lib.hold import HoldKind
from minimai.lib.note import NoteKind, is_star
from minimai.lib.slide import SlideKind, SlideTrackKind
from minimai.lib.layout import SLIDE_TRACK_POINTS
from minimai.level_builder import LevelBuilder, SlideTrackArg
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
        button = index * 3 % 8 + 1
        for mirrored in (False, True):
            builder.add_slide_headless(kind, track, mirrored, button, 2)
            builder.same_line()
            builder.advance(3)

    # With a star head, per track group
    for index, track in enumerate(group_tracks):
        builder.add_slide(SLIDE_KIND_CYCLE[index % 3], track, False, index * 3 % 8 + 1, 2)
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


levels = [
    build_level("test-notes", "Test Notes", level_entities=test_notes()),
    build_level("test-spin", "Test Spin", level_entities=test_spin()),
    build_level("test-hold", "Test Hold", level_entities=test_hold()),
    build_level("test-touch", "Test Touch", level_entities=test_touch()),
    build_level("test-slide", "Test Slide", level_entities=test_slide()),
    build_level("test-slide-tracks", "Test Slide Tracks", level_entities=test_slide_tracks()),
    build_level("test-connected-slide", "Test Connected Slide", level_entities=test_connected_slide()),
    build_level("test-simai", "Test Simai", level_entities=test_simai()),
]
