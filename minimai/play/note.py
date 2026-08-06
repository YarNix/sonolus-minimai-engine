from __future__ import annotations
from typing import assert_never, cast
from math import pi

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
from sonolus.script.globals import level_memory
from sonolus.script.interval import unlerp, Interval, clamp
from sonolus.script.array import Dim
from sonolus.script.containers import VarArray
from sonolus.script.runtime import Touch, delta_time, input_offset, offset_adjusted_time, time, touches
from sonolus.script.timing import beat_to_time
from sonolus.script.bucket import Bucket, Judgment
from sonolus.script.debug import notify, debug_log

from minimai.play.slide import BaseSlide
from minimai.lib.note import (
    NoteKind,
    get_tap_appear_time,
    get_note_bucket,
    draw_note,
    is_ex,
    get_note_angle
)
from minimai.lib.layout import Hitboxes
from minimai.lib import archetype_names, buckets

class BaseNote(PlayArchetype):
    beat: StandardImport.BEAT
    button: int = imported(default=1)
    speed: float = imported(default=1)
    rotate_speed: float = imported(default=0)
    slide_ref: EntityRef[BaseSlide] = imported(name="slide")

    kind: NoteKind = entity_data()
    start_time: float = entity_data()
    target_time: float = entity_data()

    input_interval: Interval = shared_memory()
    unadjusted_input_interval: Interval = shared_memory()

    # The id of the tap that activated this note, for tap notes and flicks or released the note, for release notes.
    # This is set by the input manager rather than the note itself.
    captured_touch_id: int = shared_memory()
    touch_captured_time: float = shared_memory()

    def spawn_order(self) -> float:
        return self.start_time

    def should_spawn(self) -> bool:
        return time() >= self.start_time

    def preprocess(self):
        self.kind = cast(NoteKind, self.key)
        self.result.bucket = get_note_bucket(self.kind)
        # Handle mirror options

        self.target_time = beat_to_time(self.beat)
        appear_time = get_tap_appear_time(self.speed)
        self.start_time = self.target_time - appear_time

        self.input_interval = self.judgment_window.good + self.target_time + input_offset()
        self.unadjusted_input_interval = self.judgment_window.good + self.target_time
        
    def update_sequential(self):
        if self.despawn:
            return
        if self.is_scored and time() in self.input_interval and self.captured_touch_id == 0:
            NoteMemory.active_tap_inputs.append(self.ref())

    def update_parallel(self):
        if self.despawn:
            return
        if not self.is_scored and time() >= self.target_time:
            self.despawn = True
            return
        if time() > self.input_interval.end:
            self.handle_miss()
            return
        draw_note(self.kind, self.button, self.start_time, self.target_time, get_note_angle(self.rotate_speed))

    def touch(self):
        if not self.is_scored:
            return
        if self.despawn:
            return
        if time() < self.input_interval.start:
            return
        self.handle_hit()

    def terminate(self):
        # if self.should_play_hit_effects:
        #     # We do this here for parallelism, and to reduce compilation time.
        #     play_note_hit_effects(
        #         self.kind,
        #         self.effect_kind,
        #         self.visual_lane,
        #         self.size,
        #         self.direction,
        #         self.result.judgment,
        #         y_offset=self.visual_y_offset,
        #         pivot_lane=self.visual_pivot_lane,
        #         half_offset=self.visual_half_offset,
        #         single_line=self.visual_single_line,
        #         lane_particles=self.visual_lane_particles,
        #         transform=self.visual_stage_transform().transform(),
        #     )
        # if self.is_scored:
        #     self.result.haptic = get_note_haptic_feedback(self.kind, self.result.judgment)
        # self.end_time = offset_adjusted_time()
        # self.played_hit_effects = self.should_play_hit_effects
        pass

    @property
    def hitbox(self):
        button = clamp(self.button - 1, 0, len(Hitboxes.button))
        return Hitboxes.button[button]

    @property
    def judgment_window(self):
        return buckets.NOTE_WINDOW

    def judge(self, actual_time: float):
        if not is_ex(self.kind):
            judgment = self.judgment_window.judge(actual_time, self.target_time)
            error = self.judgment_window.good.clamp(actual_time - self.target_time)
            bucket_val = error * buckets.WINDOW_SCALE
        else:
            judgment = Judgment.PERFECT
            error = 0
            bucket_val = self.judgment_window.good.clamp(actual_time - self.target_time) * buckets.WINDOW_SCALE
        self.result.judgment = judgment
        self.result.accuracy = error
        if self.result.bucket.id != -1:
            self.result.bucket_value = bucket_val
        self.despawn = True

    def handle_hit(self):
        if time() > self.input_interval.end:
            return
        if self.captured_touch_id == 0:
            return
        captured_touch = next(touch for touch in touches() if touch.id == self.captured_touch_id)
        self.judge(captured_touch.time)

    def handle_miss(self):
        self.result.judgment = Judgment.MISS
        self.result.accuracy = self.judgment_window.good.end
        self.result.bucket = Bucket(-1)
        self.despawn = True

