import struct
from typing import Iterable
from dataclasses import dataclass, field

from sonolus.script.level import BpmChange, Level, LevelData
from sonolus.build.collection import Asset
from sonolus.script.archetype import PlayArchetype

from minimai.lib.game import SENSOR_COUNT, Button, get_button_iterator
from minimai.lib.note import is_star
from minimai.lib.slide import SlideKind, SlideTrackKind
from minimai.lib.layout import SLIDE_TRACK_POINTS
from minimai.lib.game import get_sensor_iterator
from minimai.play.initialization import Initialization
from minimai.play import note, touch, slide

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
    for a, note_arch in enumerate(note.NOTE_ARCHETYPES):
        for i, b in get_button_iterator():
            yield note_arch(
                beat = a * 8 + i,
                button = b,
                speed = 1,
                import_rotate_speed = b if is_star(note_arch.key) and b != 8 else 0,
                has_custom_rotation = True,
            )

@dataclass
class LevelBuilderContext:
    curr_beat: float = field(default=0)

    def make_note(self, type: type[note.BaseNote], button: Button):
        return type(
            beat = self.curr_beat,
            button = button,
            speed = 1,
            import_rotate_speed = 0,
            has_custom_rotation = False,
        )

    def inc_beat(self, division: float):
        self.curr_beat = self.curr_beat + 4 / division

    def parse_note(self, data: str, division: float):
        for line in data.split(','):
            if len(line) == 0:
                self.inc_beat(division)
                continue
            notes = line.split('/')
            has_each = len(notes) > 1
            for data in notes:
                button = int(data[0])
                if 'b' in data:
                    if 'x' in data:
                        yield self.make_note(note.ExBreakTapNote, button)
                    else:
                        yield self.make_note(note.BreakTapNote, button)
                elif has_each:
                    if 'x' in data:
                        yield self.make_note(note.ExEachTapNote, button)
                    else:
                        yield self.make_note(note.EachTapNote, button)
                else:
                    if 'x' in data:
                        yield self.make_note(note.ExTapNote, button)
                    else:
                        yield self.make_note(note.NormalTapNote, button)
                if not has_each:
                    self.inc_beat(division)
            if has_each:
                self.inc_beat(division)

def test_spin():
    builder = LevelBuilderContext()
        
    yield BpmChange(
        beat = 0,
        bpm = 88.8
    )

    yield from builder.parse_note(
        '1b,2,3,4,5,6,7,8,1,2,3,4,' \
        '6b,7,8,1,2,3,4,5,6,7,8,1,' \
        '3b,4,5,6,7,8,1,2,3,4,5,6,' \
        '8b,1,2,3,4,5,6,7,8,1,2,3,' \
        '5b,6,7,8,1,2,3,4,5,6,7,8,' \
        '2b,3,4,5,6,7,8,1,2,3,4,5,',
        division=48
    )
    yield from builder.parse_note(",3/5,4,4,", division=8)

    yield from builder.parse_note(
        '8b/4,7,6,5,4,3,2,1,8,7,6,5,' \
        '3b,2,1,8,7,6,5,4,3,2,1,8,' \
        '6b,5,4,3,2,1,8,7,6,5,4,3,'
        '1b,8,7,6,5,4,3,2,1,8,7,6,' \
        '4b,3,2,1,8,7,6,5,4,3,2,1,' \
        '7b,6,5,4,3,2,1,8,7,6,5,4,',
        division=48
    )
    yield from builder.parse_note(",6/4,5,5,", division=8)
    yield from builder.parse_note(
        '1b/5bx,2,3,4,5,6,7,8,1,' \
        '2x/7b,6,5,4,3,2,1,8,7,' \
        '6x/3b,4,5,6,7,8,' \
        '1x/5b,4,3,2,1,8,7,6,5,' \
        '4x/1b,2,3,4,5,6,7,8,1,' \
        '2x/6b,5,4,3,2,1,' \
        '8x/4b,5,6,7,8,1,2,3,4,' \
        '5x/8b,7,6,5,4,3,2,1,8,' \
        '7x/3b,4,5,6,7,8,',
        division=48
    )

