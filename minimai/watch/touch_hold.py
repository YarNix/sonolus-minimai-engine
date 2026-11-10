from __future__ import annotations
from typing import cast

from sonolus.script.archetype import StandardImport, WatchArchetype, entity_data, imported
from sonolus.script.array import Dim
from sonolus.script.bucket import Bucket, Judgment
from sonolus.script.containers import VarArray
from sonolus.script.globals import level_memory
from sonolus.script.interval import Interval
from sonolus.script.runtime import is_replay, time
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names, buckets
from minimai.lib.effect import (
    emit_ex_sfx,
    emit_firework_sfx,
    emit_hold_end_sfx,
    is_hit,
    report_note_time,
    schedule_guide_sfx,
    schedule_touch_hold_riser,
)
from minimai.lib.game import ArcadeJudgment, Sensor, apply_sensor_mirror_option
from minimai.lib.hold import HoldState
from minimai.lib.initialization import init_common
from minimai.lib.options import Options
from minimai.lib.scoring import BaseWeight, add_note_to_total
from minimai.lib.streams import STREAM_START_TIME, Streams
from minimai.lib.touch import get_touch_appear_duration
from minimai.lib.touch_hold import TouchHoldKind, draw_touch_hold, is_break_touch_hold, is_ex_touch_hold


class WatchBaseTouchHold(WatchArchetype):
    sensor: Sensor = imported()
    firework: bool = imported(default=False)
    beat: StandardImport.BEAT
    speed: float = imported(default=1)
    # Beats from the head to the end. 0 = the touch hold ends with its head.
    hold_duration: float = imported(name="holdDuration", default=0)

    # From the replay. Without one, critical perfects at the head and end times.
    head_judged_time: float = imported(name="headJudgedTime")
    head_arcade_judgment: ArcadeJudgment = imported(name="headArcadeJudgment")
    judged_time: float = imported(name="judgedTime")
    arcade_judgment: ArcadeJudgment = imported(name="arcadeJudgment")
    standard_judgment: StandardImport.JUDGMENT
    accuracy: StandardImport.ACCURACY

    kind: TouchHoldKind = entity_data()
    start_time: float = entity_data()
    target_time: float = entity_data()
    end_time: float = entity_data()
    exit_time: float = entity_data()

    @classmethod
    def score_weight(cls) -> float:
        return BaseWeight.HOLD

    def preprocess(self):
        init_common()
        self.kind = cast(TouchHoldKind, self.key)
        self.result.bucket = buckets.get_touch_hold_bucket(self.kind)
        self.sensor = apply_sensor_mirror_option(self.sensor)

        self.target_time = beat_to_time(self.beat)
        self.end_time = beat_to_time(self.beat + max(self.hold_duration, 0))
        self.start_time = self.target_time - get_touch_appear_duration(self.speed)

        self.exit_time = self.end_time
        if not self.is_scored:
            return
        report_note_time(self.target_time)
        add_note_to_total(self.score_weight(), is_break_touch_hold(self.kind))
        self.result.target_time = self.target_time
        if not is_replay():
            self.head_arcade_judgment = ArcadeJudgment.CRITICAL_PERFECT
            self.head_judged_time = self.target_time
            self.arcade_judgment = ArcadeJudgment.CRITICAL_PERFECT
            self.judged_time = self.end_time
            self.standard_judgment = Judgment.PERFECT
            add_riser_period(self.target_time, self.end_time)
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
        # The head has no sound; the riser plays instead.
        if Options.auto_sfx:
            self.emit_end_sfx(ArcadeJudgment.CRITICAL_PERFECT, self.end_time)
        else:
            self.emit_end_sfx(self.arcade_judgment, self.judged_time)

    def spawn_time(self) -> float:
        return self.start_time

    def despawn_time(self) -> float:
        return self.exit_time

    def update_parallel(self):
        draw_touch_hold(self.kind, self.sensor, self.start_time, self.target_time, self.end_time, self.hold_state)

    @property
    def hold_state(self) -> HoldState:
        result = HoldState.DEFAULT
        if is_replay():
            result = Streams.hold_states[self.index].get_previous_inclusive(time())
        elif self.is_scored and time() >= self.target_time:
            result = HoldState.PRESSED
        return result

    def emit_end_sfx(self, judgment: ArcadeJudgment, at: float):
        if is_ex_touch_hold(self.kind):
            emit_ex_sfx(judgment, at, scheduled=True)
        else:
            emit_hold_end_sfx(judgment, at, scheduled=True)
        emit_firework_sfx(self.firework, judgment, at, scheduled=True)

    @property
    def judgment_window(self):
        return buckets.TOUCH_WINDOW


@level_memory
class RiserMemory:
    # Without a replay: when some touch hold wants the riser, kept merged where they overlap.
    periods: VarArray[Interval, Dim[64]]


def add_riser_period(start: float, end: float):
    """Preprocess, before ``schedule_riser``."""
    if end <= start:
        return
    for period in RiserMemory.periods:
        if start <= period.end and period.start <= end:
            period.start = min(period.start, start)
            period.end = max(period.end, end)
            return
    if RiserMemory.periods.is_full():
        schedule_touch_hold_riser(start, end)
    else:
        RiserMemory.periods.append(Interval(start, end))


def schedule_riser():
    """Preprocess, after every touch hold's: replayed from the recording, or the periods without a
    replay (merged again, since a period can grow into another)."""
    if is_replay():
        on = False
        start = 0.0
        for at, wanted in Streams.touch_hold_riser.iter_items_from(STREAM_START_TIME):
            if wanted and not on:
                start = at
            elif not wanted and on:
                schedule_touch_hold_riser(start, at)
            on = wanted
        if on:
            # The replay stopped with it on.
            schedule_touch_hold_riser(start, 1e8)
        return
    periods = RiserMemory.periods
    periods.sort(key=lambda period: period.start)
    if len(periods) == 0:
        return
    merged = +periods[0]
    for period in periods:
        if period.start <= merged.end:
            merged.end = max(merged.end, period.end)
        else:
            schedule_touch_hold_riser(merged.start, merged.end)
            merged @= period
    schedule_touch_hold_riser(merged.start, merged.end)


WatchNormalTouchHoldNote = WatchBaseTouchHold.derive(
    archetype_names.NORMAL_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.NORM_TOUCH_HOLD
)
WatchExTouchHoldNote = WatchBaseTouchHold.derive(
    archetype_names.EX_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.EX_TOUCH_HOLD
)
WatchEachTouchHoldNote = WatchBaseTouchHold.derive(
    archetype_names.EACH_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.EACH_TOUCH_HOLD
)
WatchExEachTouchHoldNote = WatchBaseTouchHold.derive(
    archetype_names.EX_EACH_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.EX_EACH_TOUCH_HOLD
)
WatchBreakTouchHoldNote = WatchBaseTouchHold.derive(
    archetype_names.BREAK_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.BREAK_TOUCH_HOLD
)
WatchExBreakTouchHoldNote = WatchBaseTouchHold.derive(
    archetype_names.EX_BREAK_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.EX_BREAK_TOUCH_HOLD
)

WATCH_TOUCH_HOLD_ARCHETYPES = (
    WatchNormalTouchHoldNote,
    WatchExTouchHoldNote,
    WatchEachTouchHoldNote,
    WatchExEachTouchHoldNote,
    WatchBreakTouchHoldNote,
    WatchExBreakTouchHoldNote,
)
