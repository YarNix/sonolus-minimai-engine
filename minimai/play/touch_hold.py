from __future__ import annotations

from typing import cast

from sonolus.script.archetype import EntityRef, StandardImport, entity_data, entity_memory, imported, shared_memory
from sonolus.script.bucket import Bucket
from sonolus.script.interval import Interval, clamp
from sonolus.script.particle import ParticleHandle
from sonolus.script.runtime import delta_time, input_offset, time, touches
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names, buckets
from minimai.lib.effect import emit_firework_sfx, emit_hold_end_sfx, is_hit, schedule_guide_sfx
from minimai.lib.judge_text import spawn_judge_text, touch_hold_slot
from minimai.lib.layout import (
    layout_sensor_firework_center,
    layout_touch_hold_effect,
    layout_touch_hold_glow,
    layout_touch_hold_judge_text,
)
from minimai.lib.particle import destroy_hold_glow, spawn_tap_effect, update_hold_glow
from minimai.lib.firework import spawn_firework
from minimai.lib.options import Options
from minimai.lib.game import apply_sensor_mirror_option
from minimai.lib.input_state import InputState
from minimai.lib.hold import HoldState
from minimai.lib.touch import get_touch_appear_duration
from minimai.lib.touch_hold import TouchHoldKind, draw_touch_hold
from minimai.play.activity_manager import register_touch_hold_riser, report_note_time
from minimai.play.base_input import BaseInputMemory, TouchBaseInput


