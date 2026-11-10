from __future__ import annotations
from typing import cast

from sonolus.script.archetype import StandardImport, entity_data, entity_memory, imported
from sonolus.script.bucket import Bucket, Judgment
from sonolus.script.particle import ParticleHandle
from sonolus.script.runtime import is_replay, is_skip, time
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names, buckets
from minimai.lib.effect import (
    emit_firework_sfx,
    emit_hold_end_sfx,
    emit_tap_sfx,
    is_hit,
    report_note_time,
    schedule_guide_sfx,
)
from minimai.lib.firework import spawn_firework
from minimai.lib.game import ArcadeJudgment, apply_button_mirror_option
from minimai.lib.hold import HoldKind, HoldState, draw_hold, is_break_hold, is_ex_hold
from minimai.lib.initialization import init_common
from minimai.lib.judge_text import button_slot, spawn_judge_text
from minimai.lib.layout import (
    layout_button_firework_center,
    layout_button_judge_text,
    layout_hold_effect,
    layout_tap_effect,
)
from minimai.lib.note import get_tap_appear_duration
from minimai.lib.options import Options
from minimai.lib.particle import destroy_hold_glow, spawn_tap_effect, update_hold_glow
from minimai.lib.scoring import BaseWeight, add_note_to_total
from minimai.lib.streams import Streams
from minimai.watch.base import WatchButtonBase


