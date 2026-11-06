from __future__ import annotations

from typing import cast

from sonolus.script.archetype import StandardImport, entity_data, entity_memory, imported
from sonolus.script.bucket import Bucket
from sonolus.script.interval import Interval, clamp
from sonolus.script.particle import ParticleHandle
from sonolus.script.runtime import delta_time, input_offset, time, touches
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names, buckets
from minimai.lib.game import ArcadeJudgment, apply_button_mirror_option
from minimai.lib.effect import emit_firework_sfx, emit_hold_end_sfx, emit_tap_sfx, schedule_guide_sfx
from minimai.lib.judge_text import button_slot, spawn_judge_text
from minimai.lib.layout import layout_button_firework_center, layout_button_judge_text, layout_hold_effect, layout_tap_effect
from minimai.lib.particle import destroy_hold_glow, spawn_tap_effect, update_hold_glow
from minimai.lib.firework import spawn_firework
from minimai.lib.scoring import BaseWeight, add_note_to_total, report_score
from minimai.lib.hold import HoldState, HoldKind, draw_hold, is_break_hold, is_ex_hold
from minimai.lib.input_state import InputState
from minimai.lib.options import Options
from minimai.lib.note import get_tap_appear_duration
from minimai.play.activity_manager import report_note_time
from minimai.play.base_input import BaseInputMemory, ButtonBaseInput


class BaseHold(ButtonBaseInput):
    beat: StandardImport.BEAT
    speed: float = imported(default=1)
    # Beats from the head to the end. 0 = the hold ends with its head.
    hold_duration: float = imported(name="holdDuration", default=0)

    kind: HoldKind = entity_data()
    end_time: float = entity_data()

    head_judgment: ArcadeJudgment = entity_memory()
    head_error: float = entity_memory()
    head_bucket_value: float = entity_memory()
    held_at_head: bool = entity_memory()

    hold_input_interval: Interval = entity_data()

    release_time: float = entity_memory()
    pending_release: float = entity_memory()
    hold_state: HoldState = entity_memory()

    judgment: ArcadeJudgment = entity_memory()
    head_text_shown: bool = entity_memory()
    glow: ParticleHandle = entity_memory()

    @classmethod
    def score_weight(cls) -> float:
        return BaseWeight.HOLD

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

        if self.is_scored:
            report_note_time(self.target_time)
            schedule_guide_sfx(self.target_time)
            if self.end_time - self.target_time >= 1 / 60:
                schedule_guide_sfx(self.end_time)
            self.emit_head_sfx(ArcadeJudgment.CRITICAL_PERFECT, self.target_time, scheduled=True)
            self.emit_end_sfx(ArcadeJudgment.CRITICAL_PERFECT, self.end_time, scheduled=True)
            add_note_to_total(self.score_weight(), is_break_hold(self.kind))

    def initialize(self):
        self.hold_state = HoldState.DEFAULT

    @property
    def judgment_window(self):
        return buckets.NOTE_WINDOW

    @property
    def is_head_judged(self) -> bool:
        return self.head_judgment != ArcadeJudgment.NONE

    @property
    def is_judged(self) -> bool:
        return self.judgment != ArcadeJudgment.NONE

    def update_sequential(self):
        if self.despawn:
            return
        if self.is_judged:
            # Judged in update_parallel
            # Despawn deferred until the score is reported
            report_score(self.score_weight(), is_break_hold(self.kind), self.judgment)
            self.despawn = True
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
        if self.is_head_judged and not self.head_text_shown:
            self.head_text_shown = True
            if Options.hold_head_judge:
                spawn_judge_text(
                    self.head_judgment,
                    is_break_hold(self.kind),
                    self.head_error,
                    button_slot(self.button),
                    layout_button_judge_text(self.button),
                )

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
            self.head_judgment = ArcadeJudgment.CRITICAL_PERFECT
            self.head_error = 0
        else:
            self.head_judgment = self.judgment_window.judge(actual_time, self.target_time)
            self.head_error = error
        self.head_bucket_value = error * buckets.WINDOW_SCALE
        self.hold_state = HoldState.PRESSED
        self.emit_head_sfx(self.head_judgment, actual_time, scheduled=False)

    def emit_head_sfx(self, judgment: ArcadeJudgment, at: float, scheduled: bool):
        emit_tap_sfx(is_break_hold(self.kind), is_ex_hold(self.kind), judgment, at, scheduled)

    def emit_end_sfx(self, judgment: ArcadeJudgment, at: float, scheduled: bool):
        emit_hold_end_sfx(judgment, at, scheduled)
        emit_firework_sfx(self.firework, judgment, at, scheduled)

    def update_parallel(self):
        if self.despawn or self.is_judged:
            return
        if not self.is_scored and time() >= self.end_time:
            self.despawn = True
            return
        if self.is_scored and not self.is_head_judged and time() > self.input_interval.end:
            self.head_judgment = ArcadeJudgment.MISS
            self.head_error = self.judgment_window.good.end
        if self.is_scored and self.is_head_judged and time() >= self.end_time + input_offset():
            self.finish()
            return
        update_hold_glow(self.glow, self.is_glowing, self.head_judgment, layout_hold_effect(self.button))
        draw_hold(self.kind, self.button, self.start_time, self.target_time, self.end_time, self.hold_state)

    def finish(self):
        final = self.head_judgment
        if self.hold_input_interval.length > 0:
            if self.hold_state == HoldState.RELEASED or (
                self.hold_state == HoldState.DEFAULT
                and self.head_judgment == ArcadeJudgment.MISS
            ):
                self.release_time += delta_time()

            held = self.hold_input_interval.length
            percent = clamp((held - self.release_time) / held, 0, 1)
            final = buckets.hold_end_judge(self.head_judgment, percent)
        elif self.head_judgment == ArcadeJudgment.MISS and self.held_at_head:
            # Judged like a longer hold held all the way, so a missed head still gives a Good.
            final = buckets.hold_end_judge(self.head_judgment, 1)

        self.result.judgment = buckets.arcade_judgement_to_normal(final)
        self.result.accuracy = self.head_error
        if self.head_judgment == ArcadeJudgment.MISS:
            self.result.bucket = Bucket(-1)
        elif self.result.bucket.id != -1:
            self.result.bucket_value = self.head_bucket_value
        self.emit_end_sfx(final, time(), scheduled=False)
        self.judgment = final

    @property
    def is_glowing(self) -> bool:
        """Held after the head is judged (the release grace included)."""
        return self.is_scored and self.is_head_judged and (
            self.hold_state == HoldState.PRESSED or self.hold_state == HoldState.RELEASED_GRACE
        )

    def terminate(self):
        destroy_hold_glow(self.glow)
        if self.is_scored and self.is_judged:
            self.play_end_effects()

    def play_end_effects(self):
        spawn_tap_effect(is_break_hold(self.kind), self.judgment, layout_tap_effect(self.button))
        spawn_firework(self.firework, self.judgment, layout_button_firework_center(self.button))
        spawn_judge_text(
            self.judgment,
            is_break_hold(self.kind),
            self.head_error,
            button_slot(self.button),
            layout_button_judge_text(self.button),
        )


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
