from typing import cast

from sonolus.script.archetype import (
    StandardImport,
    entity_data,
    entity_memory,
    imported,
)
from sonolus.script.runtime import input_offset, time, touches
from sonolus.script.timing import beat_to_time
from sonolus.script.bucket import Bucket, Judgment

from minimai.lib import archetype_names, buckets
from minimai.lib.effect import emit_firework_sfx, emit_touch_sfx, schedule_guide_sfx
from minimai.lib.judge_text import spawn_judge_text, touch_slot
from minimai.lib.layout import layout_sensor_firework_center, layout_touch_effect, layout_touch_judge_text
from minimai.lib.particle import spawn_touch_effect
from minimai.lib.firework import spawn_firework
from minimai.lib.scoring import BaseWeight, add_note_to_total, report_score
from minimai.lib.touch import TouchKind, draw_touch, get_touch_appear_duration
from minimai.lib.game import ArcadeJudgment, apply_sensor_mirror_option
from minimai.play.base_input import BaseInputMemory, TouchBaseInput
from minimai.play.activity_manager import register_touch_overlap, report_note_time

class BaseTouch(TouchBaseInput):
    beat: StandardImport.BEAT
    speed: float = imported(default=1)

    kind: TouchKind = entity_data()
    start_time: float = entity_data()

    judgment: ArcadeJudgment = entity_memory()

    def spawn_order(self) -> float:
        return self.start_time

    def should_spawn(self) -> bool:
        return time() >= self.start_time

    def preprocess(self):
        self.kind = cast(TouchKind, self.key)
        self.result.bucket = buckets.get_touch_bucket(self.kind)

        self.sensor = apply_sensor_mirror_option(self.sensor)

        self.target_time = beat_to_time(self.beat)
        appear_time = get_touch_appear_duration(self.speed)
        self.start_time = self.target_time - appear_time

        self.input_interval = self.judgment_window.good + self.target_time + input_offset()
        self.unadjusted_input_interval = self.judgment_window.good + self.target_time

        if self.is_scored:
            report_note_time(self.target_time)
            schedule_guide_sfx(self.target_time)
            self.emit_hit_sfx(ArcadeJudgment.CRITICAL_PERFECT, self.target_time, scheduled=True)
            add_note_to_total(BaseWeight.TAP, self.kind == TouchKind.BREAK_TOUCH)

    def update_sequential(self):
        if self.despawn:
            return
        if self.judgment != ArcadeJudgment.NONE:
            # Judged in update_parallel
            # Despawn deferred until the score is reported
            report_score(BaseWeight.TAP, self.kind == TouchKind.BREAK_TOUCH, self.judgment)
            self.despawn = True
            return
        register_touch_overlap(self.sensor, self.start_time, self.index, self.kind)
        if self.is_scored and time() in self.input_interval: 
            # and self.captured_touch_id == 0:
            BaseInputMemory.active_touch_inputs.append(self.ref().with_archetype(TouchBaseInput))

    def update_parallel(self):
        if self.despawn or self.is_judged:
            return
        if not self.is_scored and time() >= self.target_time:
            self.despawn = True
            return
        if time() > self.input_interval.end:
            self.handle_miss()
            return
        if self.is_scored and self.is_group_judged:
            self.set_result(self.group_result, self.group_result_error)
            return
        draw_touch(self.kind, self.sensor, self.start_time, self.target_time)

    def touch(self):
        if not self.is_scored:
            return
        if self.despawn:
            return
        if time() < self.input_interval.start:
            return
        self.handle_touch()

    @property
    def judgment_window(self):
        return buckets.TOUCH_WINDOW

    @property
    def is_judged(self) -> bool:
        return self.judgment != ArcadeJudgment.NONE

    def judge(self, actual_time: float):
        judgment = self.judgment_window.judge(actual_time, self.target_time)
        error = self.judgment_window.good.clamp(actual_time - self.target_time)
        self.register_group_hit(judgment, error)
        self.set_result(judgment, error)
        report_score(BaseWeight.TAP, self.kind == TouchKind.BREAK_TOUCH, judgment)
        self.despawn = True

    def set_result(self, judgment: ArcadeJudgment, error: float):
        self.result.judgment = buckets.arcade_judgement_to_normal(judgment)
        self.result.accuracy = error
        if self.result.bucket.id != -1:
            self.result.bucket_value = error * buckets.WINDOW_SCALE
        self.emit_hit_sfx(judgment, time(), scheduled=False)
        self.judgment = judgment

    def emit_hit_sfx(self, judgment: ArcadeJudgment, at: float, scheduled: bool):
        emit_touch_sfx(self.kind == TouchKind.BREAK_TOUCH, judgment, at, scheduled)
        emit_firework_sfx(self.firework, judgment, at, scheduled)

    def handle_touch(self):
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
        if self.is_scored and self.is_judged:
            self.play_hit_effects()

    def play_hit_effects(self):
        spawn_touch_effect(self.judgment, layout_touch_effect(self.sensor))
        spawn_firework(self.firework, self.judgment, layout_sensor_firework_center(self.sensor))
        spawn_judge_text(
            self.judgment,
            self.kind == TouchKind.BREAK_TOUCH,
            self.result.accuracy,
            touch_slot(self.sensor),
            layout_touch_judge_text(self.sensor),
        )

NormalTouchNote = BaseTouch.derive(archetype_names.NORMAL_TOUCH_NOTE, is_scored=True, key=TouchKind.NORM_TOUCH)
BreakTouchNote = BaseTouch.derive(archetype_names.BREAK_TOUCH_NOTE, is_scored=True, key=TouchKind.BREAK_TOUCH)
EachTouchNote = BaseTouch.derive(archetype_names.EACH_TOUCH_NOTE, is_scored=True, key=TouchKind.EACH_TOUCH)

TOUCH_ARCHETYPES = [
    NormalTouchNote,
    BreakTouchNote,
    EachTouchNote,
]