class BaseTouchHold(TouchBaseInput):
    beat: StandardImport.BEAT
    speed: float = imported(default=1)
    # Beats from the head to the end. 0 = the touch hold ends with its head.
    hold_duration: float = imported(name="holdDuration", default=0)
    # Body group: the touch holds of the touch group. While more than half of them are held,
    # every member's body counts as held. Same leader convention as the touch group.
    body_group_leader: EntityRef[BaseTouchHold] = imported(name="holdGroup")
    body_group_size: int = imported(name="holdGroupSize", default=0)

    kind: TouchHoldKind = entity_data()
    start_time: float = entity_data()
    end_time: float = entity_data()

    head_judgment: buckets.ArcadeJudgment = entity_memory()
    head_error: float = entity_memory()
    held_at_head: bool = entity_memory()

    hold_input_interval: Interval = entity_data()

    release_time: float = entity_memory()
    pending_release: float = entity_memory()
    hold_state: HoldState = entity_memory()
    pressed: bool = entity_memory()

    judgment: buckets.ArcadeJudgment = entity_memory()
    glow: ParticleHandle = entity_memory()

    # Body group state, kept on the leader: how many members were held in the frame at
    # ``body_group_time``.
    body_group_time: float = shared_memory()
    body_group_held: int = shared_memory()

    def spawn_order(self) -> float:
        return self.start_time

    def should_spawn(self) -> bool:
        return time() >= self.start_time

    def preprocess(self):
        self.kind = cast(TouchHoldKind, self.key)
        self.result.bucket = buckets.get_touch_hold_bucket(self.kind)
        self.sensor = apply_sensor_mirror_option(self.sensor)

        self.target_time = beat_to_time(self.beat)
        self.end_time = beat_to_time(self.beat + max(self.hold_duration, 0))
        self.start_time = self.target_time - get_touch_appear_duration(self.speed)

        self.input_interval = self.judgment_window.good + self.target_time + input_offset()
        self.unadjusted_input_interval = self.judgment_window.good + self.target_time

        self.hold_input_interval = buckets.touch_hold_interval(self.target_time, self.end_time) + input_offset()

        if self.is_scored:
            report_note_time(self.target_time)
            schedule_guide_sfx(self.target_time)
            if self.end_time - self.target_time >= 1 / 60:
                schedule_guide_sfx(self.end_time)
            # The head has no sound; the riser plays instead.
            self.emit_end_sfx(buckets.ArcadeJudgment.CRITICAL_PERFECT, self.end_time, scheduled=True)

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
        if self.is_scored and not self.is_head_judged and time() in self.input_interval:
            if self.captured_touch_id == 0:
                BaseInputMemory.active_touch_inputs.append(self.ref().with_archetype(TouchBaseInput))
            if (self.hold_input_interval.length <= 0
                and self.target_time + input_offset() <= time()
                and InputState.sensor_touch_down[self.sensor - 1]):
                self.held_at_head = True
        # Releases are read every frame: touch() isn't called in frames without touches.
        self.pressed = InputState.sensor_touch_down[self.sensor - 1]
        if self.pressed and self.body_group_leader.index > 0:
            leader = self.body_group_leader.get()
            if leader.body_group_time != time():
                leader.body_group_time = time()
                leader.body_group_held = 0
            leader.body_group_held += 1
        if self.wants_riser:
            register_touch_hold_riser()

    @property
    def wants_riser(self) -> bool:
        """From a hit head to the end, or while pressed after a missed head. With auto SFX, the
        whole body."""
        result = False
        if Options.auto_sfx:
            result = self.target_time <= time() < self.end_time
        elif self.is_scored:
            result = is_hit(self.head_judgment) or (self.is_head_judged and self.pressed)
        return result

    @property
    def is_body_group_held(self) -> bool:
        result = False
        if self.body_group_leader.index > 0:
            leader = self.body_group_leader.get()
            result = leader.body_group_time == time() and leader.body_group_held * 2 > self.body_group_size
        return result

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
        self.register_group_hit(self.head_judgment, self.head_error)

    def update_parallel(self):
        if self.despawn:
            return
        if not self.is_scored and time() >= self.end_time:
            self.despawn = True
            return
        if self.is_scored and not self.is_head_judged:
            if time() > self.input_interval.end:
                self.head_judgment = buckets.ArcadeJudgment.MISS
                self.head_error = self.judgment_window.good.end
            elif self.is_group_judged:
                self.head_judgment = self.group_result
                self.head_error = self.group_result_error
                self.hold_state = HoldState.PRESSED
        # No body check when the touch hold is 27 frames or shorter (empty or zero-length interval).
        if self.hold_input_interval.length > 0 and time() in self.hold_input_interval:
            self.check_body(self.pressed or self.is_body_group_held)
        if self.is_scored and self.is_head_judged and time() >= self.end_time + input_offset():
            self.finish()
            return
        update_hold_glow(self.glow, self.is_glowing, self.head_judgment, layout_touch_hold_glow(self.sensor))
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
        elif self.head_judgment == buckets.ArcadeJudgment.MISS and self.held_at_head:
            # Judged like a longer hold held all the way, so a missed head still gives a Good.
            final = buckets.hold_end_judge(self.head_judgment, 1)

        self.result.judgment = buckets.arcade_judgement_to_normal(final)
        self.result.accuracy = self.head_error
        if self.head_judgment == buckets.ArcadeJudgment.MISS:
            self.result.bucket = Bucket(-1)
        elif self.result.bucket.id != -1:
            self.result.bucket_value = self.head_error * buckets.WINDOW_SCALE
        self.emit_end_sfx(final, time(), scheduled=False)
        self.judgment = final
        self.despawn = True

    @property
    def is_glowing(self) -> bool:
        return self.is_scored and self.is_head_judged and (
            self.hold_state == HoldState.PRESSED or self.hold_state == HoldState.RELEASED_GRACE
        )

    def terminate(self):
        destroy_hold_glow(self.glow)
        if self.is_scored and self.judgment != buckets.ArcadeJudgment.NONE:
            self.play_end_effects()

    def play_end_effects(self):
        is_break = self.kind == TouchHoldKind.BREAK_TOUCH_HOLD
        spawn_tap_effect(is_break, self.judgment, layout_touch_hold_effect(self.sensor))
        spawn_firework(self.firework, self.judgment, layout_sensor_firework_center(self.sensor))
        spawn_judge_text(
            self.judgment, is_break, self.head_error, touch_hold_slot(self.sensor), layout_touch_hold_judge_text(self.sensor)
        )

    def emit_end_sfx(self, judgment: buckets.ArcadeJudgment, at: float, scheduled: bool):
        emit_hold_end_sfx(judgment, at, scheduled)
        emit_firework_sfx(self.firework, judgment, at, scheduled)


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
