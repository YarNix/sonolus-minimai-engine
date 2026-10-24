from typing import cast

from sonolus.script.archetype import (
    AnyArchetype,
    EntityRef,
    PlayArchetype,
    StandardImport,
    entity_data,
    entity_memory,
    exported,
    imported,
    shared_memory,
)
from sonolus.script.interval import Interval
from sonolus.script.runtime import input_offset, time, touches
from sonolus.script.timing import beat_to_time
from sonolus.script.globals import level_memory
from sonolus.script.array import Dim
from sonolus.script.containers import VarArray
from sonolus.script.bucket import Bucket, Judgment

from minimai.lib import archetype_names, buckets
from minimai.lib.touch import TouchKind, draw_touch, get_touch_appear_duration
from minimai.lib.game import Sensor

class BaseTouch(PlayArchetype):
    beat: StandardImport.BEAT
    sensor: Sensor = imported()
    speed: float = imported(default=1)

    kind: TouchKind = entity_data()
    start_time: float = entity_data()
    target_time: float = entity_data()

    input_interval: Interval = shared_memory()
    unadjusted_input_interval: Interval = shared_memory()

    # The id of the input that activated this note.
    # This is set by the input manager rather than the note itself.
    captured_touch_id: int = shared_memory()

    def spawn_order(self) -> float:
        return self.start_time

    def should_spawn(self) -> bool:
        return time() >= self.start_time

    def preprocess(self):
        self.kind = cast(TouchKind, self.key)
        self.result.bucket = buckets.get_touch_bucket(self.kind)

        # Handle mirror options

        self.target_time = beat_to_time(self.beat)
        appear_time = get_touch_appear_duration(self.speed)
        self.start_time = self.target_time - appear_time

        self.input_interval = self.judgment_window.good + self.target_time + input_offset()
        self.unadjusted_input_interval = self.judgment_window.good + self.target_time

    def update_sequential(self):
        if self.despawn:
            return
        if self.is_scored and time() in self.input_interval: 
            # and self.captured_touch_id == 0:
            TouchMemory.active_touch_inputs.append(self.ref())

    def update_parallel(self):
        if self.despawn:
            return
        if not self.is_scored and time() >= self.target_time:
            self.despawn = True
            return
        if time() > self.input_interval.end:
            self.handle_miss()
        draw_touch(self.kind, self.sensor, self.start_time, self.target_time)

    def touch(self):
        if not self.is_scored:
            return
        if self.despawn:
            return
        if time() < self.input_interval.start:
            return
        self.handle_touch()

    def terminate(self):
        pass

    @property
    def judgment_window(self):
        return buckets.TOUCH_WINDOW

    def judge(self, actual_time: float):
        judgment = self.judgment_window.judge(actual_time, self.target_time)
        self.result.judgment = buckets.arcade_judgement_to_normal(judgment)
        self.result.accuracy = self.judgment_window.good.clamp(actual_time - self.target_time)
        if self.result.bucket.id != -1:
            self.result.bucket_value = self.result.accuracy * buckets.WINDOW_SCALE
        self.despawn = True

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
        self.despawn = True

@level_memory
class TouchMemory:
    active_touch_inputs: VarArray[EntityRef[BaseTouch], Dim[256]]

NormalTouchNote = BaseTouch.derive(archetype_names.NORMAL_TOUCH_NOTE, is_scored=True, key=TouchKind.NORM_TOUCH)
BreakTouchNote = BaseTouch.derive(archetype_names.BREAK_TOUCH_NOTE, is_scored=True, key=TouchKind.BREAK_TOUCH)
EachTouchNote = BaseTouch.derive(archetype_names.EACH_TOUCH_NOTE, is_scored=True, key=TouchKind.EACH_TOUCH)

TOUCH_ARCHETYPES = [
    NormalTouchNote,
    BreakTouchNote,
    EachTouchNote,
]
