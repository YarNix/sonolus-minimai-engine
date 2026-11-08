from __future__ import annotations
from typing import cast

from sonolus.script.archetype import (
    StandardImport,
    entity_data,
    entity_memory,
    imported,
    shared_memory,
)
from sonolus.script.runtime import input_offset, time, touches
from sonolus.script.timing import beat_to_time
from sonolus.script.bucket import Bucket, Judgment

from minimai.lib.game import ArcadeJudgment, apply_button_mirror_option
from minimai.lib.note import (
    NoteKind,
    get_tap_appear_duration,
    draw_note,
    is_break,
    is_ex,
    is_star,
    get_note_angle,
)
from minimai.lib import archetype_names, buckets
from minimai.lib.effect import emit_firework_sfx, emit_tap_sfx, schedule_guide_sfx
from minimai.lib.judge_text import button_slot, spawn_judge_text
from minimai.lib.layout import layout_button_firework_center, layout_button_judge_text, layout_tap_effect
from minimai.lib.particle import spawn_tap_effect
from minimai.lib.firework import spawn_firework
from minimai.lib.scoring import BaseWeight, add_note_to_total, report_score, is_challenge_over
from minimai.play.activity_manager import report_note_time
from minimai.play.base_input import BaseInputMemory, ButtonBaseInput

# Fake-rotate star (simai ``$$``): -440 deg/s, in half-turns per second.
FAKE_ROTATION_SPEED = 440 / 180


class BaseNote(ButtonBaseInput):
    beat: StandardImport.BEAT
    speed: float = imported(default=1)
    # Specify whether to use the imported rotation speed
    has_custom_rotation: bool = imported(name="hasCustomRotation", default=False)
    import_rotate_speed: float = imported(name="rotateSpeed", default=0)

    kind: NoteKind = entity_data()

    rotate_speed: float = entity_memory()
    slide_rotate_speed: float = shared_memory()

    judgment: ArcadeJudgment = entity_memory()

    @classmethod
    def score_weight(cls) -> float:
        return BaseWeight.TAP

    def spawn_order(self) -> float:
        return self.start_time

    def should_spawn(self) -> bool:
        return time() >= self.start_time or is_challenge_over()

    def preprocess(self):
        self.kind = cast(NoteKind, self.key)
        self.result.bucket = buckets.get_note_bucket(self.kind)

        self.button = apply_button_mirror_option(self.button)

        self.target_time = beat_to_time(self.beat)
        appear_time = get_tap_appear_duration(self.speed)
        self.start_time = self.target_time - appear_time

        self.input_interval = self.judgment_window.good + self.target_time + input_offset()
        self.unadjusted_input_interval = self.judgment_window.good + self.target_time

        if not self.has_custom_rotation:
            self.import_rotate_speed = FAKE_ROTATION_SPEED if is_star(self.kind) else 0

        if self.is_scored:
            report_note_time(self.target_time)
            add_note_to_total(self.score_weight(), is_break(self.kind))

    def initialize(self):
        if is_challenge_over():
            return
        if self.is_scored:
            schedule_guide_sfx(self.target_time)
            self.emit_hit_sfx(ArcadeJudgment.CRITICAL_PERFECT, self.target_time, scheduled=True)
        if not self.has_custom_rotation and self.slide_rotate_speed != 0:
            self.rotate_speed = self.slide_rotate_speed
        else:
            self.rotate_speed = self.import_rotate_speed

    def update_sequential(self):
        if self.despawn:
            return
        if is_challenge_over():
            self.despawn = True
            return
        if self.is_judged:
            # Judged in update_parallel
            # Despawn deferred until the score is reported
            report_score(self.score_weight(), is_break(self.kind), self.judgment)
            self.despawn = True
            return
        if self.is_scored and time() in self.input_interval and self.captured_touch_id == 0:
            BaseInputMemory.active_tap_inputs.append(self.ref().with_archetype(ButtonBaseInput))

    def update_parallel(self):
        if self.despawn or self.is_judged:
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

    def emit_hit_sfx(self, judgment: ArcadeJudgment, at: float, scheduled: bool):
        emit_tap_sfx(is_break(self.kind), is_ex(self.kind), judgment, at, scheduled)
        emit_firework_sfx(self.firework, judgment, at, scheduled)

    @property
    def judgment_window(self):
        return buckets.NOTE_WINDOW

    @property
    def is_judged(self) -> bool:
        return self.judgment != ArcadeJudgment.NONE

    def judge(self, actual_time: float):
        if not is_ex(self.kind):
            judgment = self.judgment_window.judge(actual_time, self.target_time)
            error = self.judgment_window.good.clamp(actual_time - self.target_time)
            bucket_val = error * buckets.WINDOW_SCALE
        else:
            judgment = ArcadeJudgment.CRITICAL_PERFECT
            error = 0
            bucket_val = self.judgment_window.good.clamp(actual_time - self.target_time) * buckets.WINDOW_SCALE
        self.result.judgment = buckets.arcade_judgement_to_normal(judgment)
        self.result.accuracy = error
        if self.result.bucket.id != -1:
            self.result.bucket_value = bucket_val
        self.emit_hit_sfx(judgment, actual_time, scheduled=False)
        self.judgment = judgment
        report_score(self.score_weight(), is_break(self.kind), judgment)
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
        self.judgment = ArcadeJudgment.MISS

    def terminate(self):
        # Spawned here rather than at judgment, so every way of despawning is covered.
        if self.is_scored and self.is_judged:
            self.play_hit_effects()

    def play_hit_effects(self):
        spawn_tap_effect(is_break(self.kind), self.judgment, layout_tap_effect(self.button))
        spawn_firework(self.firework, self.judgment, layout_button_firework_center(self.button))
        spawn_judge_text(
            self.judgment,
            is_break(self.kind),
            self.result.accuracy,
            button_slot(self.button),
            layout_button_judge_text(self.button),
        )

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