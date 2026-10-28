from __future__ import annotations

from sonolus.script.archetype import EntityRef, PlayArchetype, entity_data, imported, shared_memory
from sonolus.script.array import Dim
from sonolus.script.containers import VarArray
from sonolus.script.globals import level_memory
from sonolus.script.interval import Interval

from minimai.lib.game import Button, Sensor


class ButtonBaseInput(PlayArchetype):
    button: Button = imported(default=1)

    target_time: float = entity_data()

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

    target_time: float = entity_data()

    input_interval: Interval = shared_memory()
    unadjusted_input_interval: Interval = shared_memory()

    # The id of the input that activated this note.
    # This is set by the input manager
    captured_touch_id: int = shared_memory()


@level_memory
class BaseInputMemory:
    # Rebuilt every frame: the notes waiting for an input this frame.
    active_tap_inputs: VarArray[EntityRef[ButtonBaseInput], Dim[256]]
    active_touch_inputs: VarArray[EntityRef[TouchBaseInput], Dim[256]]
