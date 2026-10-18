import struct
from typing import Iterable
from dataclasses import dataclass, field

from sonolus.script.level import BpmChange, Level, LevelData
from sonolus.build.collection import Asset
from sonolus.script.archetype import PlayArchetype

from minimai.lib.game import SENSOR_COUNT, Button, get_button_iterator
from minimai.lib.note import is_star
from minimai.lib.slide import SlideKind, SlideTrackKind
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

    if not any(isinstance(e, BpmChange) for e in level_entities):
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
                rotate_speed = b if is_star(note_arch.key) and b != 8 else 0
            )

@dataclass
class LevelBuilderContext:
    curr_beat: float = field(default=0)

    def make_note(self, type: type[note.BaseNote], button: Button):
        return type(
            beat = self.curr_beat,
            button = button,
            speed = 1,
            rotate_speed = 0,
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
        yield slide.SLIDE_ARCHETYPES[int(kind) - 1](
            beat=s * 4,
            track=track,
            start_button=button,
            is_mirrored=False,
            wait_duration=1,
            slide_duration=1,
            speed=1
        )
        yield slide.SLIDE_ARCHETYPES[int(kind) - 1](
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
        yield slide.SLIDE_ARCHETYPES[int(kind) - 1](
            beat=s,
            track=track,
            start_button=button,
            is_mirrored=False,
            wait_duration=1,
            slide_duration=4,
            speed=1
        )


levels = [
    build_level("test-notes", "Test Notes", level_entities=test_notes()),
    build_level("test-spin", "Test Spin", level_entities=test_spin()),
    build_level("test-touch", "Test Touch", level_entities=test_touch()),
    build_level("test-slide", "Test Slide", level_entities=test_slide()),
]