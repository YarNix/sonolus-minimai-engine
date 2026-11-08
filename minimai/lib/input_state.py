from minimai.lib.game import Sensor

from sonolus.script.array import Array, Dim
from sonolus.script.containers import ArrayMap, ArraySet, Pair, VarArray
from sonolus.script.globals import level_memory


@level_memory
class InputState:
    # Whether a button is being held down, store the id of the touch
    button_down: Array[int, Dim[8]]
    button_started: Array[bool, Dim[8]]
    # disallowed_release_touches: ArrayMap[int, float, Dim[32]]

    processing_sensor_touch: VarArray[Pair[int, Sensor], Dim[32]]
    sensor_touch_active: ArrayMap[int, ArraySet[Sensor, Dim[8]], Dim[16]]
    sensor_touch_started: Array[bool, Dim[33]]
    sensor_touch_down: Array[bool, Dim[33]]
    sensor_touch_ended: Array[bool, Dim[33]]

    # The same, with the note radius. Read by taps, holds and slides.
    processing_sensor_note: VarArray[Pair[int, Sensor], Dim[32]]
    sensor_note_active: ArrayMap[int, ArraySet[Sensor, Dim[8]], Dim[16]]
    sensor_note_started: Array[bool, Dim[33]]
    sensor_note_down: Array[bool, Dim[33]]
    sensor_note_ended: Array[bool, Dim[33]]