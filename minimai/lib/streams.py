from sonolus.script.array import Dim
from sonolus.script.record import Record
from sonolus.script.stream import Stream, StreamGroup, streams

from minimai.lib.game import Button, Sensor
from minimai.lib.hold import HoldState
from minimai.lib.scoring import ScoreSnapshot

# Exported by Initialization. Bump it when what play records changes meaning.
REPLAY_VERSION = 1

# State streams get their first entry here, so a lookup at any frame finds one.
STREAM_START_TIME = -100

# Sensor bit mask split boundary
# The split is required because 33 sensors can't fit in 24 bit mask of float
# In this case 16 flag split group A and B in low and C-E in high part
SENSOR_MASK_SPLIT = 16


class SensorMask(Record):
    """Sensors as bits by sensor - 1, in two parts so each stays an exact integer."""
    low: int
    high: int

    def add(self, sensor: Sensor):
        slot = sensor - 1
        if slot < SENSOR_MASK_SPLIT:
            bit = 2**slot
            if (self.low // bit) % 2 == 0:
                self.low += bit
        else:
            bit = 2 ** (slot - SENSOR_MASK_SPLIT)
            if (self.high // bit) % 2 == 0:
                self.high += bit

    def has(self, sensor: Sensor) -> bool:
        slot = sensor - 1
        result = False
        if slot < SENSOR_MASK_SPLIT:
            result = (self.low // 2**slot) % 2 == 1
        else:
            result = (self.high // 2 ** (slot - SENSOR_MASK_SPLIT)) % 2 == 1
        return result


class TouchFeedbackEvents(Record):
    """One frame's touch feedback changes. A button uses its A sensor.
    Sensors value are the chart's sensor not a mirrored version of the chart."""
    # Presses past the cooldown, before the Touch Feedback option.
    started: SensorMask
    # A note took a press there: the feedback stops.
    hit: SensorMask


class InputSnapshot(Record):
    # Bits by button - 1. Ex: 101 mean button 1 and 3 is on
    buttons: int
    # Sensors down within the touch radius, and within the note radius.
    touch: SensorMask
    note: SensorMask

    def add_button(self, button: Button):
        bit = 2 ** (button - 1)
        if (self.buttons // bit) % 2 == 0:
            self.buttons += bit

    def has_button(self, button: Button) -> bool:
        return (self.buttons // 2 ** (button - 1)) % 2 == 1


@streams
class Streams:
    """Keyed by offset adjusted time. State streams are written when they change; events are
    written in the frames they happen."""
    score: Stream[ScoreSnapshot]
    touch_hold_riser: Stream[bool]
    touch_feedback: Stream[TouchFeedbackEvents]
    # Only with Record touch input; otherwise empty, which reads as nothing pressed.
    input: Stream[InputSnapshot]
    # By entity index: holds and touch holds.
    hold_states: StreamGroup[HoldState, Dim[1_000_000]]
    # By entity index: the path points a slide hides.
    slide_path_hidden: StreamGroup[int, Dim[1_000_000]]