def test_touch():
    for t, touch_arch in enumerate(touch.TOUCH_ARCHETYPES):
        for i, sensor in get_sensor_iterator():
            yield touch_arch(
                beat = t * SENSOR_COUNT + i,
                sensor = sensor,
                speed = 1
            )

SLIDE_ARCHETYPE_BY_KIND = {arch.key: arch for arch in slide.SLIDE_ARCHETYPES if arch.is_scored}

def test_slide():
    yield BpmChange(
        beat = 0,
        bpm = 160
    )

    testing_params = [(SlideKind(i % 3 + 1), SlideTrackKind.CIRCLE_4, i * 2 + 1) for i in range(4)] \
        + [(SlideKind.NORMAL_SLIDE, SlideTrackKind.LINE_3 + i, 1 + (i * 3 % 8)) for i in range(3)] \
        + [(SlideKind.EACH_SLIDE, SlideTrackKind.CENTER_2, i * 4 + 1) for i in range(2)] \
        + [(SlideKind.BREAK_SLIDE, SlideTrackKind.CENTER_4, i * 4 + 1) for i in range(2)] \
        + [(SlideKind.NORMAL_SLIDE, SlideTrackKind.LOOP_IN_1 + i, 1) for i in range(8)] \
        + [(SlideKind.EACH_SLIDE, SlideTrackKind.LOOP_OUT_1 + i, 1 + (i % 8)) for i in range(8)] \
        + [(SlideKind.BREAK_SLIDE, SlideTrackKind.REFLECT_2 + i, 4 + i) for i in range(4)] \
        + [(SlideKind.NORMAL_SLIDE, SlideTrackKind.ZIG_ZAG, 1 + i) for i in range(8)] \
    
    for s, (kind, track, button) in enumerate(testing_params):
        yield SLIDE_ARCHETYPE_BY_KIND[kind](
            beat=s * 4,
            track=track,
            start_button=button,
            is_mirrored=False,
            wait_duration=1,
            slide_duration=1,
            speed=1
        )
        yield SLIDE_ARCHETYPE_BY_KIND[kind](
            beat=s * 4 + 2,
            track=track,
            start_button=button,
            is_mirrored=True,
            wait_duration=1,
            slide_duration=1,
            speed=1
        )

    wifi_test_params = [
        (wifi_kind, SlideTrackKind.FAN, button) 
        for wifi_kind in (SlideKind.WIFI_SLIDE, SlideKind.EACH_WIFI_SLIDE, SlideKind.BREAK_WIFI_SLIDE)
        for button in (1, 4, 7)
    ]
    next_beat = len(testing_params) * 4
    for s, (kind, track, button) in enumerate(wifi_test_params):
        s = s * 5 + next_beat
        yield SLIDE_ARCHETYPE_BY_KIND[kind](
            beat=s,
            track=track,
            start_button=button,
            is_mirrored=False,
            wait_duration=1,
            slide_duration=4,
            speed=1
        )


def _segment_beats(tracks: list[SlideTrackKind], total: float) -> list[float]:
    """Split a chain's total duration by bar count."""
    bars = [11 if t == SlideTrackKind.FAN else len(SLIDE_TRACK_POINTS[t]) for t in tracks]
    return [total * b / sum(bars) for b in bars]


def _link(parent, child, attr: str = "next_slide_ref"):
    setattr(parent, attr, child.ref())
    child.prev_slide_ref = parent.ref()


def _slide_kwargs(beat: float, track: SlideTrackKind, button: int, mirrored: bool, duration: float, wait: float = 1):
    return dict(
        beat=beat,
        track=track,
        start_button=button,
        is_mirrored=mirrored,
        wait_duration=wait,
        slide_duration=duration,
        speed=1,
    )


def _star(beat: float, button: int):
    return note.NormalStarNote(beat=beat, button=button, speed=1, import_rotate_speed=0, has_custom_rotation=False)


