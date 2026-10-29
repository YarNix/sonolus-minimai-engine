from __future__ import annotations

from sonolus.script.archetype import EntityRef, PlayArchetype, entity_data, imported, shared_memory
from sonolus.script.array import Dim
from sonolus.script.containers import VarArray
from sonolus.script.globals import level_memory
from sonolus.script.interval import Interval

from minimai.lib import buckets
from minimai.lib.game import Button, Sensor


class ButtonBaseInput(PlayArchetype):
    button: Button = imported(default=1)

    target_time: float = entity_data()
    # When the note appears (each lines appear with it).
    start_time: float = entity_data()
    # Holds stop at the ring; taps and stars keep going when late.
    is_hold: bool = entity_data()

    input_interval: Interval = shared_memory()
    unadjusted_input_interval: Interval = shared_memory()

    # The id of the input that activated this note.
    # This is set by the input manager rather than the note itself.
    captured_touch_id: int = shared_memory()

    @property
    def sensor(self) -> Sensor:
        return Sensor.A1 + (self.button - 1)


class TouchBaseInput(PlayArchetype):
    sensor: Sensor = imported()
    # Touch group: the touches and touch holds at the same time on neighbouring sensors.
    # Every member refers to the same leader (the first member, itself included); 0 = no group.
    group_leader: EntityRef[TouchBaseInput] = imported(name="group")
    group_size: int = imported(name="groupSize", default=0)

    target_time: float = entity_data()

    input_interval: Interval = shared_memory()
    unadjusted_input_interval: Interval = shared_memory()

    # The id of the input that activated this note.
    # This is set by the input manager
    captured_touch_id: int = shared_memory()

    # Group state, kept on the leader: members hit (not missed), and the judgment and error
    # the rest take over once more than half the group is hit.
    group_hit_count: int = shared_memory()
    group_judgment: buckets.ArcadeJudgment = shared_memory()
    group_error: float = shared_memory()

    @property
    def in_group(self) -> bool:
        return self.group_leader.index > 0

    def register_group_hit(self, judgment: buckets.ArcadeJudgment, error: float):
        """A member was hit (sequential callbacks only). The judgment counts until the group passes
        half; the member that takes it past half sets what the rest get."""
        if not self.in_group or judgment == buckets.ArcadeJudgment.MISS:
            return
        leader = self.group_leader.get()
        if leader.group_hit_count * 2 <= self.group_size:
            leader.group_judgment = judgment
            leader.group_error = error
        leader.group_hit_count += 1

    @property
    def is_group_judged(self) -> bool:
        """More than half the group is hit: the rest are judged like the last of those."""
        result = False
        if self.in_group:
            leader = self.group_leader.get()
            result = (
                leader.group_hit_count * 2 > self.group_size
                and leader.group_judgment != buckets.ArcadeJudgment.NONE
            )
        return result

    @property
    def group_result(self) -> buckets.ArcadeJudgment:
        return self.group_leader.get().group_judgment

    @property
    def group_result_error(self) -> float:
        return self.group_leader.get().group_error


@level_memory
class BaseInputMemory:
    # Rebuilt every frame: the notes waiting for an input this frame.
    active_tap_inputs: VarArray[EntityRef[ButtonBaseInput], Dim[256]]
    active_touch_inputs: VarArray[EntityRef[TouchBaseInput], Dim[256]]
