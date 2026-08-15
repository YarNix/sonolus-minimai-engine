from enum import IntEnum, auto
from math import atan, ceil, cos, floor, log, pi, sin, e
from typing import assert_never

from sonolus.script.globals import level_data
from sonolus.script.runtime import screen
from sonolus.script.quad import Quad, Rect
from sonolus.script.vec import Vec2
from sonolus.script.array import Array, Dim
from sonolus.script.record import Record
from sonolus.script.interval import Interval, lerp, lerp_clamped, unlerp, clamp, remap, unlerp_clamped
from sonolus.script.debug import assert_true, debug_log

from minimai.lib.options import Options

Button = int

class Sensor(IntEnum):
    N0 = 0 # Not assigned / Invalid / None
    A1 = auto()
    A2 = auto()
    A3 = auto()
    A4 = auto()
    A5 = auto()
    A6 = auto()
    A7 = auto()
    A8 = auto()
    B1 = auto()
    B2 = auto()
    B3 = auto()
    B4 = auto()
    B5 = auto()
    B6 = auto()
    B7 = auto()
    B8 = auto()
    C = auto()
    D1 = auto()
    D2 = auto()
    D3 = auto()
    D4 = auto()
    D5 = auto()
    D6 = auto()
    D7 = auto()
    D8 = auto()
    E1 = auto()
    E2 = auto()
    E3 = auto()
    E4 = auto()
    E5 = auto()
    E6 = auto()
    E7 = auto()
    E8 = auto()

class SensorGroup(IntEnum):
    N = 0 # Not assigned / Invalid / None
    A = auto()
    B = auto()
    C = auto()
    D = auto()
    E = auto()

def sensor_to_group(sensor: Sensor):
   match sensor:
        case Sensor.N0:
            return SensorGroup.N
        case (
            Sensor.A1 | Sensor.A2 | Sensor.A3 | Sensor.A4 |
            Sensor.A5 | Sensor.A6 | Sensor.A7 | Sensor.A8
        ):
            return SensorGroup.A
        case (
            Sensor.B1 | Sensor.B2 | Sensor.B3 | Sensor.B4 |
            Sensor.B5 | Sensor.B6 | Sensor.B7 | Sensor.B8
        ):
            return SensorGroup.B
        case Sensor.C:
            return SensorGroup.C
        case (
            Sensor.D1 | Sensor.D2 | Sensor.D3 | Sensor.D4 |
            Sensor.D5 | Sensor.D6 | Sensor.D7 | Sensor.D8
        ):
            return SensorGroup.D
        case (
            Sensor.E1 | Sensor.E2 | Sensor.E3 | Sensor.E4 |
            Sensor.E5 | Sensor.E6 | Sensor.E7 | Sensor.E8
        ):
            return SensorGroup.E
        case _:
            assert_never(sensor)

def get_button_range():
    return range(1, 9)

def get_button_iterator():
    return enumerate(get_button_range())

SENSOR_COUNT = Sensor.E8 - Sensor.N0 # 33

def get_sensor_iterator():
    return enumerate(s for s in Sensor if s is not Sensor.N0)

@level_data
class Layout:
    field_w: float
    field_h: float
    ring_center: Vec2
    # Distance from center to where the judgment/ring reside
    ring_distance: float
    button_distance: float

 # Base distance from center to the judgment ring in the texture
JUDGEMENT_DISTANCE = 0.9725
BUTTON_DISTANCE = 1.1

DISTANCE_SCALING = 1.225
DISTANCE_END = 4.8
DISTANCE_TRAVEL = DISTANCE_END - DISTANCE_SCALING
TOUCH_DISTANCE_START = 0.105
TOUCH_DISTANCE_END = 0.041

NOTE_SCALE_RATE = 0.265
NOTE_BASE_SIZE = 0.335
LINE_BASE_SIZE = 1.095
TOUCH_DOT_BASE_SIZE = 0.0665
TOUCH_FAN_BASE_SIZE = Vec2(112, 82) / 112 * 0.22

TRAVEL_DISTANCE_PROGRESS = DISTANCE_SCALING / DISTANCE_END
NOTE_END_SCALING_PROGRESS = 1 / (DISTANCE_TRAVEL * NOTE_SCALE_RATE + 1)
TOUCH_END_SCALING_PROGGRESS = 0.2

def init_layout():
    Layout.field_w = screen().w
    Layout.field_h = screen().h
    Layout.ring_distance = JUDGEMENT_DISTANCE * Options.ring_size
    Layout.button_distance = BUTTON_DISTANCE * Options.ring_size
    # Change this when it's time to add orientation
    Layout.ring_center = Vec2(0, Options.ring_offset)

def wrap_pi(angle: float):
    return (angle + pi) % (2 * pi) - pi

def get_button_angle_horizontal(button: Button):
    # 8 buttons
    # each offset by 45 degrees (2 pi / 8)
    # the starting button is offset by 5 pi / 8
    angle = (-2.0 * button + 5.0) * pi / 8
    return wrap_pi(angle)