class WatchBaseHold(WatchButtonBase):
    beat: StandardImport.BEAT
    speed: float = imported(default=1)
    # Beats from the head to the end. 0 = the hold ends with its head.
    hold_duration: float = imported(name="holdDuration", default=0)

    # From the replay. Without one, critical perfects at the head and end times.
    head_judged_time: float = imported(name="headJudgedTime")
    head_arcade_judgment: ArcadeJudgment = imported(name="headArcadeJudgment")
    judged_time: float = imported(name="judgedTime")
    arcade_judgment: ArcadeJudgment = imported(name="arcadeJudgment")
    standard_judgment: StandardImport.JUDGMENT
    accuracy: StandardImport.ACCURACY

    kind: HoldKind = entity_data()
    end_time: float = entity_data()

    glow: ParticleHandle = entity_memory()

    @classmethod
    def score_weight(cls) -> float:
        return BaseWeight.HOLD

    def preprocess(self):
        init_common()
        self.kind = cast(HoldKind, self.key)
        self.result.bucket = buckets.get_hold_bucket(self.kind)
        self.button = apply_button_mirror_option(self.button)

        self.target_time = beat_to_time(self.beat)
        self.end_time = beat_to_time(self.beat + max(self.hold_duration, 0))
        self.start_time = self.target_time - get_tap_appear_duration(self.speed)
        self.is_hold = True

        self.exit_time = self.end_time
        if not self.is_scored:
            return
        report_note_time(self.target_time)
        add_note_to_total(self.score_weight(), is_break_hold(self.kind))
        self.result.target_time = self.target_time
        if not is_replay():
            self.head_arcade_judgment = ArcadeJudgment.CRITICAL_PERFECT
            self.head_judged_time = self.target_time
            self.arcade_judgment = ArcadeJudgment.CRITICAL_PERFECT
            self.judged_time = self.end_time
            self.standard_judgment = Judgment.PERFECT
        if not is_hit(self.head_arcade_judgment):
            self.result.bucket = Bucket(-1)
        elif self.result.bucket.id != -1:
            self.result.bucket_value = self.accuracy * buckets.WINDOW_SCALE

        if self.arcade_judgment == ArcadeJudgment.NONE:
            # Not finished in the replay: gone when it would have been.
            self.exit_time = max(self.end_time, self.target_time + self.judgment_window.good.end)
        else:
            self.exit_time = self.judged_time
        if self.head_arcade_judgment == ArcadeJudgment.NONE:
            return
        schedule_guide_sfx(self.target_time)
        if self.end_time - self.target_time >= 1 / 60:
            schedule_guide_sfx(self.end_time)
        if Options.auto_sfx:
            self.emit_head_sfx(ArcadeJudgment.CRITICAL_PERFECT, self.target_time)
            self.emit_end_sfx(ArcadeJudgment.CRITICAL_PERFECT, self.end_time)
        else:
            self.emit_head_sfx(self.head_arcade_judgment, self.head_judged_time)
            self.emit_end_sfx(self.arcade_judgment, self.judged_time)
        self.spawn_effects()

    def spawn_time(self) -> float:
        return self.start_time

    def despawn_time(self) -> float:
        return self.exit_time

    def spawn_effects(self):
        if Options.hold_head_judge:
            spawn_judge_text(
                self.head_arcade_judgment,
                is_break_hold(self.kind),
                self.accuracy,
                button_slot(self.button),
                layout_button_judge_text(self.button),
                self.head_judged_time,
            )
        if self.arcade_judgment == ArcadeJudgment.NONE:
            return
        spawn_firework(
            self.firework, self.arcade_judgment, layout_button_firework_center(self.button), self.judged_time
        )
        spawn_judge_text(
            self.arcade_judgment,
            is_break_hold(self.kind),
            self.accuracy,
            button_slot(self.button),
            layout_button_judge_text(self.button),
            self.judged_time,
        )

    def update_parallel(self):
        hold_state = self.hold_state
        # After a seek, the looped glow starts over.
        if is_skip():
            destroy_hold_glow(self.glow)
        update_hold_glow(
            self.glow, self.is_glowing(hold_state), self.head_arcade_judgment, layout_hold_effect(self.button)
        )
        draw_hold(self.kind, self.button, self.start_time, self.target_time, self.end_time, hold_state)

    def is_glowing(self, hold_state: HoldState) -> bool:
        """Held after the head is judged (the release grace included)."""
        return (
            self.is_scored
            and self.head_arcade_judgment != ArcadeJudgment.NONE
            and time() >= self.head_judged_time
            and (hold_state == HoldState.PRESSED or hold_state == HoldState.RELEASED_GRACE)
        )

    def terminate(self):
        destroy_hold_glow(self.glow)
        # Not when a seek despawns it.
        if self.is_scored and not is_skip():
            spawn_tap_effect(is_break_hold(self.kind), self.arcade_judgment, layout_tap_effect(self.button))

    @property
    def hold_state(self) -> HoldState:
        result = HoldState.DEFAULT
        if is_replay():
            result = Streams.hold_states[self.index].get_previous_inclusive(time())
        elif self.is_scored and time() >= self.target_time:
            result = HoldState.PRESSED
        return result

    def emit_head_sfx(self, judgment: ArcadeJudgment, at: float):
        emit_tap_sfx(is_break_hold(self.kind), is_ex_hold(self.kind), judgment, at, scheduled=True)

    def emit_end_sfx(self, judgment: ArcadeJudgment, at: float):
        emit_hold_end_sfx(judgment, at, scheduled=True)
        emit_firework_sfx(self.firework, judgment, at, scheduled=True)

    @property
    def judgment_window(self):
        return buckets.NOTE_WINDOW


WatchNormalHoldNote = WatchBaseHold.derive(archetype_names.NORMAL_HOLD_NOTE, is_scored=True, key=HoldKind.NORM_HOLD)
WatchExHoldNote = WatchBaseHold.derive(archetype_names.EX_HOLD_NOTE, is_scored=True, key=HoldKind.EX_HOLD)
WatchEachHoldNote = WatchBaseHold.derive(archetype_names.EACH_HOLD_NOTE, is_scored=True, key=HoldKind.EACH_HOLD)
WatchExEachHoldNote = WatchBaseHold.derive(archetype_names.EX_EACH_HOLD_NOTE, is_scored=True, key=HoldKind.EX_EACH_HOLD)
WatchBreakHoldNote = WatchBaseHold.derive(archetype_names.BREAK_HOLD_NOTE, is_scored=True, key=HoldKind.BREAK_HOLD)
WatchExBreakHoldNote = WatchBaseHold.derive(archetype_names.EX_BREAK_HOLD_NOTE, is_scored=True, key=HoldKind.EX_BREAK_HOLD)

WATCH_HOLD_ARCHETYPES = (
    WatchNormalHoldNote,
    WatchExHoldNote,
    WatchEachHoldNote,
    WatchExEachHoldNote,
    WatchBreakHoldNote,
    WatchExBreakHoldNote,
)
