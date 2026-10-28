from __future__ import annotations

from enum import IntEnum, auto
from typing import cast

from sonolus.script.archetype import StandardImport, entity_data, entity_memory, imported
from sonolus.script.bucket import Bucket
from sonolus.script.interval import Interval, clamp
from sonolus.script.runtime import delta_time, input_offset, time, touches
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names, buckets
from minimai.lib.input_state import InputState
from minimai.lib.hold import HoldState
from minimai.lib.touch import get_touch_appear_duration
from minimai.lib.touch_hold import TouchHoldKind, draw_touch_hold
from minimai.play.base_input import BaseInputMemory, TouchBaseInput


class BaseTouchHold(TouchBaseInput):
    beat: StandardImport.BEAT
    speed: float = imported(default=1)
    # Beats from the head to the end. 0 = the touch hold ends with its head.
    hold_duration: float = imported(name="holdDuration", default=0)

    kind: TouchHoldKind = entity_data()
    start_time: float = entity_data()
    end_time: float = entity_data()

    head_judgment: buckets.ArcadeJudgment = entity_memory()
    head_error: float = entity_memory()

    hold_input_interval: Interval = entity_data()

    release_time: float = entity_memory()
    pending_release: float = entity_memory()
    hold_state: HoldState = entity_memory()

    def spawn_order(self) -> float:
        return self.start_time

    def should_spawn(self) -> bool:
        return time() >= self.start_time

    def preprocess(self):
        self.kind = cast(TouchHoldKind, self.key)
        self.result.bucket = buckets.get_touch_hold_bucket(self.kind)

        self.target_time = beat_to_time(self.beat)
        self.end_time = beat_to_time(self.beat + max(self.hold_duration, 0))
        self.start_time = self.target_time - get_touch_appear_duration(self.speed)

        self.input_interval = self.judgment_window.good + self.target_time + input_offset()
        self.unadjusted_input_interval = self.judgment_window.good + self.target_time

        self.hold_input_interval = buckets.touch_hold_interval(self.target_time, self.end_time) + input_offset()

    def initialize(self):
        self.hold_state = HoldState.DEFAULT

    @property
    def judgment_window(self):
        return buckets.TOUCH_WINDOW

    @property
    def is_head_judged(self) -> bool:
        return self.head_judgment != buckets.ArcadeJudgment.NONE

    def update_sequential(self):
        if self.despawn:
            return
        if (
            self.is_scored
            and not self.is_head_judged
            and time() in self.input_interval
            and self.captured_touch_id == 0
        ):
            BaseInputMemory.active_touch_inputs.append(self.ref().with_archetype(TouchBaseInput))
        # Releases are read here: touch() isn't called in frames without touches.
        # No body check when the touch hold is 27 frames or shorter (empty or zero-length interval).
        if self.hold_input_interval.length > 0 and time() in self.hold_input_interval:
            self.check_body(InputState.sensor_touch_down[self.sensor - 1])

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
            self.pending_release += delta_time()
            self.hold_state = HoldState.RELEASED_GRACE
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
        self.head_judgment = self.judgment_window.judge(captured_touch.time, self.target_time)
        self.head_error = self.judgment_window.good.clamp(captured_touch.time - self.target_time)
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
        draw_touch_hold(self.kind, self.sensor, self.start_time, self.target_time, self.end_time, self.hold_state)

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

        self.result.judgment = buckets.arcade_judgement_to_normal(final)
        self.result.accuracy = self.head_error
        if self.head_judgment == buckets.ArcadeJudgment.MISS:
            self.result.bucket = Bucket(-1)
        elif self.result.bucket.id != -1:
            self.result.bucket_value = self.head_error * buckets.WINDOW_SCALE
        self.despawn = True


NormalTouchHoldNote = BaseTouchHold.derive(
    archetype_names.NORMAL_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.NORM_TOUCH_HOLD
)
EachTouchHoldNote = BaseTouchHold.derive(
    archetype_names.EACH_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.EACH_TOUCH_HOLD
)
BreakTouchHoldNote = BaseTouchHold.derive(
    archetype_names.BREAK_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.BREAK_TOUCH_HOLD
)

TOUCH_HOLD_ARCHETYPES = (
    NormalTouchHoldNote,
    EachTouchHoldNote,
    BreakTouchHoldNote,
)
