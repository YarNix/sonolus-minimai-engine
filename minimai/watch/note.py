from __future__ import annotations
from typing import cast

from sonolus.script.archetype import StandardImport, entity_data, entity_memory, imported, shared_memory
from sonolus.script.bucket import Bucket, Judgment
from sonolus.script.runtime import is_replay
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names, buckets
from minimai.lib.effect import emit_firework_sfx, emit_tap_sfx, is_hit, report_note_time, schedule_guide_sfx
from minimai.lib.game import ArcadeJudgment, apply_button_mirror_option
from minimai.lib.initialization import init_common
from minimai.lib.note import (
    FAKE_ROTATION_SPEED,
    NoteKind,
    draw_note,
    get_note_angle,
    get_tap_appear_duration,
    is_break,
    is_ex,
    is_star,
)
from minimai.lib.options import Options
from minimai.lib.scoring import BaseWeight, add_note_to_total
from minimai.watch.base import WatchButtonBase


class WatchBaseNote(WatchButtonBase):
    beat: StandardImport.BEAT
    speed: float = imported(default=1)
    has_custom_rotation: bool = imported(name="hasCustomRotation", default=False)
    import_rotate_speed: float = imported(name="rotateSpeed", default=0)

    # From the replay. Without one, a critical perfect at the target time.
    judged_time: float = imported(name="judgedTime")
    arcade_judgment: ArcadeJudgment = imported(name="arcadeJudgment")
    standard_judgment: StandardImport.JUDGMENT
    accuracy: StandardImport.ACCURACY

    kind: NoteKind = entity_data()

    rotate_speed: float = entity_memory()
    slide_rotate_speed: float = shared_memory()

    @classmethod
    def score_weight(cls) -> float:
        return BaseWeight.TAP

    def preprocess(self):
        init_common()
        self.kind = cast(NoteKind, self.key)
        self.result.bucket = buckets.get_note_bucket(self.kind)

        self.button = apply_button_mirror_option(self.button)

        self.target_time = beat_to_time(self.beat)
        self.start_time = self.target_time - get_tap_appear_duration(self.speed)

        if not self.has_custom_rotation:
            self.import_rotate_speed = FAKE_ROTATION_SPEED if is_star(self.kind) else 0

        self.exit_time = self.target_time
        if not self.is_scored:
            return
        report_note_time(self.target_time)
        add_note_to_total(self.score_weight(), is_break(self.kind))
        self.result.target_time = self.target_time
        if not is_replay():
            self.arcade_judgment = ArcadeJudgment.CRITICAL_PERFECT
            self.judged_time = self.target_time
            self.standard_judgment = Judgment.PERFECT
        if not is_hit(self.arcade_judgment):
            self.result.bucket = Bucket(-1)
        elif self.result.bucket.id != -1:
            self.result.bucket_value = self.accuracy * buckets.WINDOW_SCALE

        if self.arcade_judgment == ArcadeJudgment.NONE:
            # Never reached in the replay: gone when it would have been missed.
            self.exit_time = self.target_time + self.judgment_window.good.end
            return
        self.exit_time = self.judged_time
        schedule_guide_sfx(self.target_time)
        if Options.auto_sfx:
            self.emit_hit_sfx(ArcadeJudgment.CRITICAL_PERFECT, self.target_time)
        else:
            self.emit_hit_sfx(self.arcade_judgment, self.judged_time)

    def spawn_time(self) -> float:
        return self.start_time

    def despawn_time(self) -> float:
        return self.exit_time

    def initialize(self):
        if not self.has_custom_rotation and self.slide_rotate_speed != 0:
            self.rotate_speed = self.slide_rotate_speed
        else:
            self.rotate_speed = self.import_rotate_speed

    def update_parallel(self):
        draw_note(self.kind, self.button, self.start_time, self.target_time, get_note_angle(self.rotate_speed))

    def emit_hit_sfx(self, judgment: ArcadeJudgment, at: float):
        emit_tap_sfx(is_break(self.kind), is_ex(self.kind), judgment, at, scheduled=True)
        emit_firework_sfx(self.firework, judgment, at, scheduled=True)

    @property
    def judgment_window(self):
        return buckets.NOTE_WINDOW