@level_memory
class NoteMemory:
    active_tap_inputs: VarArray[EntityRef[BaseNote], Dim[256]]

NormalTapNote = BaseNote.derive(archetype_names.NORMAL_TAP_NOTE, is_scored=True, key=NoteKind.NORM_TAP)
ExTapNote = BaseNote.derive(archetype_names.EX_TAP_NOTE, is_scored=True, key=NoteKind.EX_TAP)
EachTapNote = BaseNote.derive(archetype_names.EACH_TAP_NOTE, is_scored=True, key=NoteKind.EACH_TAP)
ExEachTapNote = BaseNote.derive(archetype_names.EX_EACH_TAP_NOTE, is_scored=True, key=NoteKind.EX_EACH_TAP)
BreakTapNote = BaseNote.derive(archetype_names.BREAK_TAP_NOTE, is_scored=True, key=NoteKind.BREAK_TAP)
ExBreakTapNote = BaseNote.derive(archetype_names.EX_BREAK_TAP_NOTE, is_scored=True, key=NoteKind.EX_BREAK_TAP)

NormalStarNote = BaseNote.derive(archetype_names.NORMAL_STAR_NOTE, is_scored=True, key=NoteKind.NORM_STAR)
ExStarNote = BaseNote.derive(archetype_names.EX_STAR_NOTE, is_scored=True, key=NoteKind.EX_STAR)
EachStarNote = BaseNote.derive(archetype_names.EACH_STAR_NOTE, is_scored=True, key=NoteKind.EACH_STAR)
ExEachStarNote = BaseNote.derive(archetype_names.EX_EACH_STAR_NOTE, is_scored=True, key=NoteKind.EX_EACH_STAR)
BreakStarNote = BaseNote.derive(archetype_names.BREAK_STAR_NOTE, is_scored=True, key=NoteKind.BREAK_STAR)
ExBreakStarNote = BaseNote.derive(archetype_names.EX_BREAK_STAR_NOTE, is_scored=True, key=NoteKind.EX_BREAK_STAR)

DoubleStarNote = BaseNote.derive(archetype_names.DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.DOUBLE_STAR)
ExDoubleStarNote = BaseNote.derive(archetype_names.EX_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.EX_DOUBLE_STAR)
EachDoubleStarNote = BaseNote.derive(archetype_names.EACH_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.EACH_DOUBLE_STAR)
ExEachDoubleStarNote = BaseNote.derive(archetype_names.EX_EACH_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.EX_EACH_DOUBLE_STAR)
BreakDoubleStarNote = BaseNote.derive(archetype_names.BREAK_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.BREAK_DOUBLE_STAR)
ExBreakDoubleStarNote = BaseNote.derive(archetype_names.EX_BREAK_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.EX_BREAK_DOUBLE_STAR)

NOTE_ARCHETYPES = (
    NormalTapNote,
    ExTapNote,
    EachTapNote,
    ExEachTapNote,
    BreakTapNote,
    ExBreakTapNote,
    NormalStarNote,
    ExStarNote,
    EachStarNote,
    ExEachStarNote,
    BreakStarNote,
    ExBreakStarNote,
    DoubleStarNote,
    ExDoubleStarNote,
    EachDoubleStarNote,
    ExEachDoubleStarNote,
    BreakDoubleStarNote,
    ExBreakDoubleStarNote,
)