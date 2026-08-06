from __future__ import annotations

from sonolus.script.archetype import (
    AnyArchetype,
    EntityRef,
    PlayArchetype,
    StandardImport,
    entity_data,
    entity_memory,
    exported,
    imported,
    shared_memory,
)

from minimai.lib.slide import SlideKind
from minimai.play import note

class BaseSlide(PlayArchetype):
    beat: StandardImport.BEAT
    wait_time: float = imported(name="waitTime")
    slide_time: float = imported(name="slideTime")
    head_note_ref: EntityRef[note.BaseNote] = imported(name="headNote")