def test_connected_slide():
    yield BpmChange(beat=0, bpm=120)
    beat = 2

    # 1-4>7 : LINE_4 (1 -> 4) then CIRCLE_4 (4 -> 7), normal colour
    tracks = [SlideTrackKind.LINE_4, SlideTrackKind.CIRCLE_4]
    d = _segment_beats(tracks, 3)
    star = _star(beat, 1)
    head = slide.ConnSlide(**_slide_kwargs(beat, tracks[0], 1, False, d[0]), head_note_ref=star.ref())
    tail = slide.NormalSlideNote(**_slide_kwargs(beat, tracks[1], 4, False, d[1]))
    _link(head, tail)
    yield from (star, head, tail)
    beat += 6

    # 1>2>3 : two CIRCLE_2, 3 areas in total -> head [skip, no], tail [no, skip]; break colour
    tracks = [SlideTrackKind.CIRCLE_2, SlideTrackKind.CIRCLE_2]
    d = _segment_beats(tracks, 2)
    star = _star(beat, 1)
    head = slide.ConnSlide(**_slide_kwargs(beat, tracks[0], 1, False, d[0]), head_note_ref=star.ref())
    tail = slide.BreakSlideNote(**_slide_kwargs(beat, tracks[1], 2, False, d[1]))
    _link(head, tail)
    yield from (star, head, tail)
    beat += 6

    # 3 segments, mirrored middle: 1-3, 3<1 (mirrored CIRCLE_3), 1-5 ; each colour
    tracks = [SlideTrackKind.LINE_3, SlideTrackKind.CIRCLE_3, SlideTrackKind.LINE_5]
    d = _segment_beats(tracks, 4)
    star = _star(beat, 1)
    head = slide.ConnSlide(**_slide_kwargs(beat, tracks[0], 1, False, d[0]), head_note_ref=star.ref())
    middle = slide.ConnSlide(**_slide_kwargs(beat, tracks[1], 3, True, d[1]))
    tail = slide.EachSlideNote(**_slide_kwargs(beat, tracks[2], 1, False, d[2]))
    _link(head, middle)
    _link(middle, tail)
    yield from (star, head, middle, tail)
    beat += 8

    # 1-5 then Wi-Fi from 5 as the final slide
    tracks = [SlideTrackKind.LINE_5, SlideTrackKind.FAN]
    d = _segment_beats(tracks, 3)
    star = _star(beat, 1)
    head = slide.ConnSlide(**_slide_kwargs(beat, tracks[0], 1, False, d[0]), head_note_ref=star.ref())
    tail = slide.NormalWifiSlideNote(**_slide_kwargs(beat, tracks[1], 5, False, d[1]))
    _link(head, tail)
    yield from (star, head, tail)
    beat += 7

    # Wi-Fi from 1 as chain head: C (ends 5) -> 5-7, L (ends 6) -> 6>8, R (ends 4) not continued
    wifi_d = 2
    star = _star(beat, 1)
    wifi = slide.ConnWifiSlide(**_slide_kwargs(beat, SlideTrackKind.FAN, 1, False, wifi_d), head_note_ref=star.ref())
    tail_c = slide.NormalSlideNote(**_slide_kwargs(beat, SlideTrackKind.LINE_3, 5, False, 1))
    tail_l = slide.NormalSlideNote(**_slide_kwargs(beat, SlideTrackKind.CIRCLE_3, 6, False, 1.5))
    _link(wifi, tail_c, "next_slide_ref")
    _link(wifi, tail_l, "next_slide_l_ref")
    yield from (star, wifi, tail_c, tail_l)


levels = [
    build_level("test-notes", "Test Notes", level_entities=test_notes()),
    build_level("test-spin", "Test Spin", level_entities=test_spin()),
    build_level("test-touch", "Test Touch", level_entities=test_touch()),
    build_level("test-slide", "Test Slide", level_entities=test_slide()),
    build_level("test-connected-slide", "Test Connected Slide", level_entities=test_connected_slide()),
]