def get_button_angle_vertical(button: Button):
    angle = (-2.0 * button + 1.0) * pi / 8
    return wrap_pi(angle)

def get_sensor_angle_horizontal(sensor: Sensor):
    group = sensor_to_group(sensor)
    match group:
        case SensorGroup.A:
            offset = sensor - Sensor.A1
        case SensorGroup.B:
            offset = sensor - Sensor.B1
        case SensorGroup.C:
            return 0.0
        case SensorGroup.D:
            offset = sensor - Sensor.D1
        case SensorGroup.E:
            offset = sensor - Sensor.E1
        case _:
            assert_never(group)
    match group:
        case SensorGroup.A | SensorGroup.B:
            angle = (-2.0 * offset + 3.0) * pi / 8
        case SensorGroup.D | SensorGroup.E:
            angle = (-2.0 * offset + 4.0) * pi / 8
        case _:
            assert_never(group)
    return wrap_pi(angle)


def get_pos_from_center(angle: float, distance: float) -> Vec2:
    return Layout.ring_center + Vec2(distance * cos(angle), distance * sin(angle))

def get_sensor_group_dist_from_center(group: SensorGroup):
    match group:
        case SensorGroup.A:
            return 4 / DISTANCE_END * Layout.ring_distance
        case SensorGroup.B:
            return 2.2 / DISTANCE_END * Layout.ring_distance
        case SensorGroup.C:
            return 0.0
        case SensorGroup.D:
            return 4.1 / DISTANCE_END * Layout.ring_distance
        case SensorGroup.E:
            return 3.1 / DISTANCE_END * Layout.ring_distance
        case _:
            assert_never(group)

def get_sensor_pos_from_center(sensor: Sensor):
    group = sensor_to_group(sensor)
    distance = get_sensor_group_dist_from_center(group)
    angle = get_sensor_angle_horizontal(sensor)
    return get_pos_from_center(angle, distance)

def get_dist_from_center(pos: Vec2):
    return (pos - Layout.ring_center).magnitude

def layout_ring():
    return Rect.from_center(
        Layout.ring_center, 
        Vec2(Layout.field_h * Options.ring_size, Layout.field_h * Options.ring_size)
    ).as_quad()

def layout_note(progress: float, button: Button):
    note_size = NOTE_BASE_SIZE * Options.note_scale
    pos = TRAVEL_DISTANCE_PROGRESS
    if progress <= NOTE_END_SCALING_PROGRESS:
        note_size = note_size * clamp(unlerp(0, NOTE_END_SCALING_PROGRESS, progress), 1e-4, 1)
    else:
        pos = remap(NOTE_END_SCALING_PROGRESS, 1, pos, 1, progress)
    center = get_pos_from_center(get_button_angle_horizontal(button), pos * Layout.ring_distance)
    dimensions = Vec2(note_size, note_size)
    layout = Rect.from_center(center, dimensions).as_quad()
    return layout

def layout_line(progress: float):
    line_size = Layout.field_h * Options.ring_size * LINE_BASE_SIZE
    if progress <= NOTE_END_SCALING_PROGRESS:
        line_size = line_size * TRAVEL_DISTANCE_PROGRESS
    else:
        line_size = line_size * remap(NOTE_END_SCALING_PROGRESS, 1, TRAVEL_DISTANCE_PROGRESS, 1, progress)
    dimensions = Vec2(line_size, line_size)
    layout = Rect.from_center(Layout.ring_center, dimensions).as_quad()
    return layout

def get_line_alpha(progress: float):
    return unlerp_clamped(0, NOTE_END_SCALING_PROGRESS, progress)

class TouchLayoutGroup(Record):
    dot: Quad
    bottom_fan: Quad
    border: Quad

    @property
    def left_fan(self):
        return self.bottom_fan.rotate_about(-pi / 2, pivot=self.dot.center)

    @property
    def top_fan(self):
        return self.bottom_fan.rotate_about(pi, pivot=self.dot.center)

    @property
    def right_fan(self):
        return self.bottom_fan.rotate_about(pi / 2, pivot=self.dot.center)

def layout_touch(progress: float, sensor: Sensor):
    pos = get_sensor_pos_from_center(sensor)

    dot_size = TOUCH_DOT_BASE_SIZE * Options.touch_scale
    dot_rect = Rect.from_center(pos, Vec2(dot_size, dot_size))

    dist_progress = unlerp_clamped(0.4, 0, 0.42 - e ** (4.3 * progress - 5.15))
    fan_dist = lerp(TOUCH_DISTANCE_START, TOUCH_DISTANCE_END, dist_progress) * Options.touch_scale
    fan_size = TOUCH_FAN_BASE_SIZE * Options.touch_scale
    fan_rect = Rect.from_center(pos + Vec2(0, -fan_dist), fan_size)

    return TouchLayoutGroup(
        dot=dot_rect.as_quad(),
        bottom_fan=fan_rect.as_quad(),
        border=dot_rect.scale_centered(Vec2(4, 4)).as_quad(),
    )

def get_touch_fan_alpha(progress: float):
    return unlerp_clamped(0, TOUCH_END_SCALING_PROGGRESS, progress)