WatchNormalTapNote = WatchBaseNote.derive(archetype_names.NORMAL_TAP_NOTE, is_scored=True, key=NoteKind.NORM_TAP)
WatchExTapNote = WatchBaseNote.derive(archetype_names.EX_TAP_NOTE, is_scored=True, key=NoteKind.EX_TAP)
WatchEachTapNote = WatchBaseNote.derive(archetype_names.EACH_TAP_NOTE, is_scored=True, key=NoteKind.EACH_TAP)
WatchExEachTapNote = WatchBaseNote.derive(archetype_names.EX_EACH_TAP_NOTE, is_scored=True, key=NoteKind.EX_EACH_TAP)
WatchBreakTapNote = WatchBaseNote.derive(archetype_names.BREAK_TAP_NOTE, is_scored=True, key=NoteKind.BREAK_TAP)
WatchExBreakTapNote = WatchBaseNote.derive(archetype_names.EX_BREAK_TAP_NOTE, is_scored=True, key=NoteKind.EX_BREAK_TAP)

WatchNormalStarNote = WatchBaseNote.derive(archetype_names.NORMAL_STAR_NOTE, is_scored=True, key=NoteKind.NORM_STAR)
WatchExStarNote = WatchBaseNote.derive(archetype_names.EX_STAR_NOTE, is_scored=True, key=NoteKind.EX_STAR)
WatchEachStarNote = WatchBaseNote.derive(archetype_names.EACH_STAR_NOTE, is_scored=True, key=NoteKind.EACH_STAR)
WatchExEachStarNote = WatchBaseNote.derive(archetype_names.EX_EACH_STAR_NOTE, is_scored=True, key=NoteKind.EX_EACH_STAR)
WatchBreakStarNote = WatchBaseNote.derive(archetype_names.BREAK_STAR_NOTE, is_scored=True, key=NoteKind.BREAK_STAR)
WatchExBreakStarNote = WatchBaseNote.derive(archetype_names.EX_BREAK_STAR_NOTE, is_scored=True, key=NoteKind.EX_BREAK_STAR)

WatchDoubleStarNote = WatchBaseNote.derive(archetype_names.DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.DOUBLE_STAR)
WatchExDoubleStarNote = WatchBaseNote.derive(archetype_names.EX_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.EX_DOUBLE_STAR)
WatchEachDoubleStarNote = WatchBaseNote.derive(archetype_names.EACH_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.EACH_DOUBLE_STAR)
WatchExEachDoubleStarNote = WatchBaseNote.derive(archetype_names.EX_EACH_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.EX_EACH_DOUBLE_STAR)
WatchBreakDoubleStarNote = WatchBaseNote.derive(archetype_names.BREAK_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.BREAK_DOUBLE_STAR)
WatchExBreakDoubleStarNote = WatchBaseNote.derive(archetype_names.EX_BREAK_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.EX_BREAK_DOUBLE_STAR)

WATCH_NOTE_ARCHETYPES = (
    WatchNormalTapNote,
    WatchExTapNote,
    WatchEachTapNote,
    WatchExEachTapNote,
    WatchBreakTapNote,
    WatchExBreakTapNote,
    WatchNormalStarNote,
    WatchExStarNote,
    WatchEachStarNote,
    WatchExEachStarNote,
    WatchBreakStarNote,
    WatchExBreakStarNote,
    WatchDoubleStarNote,
    WatchExDoubleStarNote,
    WatchEachDoubleStarNote,
    WatchExEachDoubleStarNote,
    WatchBreakDoubleStarNote,
    WatchExBreakDoubleStarNote,
)
