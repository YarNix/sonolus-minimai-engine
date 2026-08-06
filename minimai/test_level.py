import struct
from typing import Iterable

from sonolus.script.level import BpmChange, Level, LevelData
from sonolus.build.collection import Asset
from sonolus.script.archetype import PlayArchetype

from minimai.lib.note import is_star
from minimai.lib.layout import get_button_iterator
from minimai.play.initialization import Initialization
from minimai.play.note import NOTE_ARCHETYPES

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
    for a, note_arch in enumerate(NOTE_ARCHETYPES):
        for i, b in get_button_iterator():
            yield note_arch(
                beat = a * 8 + i,
                button = b,
                speed = 1,
                rotate_speed = b if is_star(note_arch.key) and b != 8 else 0
            )

levels = [build_level("test-notes", "Test Notes", level_entities=test_notes())]