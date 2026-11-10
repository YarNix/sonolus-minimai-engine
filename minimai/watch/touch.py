from __future__ import annotations
from typing import cast

from sonolus.script.archetype import StandardImport, WatchArchetype, entity_data, imported
from sonolus.script.bucket import Bucket, Judgment
from sonolus.script.runtime import is_replay
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names, buckets
from minimai.lib.effect import emit_firework_sfx, emit_touch_sfx, is_hit, report_note_time, schedule_guide_sfx
from minimai.lib.game import ArcadeJudgment, Sensor, apply_sensor_mirror_option
from minimai.lib.initialization import init_common
from minimai.lib.options import Options
from minimai.lib.scoring import BaseWeight, add_note_to_total
from minimai.lib.touch import TouchKind, draw_touch, get_touch_appear_duration, is_break_touch
from minimai.lib.touch_overlap import register_touch_overlap


class WatchBaseTouch(WatchArchetype):
    sensor: Sensor = imported()
    firework: bool = imported(default=False)
    beat: StandardImport.BEAT
    speed: float = imported(default=1)

    # From the replay. Without one, a critical perfect at the target time.
    judged_time: float = imported(name="judgedTime")
    arcade_judgment: ArcadeJudgment = imported(name="arcadeJudgment")
    standard_judgment: StandardImport.JUDGMENT
    accuracy: StandardImport.ACCURACY

    kind: TouchKind = entity_data()
    start_time: float = entity_data()
    target_time: float = entity_data()
    exit_time: float = entity_data()

    @classmethod
    def score_weight(cls) -> float:
        return BaseWeight.TAP

    def preprocess(self):
        init_common()
        self.kind = cast(TouchKind, self.key)
        self.result.bucket = buckets.get_touch_bucket(self.kind)

        self.sensor = apply_sensor_mirror_option(self.sensor)

        self.target_time = beat_to_time(self.beat)
        self.start_time = self.target_time - get_touch_appear_duration(self.speed)

        self.exit_time = self.target_time
        if not self.is_scored:
            return
        report_note_time(self.target_time)
        add_note_to_total(self.score_weight(), is_break_touch(self.kind))
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

    def update_sequential(self):
        register_touch_overlap(self.sensor, self.start_time, self.index, self.kind)

    def update_parallel(self):
        draw_touch(self.kind, self.sensor, self.start_time, self.target_time)

    def emit_hit_sfx(self, judgment: ArcadeJudgment, at: float):
        emit_touch_sfx(is_break_touch(self.kind), judgment, at, scheduled=True)
        emit_firework_sfx(self.firework, judgment, at, scheduled=True)

    @property
    def judgment_window(self):
        return buckets.TOUCH_WINDOW


WatchNormalTouchNote = WatchBaseTouch.derive(archetype_names.NORMAL_TOUCH_NOTE, is_scored=True, key=TouchKind.NORM_TOUCH)
WatchExTouchNote = WatchBaseTouch.derive(archetype_names.EX_TOUCH_NOTE, is_scored=True, key=TouchKind.EX_TOUCH)
WatchBreakTouchNote = WatchBaseTouch.derive(archetype_names.BREAK_TOUCH_NOTE, is_scored=True, key=TouchKind.BREAK_TOUCH)
WatchExBreakTouchNote = WatchBaseTouch.derive(archetype_names.EX_BREAK_TOUCH_NOTE, is_scored=True, key=TouchKind.EX_BREAK_TOUCH)
WatchEachTouchNote = WatchBaseTouch.derive(archetype_names.EACH_TOUCH_NOTE, is_scored=True, key=TouchKind.EACH_TOUCH)
WatchExEachTouchNote = WatchBaseTouch.derive(archetype_names.EX_EACH_TOUCH_NOTE, is_scored=True, key=TouchKind.EX_EACH_TOUCH)

WATCH_TOUCH_ARCHETYPES = (
    WatchNormalTouchNote,
    WatchExTouchNote,
    WatchBreakTouchNote,
    WatchExBreakTouchNote,
    WatchEachTouchNote,
    WatchExEachTouchNote,
)
