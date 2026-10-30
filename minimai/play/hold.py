from __future__ import annotations

from typing import cast

from sonolus.script.archetype import StandardImport, entity_data, entity_memory, imported
from sonolus.script.bucket import Bucket
from sonolus.script.interval import Interval, clamp
from sonolus.script.runtime import delta_time, input_offset, time, touches
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names, buckets
from minimai.lib.game import apply_button_mirror_option
from minimai.lib.hold import HoldState, HoldKind, draw_hold, is_ex_hold
from minimai.lib.input_state import InputState
from minimai.lib.note import get_tap_appear_duration
from minimai.play.base_input import BaseInputMemory, ButtonBaseInput


class BaseHold(ButtonBaseInput):
    beat: StandardImport.BEAT
    speed: float = imported(default=1)
    # Beats from the head to the end. 0 = the hold ends with its head.
    hold_duration: float = imported(name="holdDuration", default=0)

    kind: HoldKind = entity_data()
    end_time: float = entity_data()

    head_judgment: buckets.ArcadeJudgment = entity_memory()
    head_error: float = entity_memory()
    head_bucket_value: float = entity_memory()
    held_at_head: bool = entity_memory()

    hold_input_interval: Interval = entity_data()

    release_time: float = entity_memory()
    pending_release: float = entity_memory()
    hold_state: HoldState = entity_memory()

    def spawn_order(self) -> float:
        return self.start_time

    def should_spawn(self) -> bool:
        return time() >= self.start_time

    def preprocess(self):
        self.kind = cast(HoldKind, self.key)
        self.result.bucket = buckets.get_hold_bucket(self.kind)
        self.button = apply_button_mirror_option(self.button)

        self.target_time = beat_to_time(self.beat)
        self.end_time = beat_to_time(self.beat + max(self.hold_duration, 0))
        self.start_time = self.target_time - get_tap_appear_duration(self.speed)
        self.is_hold = True

        self.input_interval = self.judgment_window.good + self.target_time + input_offset()
        self.unadjusted_input_interval = self.judgment_window.good + self.target_time

        self.hold_input_interval = buckets.hold_interval(self.target_time, self.end_time) + input_offset()

    def initialize(self):
        self.hold_state = HoldState.DEFAULT

    @property
    def judgment_window(self):
        return buckets.NOTE_WINDOW

    @property
    def is_head_judged(self) -> bool:
        return self.head_judgment != buckets.ArcadeJudgment.NONE

    def update_sequential(self):
        if self.despawn:
            return
        if self.is_scored and not self.is_head_judged and time() in self.input_interval:
            if self.captured_touch_id == 0:
                BaseInputMemory.active_tap_inputs.append(self.ref().with_archetype(ButtonBaseInput))
            if (self.target_time + input_offset() <= time()
                and self.hold_input_interval.length <= 0
                and self.is_pressed()
            ):
                self.held_at_head = True
        # Releases are read here: touch() isn't called in frames without touches.
        if self.hold_input_interval.length > 0 and time() in self.hold_input_interval:
            self.check_body(self.is_pressed())

    def is_pressed(self) -> bool:
        return InputState.button_down[self.button - 1] != 0 or InputState.sensor_touch_down[self.sensor - 1]

    def check_body(self, pressed: bool):
        if pressed:
            self.pending_release = 0
            self.hold_state = HoldState.PRESSED
            return
        # The first frames of a release after the head (or a press) are forgiven.
        if (
            self.is_head_judged
            and self.hold_state != HoldState.RELEASED
            and self.pending_release <= 2 / 60
        ):
            self.hold_state = HoldState.RELEASED_GRACE
            self.pending_release += delta_time()
            return
        self.release_time += self.pending_release + delta_time()
        self.pending_release = 0
        self.hold_state = HoldState.RELEASED

    def touch(self):
        if not self.is_scored or self.despawn or self.is_head_judged:
            return
        if time() not in self.input_interval:
            return
        if self.captured_touch_id == 0:
            return
        captured_touch = next(touch for touch in touches() if touch.id == self.captured_touch_id)
        self.judge_head(captured_touch.time)

    def judge_head(self, actual_time: float):
        error = self.judgment_window.good.clamp(actual_time - self.target_time)
        if is_ex_hold(self.kind):
            self.head_judgment = buckets.ArcadeJudgment.CRITICAL_PERFECT
            self.head_error = 0
        else:
            self.head_judgment = self.judgment_window.judge(actual_time, self.target_time)
            self.head_error = error
        self.head_bucket_value = error * buckets.WINDOW_SCALE
        self.hold_state = HoldState.PRESSED

    def update_parallel(self):
        if self.despawn:
            return
        if not self.is_scored and time() >= self.end_time:
            self.despawn = True
            return
        if self.is_scored and not self.is_head_judged and time() > self.input_interval.end:
            self.head_judgment = buckets.ArcadeJudgment.MISS
            self.head_error = self.judgment_window.good.end
        if self.is_scored and self.is_head_judged and time() >= self.end_time + input_offset():
            self.finish()
            return
        draw_hold(self.kind, self.button, self.start_time, self.target_time, self.end_time, self.hold_state)

    def finish(self):
        final = self.head_judgment
        if self.hold_input_interval.length > 0:
            if self.hold_state == HoldState.RELEASED or (
                self.hold_state == HoldState.DEFAULT
                and self.head_judgment == buckets.ArcadeJudgment.MISS
            ):
                self.release_time += delta_time()

            held = self.hold_input_interval.length
            percent = clamp((held - self.release_time) / held, 0, 1)
            final = buckets.hold_end_judge(self.head_judgment, percent)
        elif self.head_judgment == buckets.ArcadeJudgment.MISS and self.held_at_head:
            # Judged like a longer hold held all the way, so a missed head still gives a Good.
            final = buckets.hold_end_judge(self.head_judgment, 1)

        self.result.judgment = buckets.arcade_judgement_to_normal(final)
        self.result.accuracy = self.head_error
        if self.head_judgment == buckets.ArcadeJudgment.MISS:
            self.result.bucket = Bucket(-1)
        elif self.result.bucket.id != -1:
            self.result.bucket_value = self.head_bucket_value
        self.despawn = True


NormalHoldNote = BaseHold.derive(archetype_names.NORMAL_HOLD_NOTE, is_scored=True, key=HoldKind.NORM_HOLD)
ExHoldNote = BaseHold.derive(archetype_names.EX_HOLD_NOTE, is_scored=True, key=HoldKind.EX_HOLD)
EachHoldNote = BaseHold.derive(archetype_names.EACH_HOLD_NOTE, is_scored=True, key=HoldKind.EACH_HOLD)
ExEachHoldNote = BaseHold.derive(archetype_names.EX_EACH_HOLD_NOTE, is_scored=True, key=HoldKind.EX_EACH_HOLD)
BreakHoldNote = BaseHold.derive(archetype_names.BREAK_HOLD_NOTE, is_scored=True, key=HoldKind.BREAK_HOLD)
ExBreakHoldNote = BaseHold.derive(archetype_names.EX_BREAK_HOLD_NOTE, is_scored=True, key=HoldKind.EX_BREAK_HOLD)

HOLD_ARCHETYPES = (
    NormalHoldNote,
    ExHoldNote,
    EachHoldNote,
    ExEachHoldNote,
    BreakHoldNote,
    ExBreakHoldNote,
)
