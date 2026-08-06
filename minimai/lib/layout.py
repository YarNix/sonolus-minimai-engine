from math import atan, ceil, cos, floor, log, pi, sin

from sonolus.script.globals import level_data
from sonolus.script.runtime import screen
from sonolus.script.quad import Quad, Rect
from sonolus.script.vec import Vec2
from sonolus.script.array import Array, Dim
from sonolus.script.record import Record
from sonolus.script.interval import Interval, lerp, unlerp, clamp, remap, unlerp_clamped
from sonolus.script.debug import debug_log

from minimai.lib.options import Options

@level_data
class Layout:
    field_w: float
    field_h: float
    ring_center: Vec2
    # Distance from center to where the judgment/ring reside
    ring_distance: float

JUDGEMENT_DISTANCE = 0.9725
DISTANCE_SCALING = 1.225
DISTANCE_END = 4.8
DISTANCE_TRAVEL = DISTANCE_END - DISTANCE_SCALING

NOTE_SCALE_RATE = 0.265
NOTE_BASE_SIZE = 0.335
LINE_BASE_SIZE = 1.095
TRAVEL_DISTANCE_PROGRESS = DISTANCE_SCALING / DISTANCE_END
END_SCALING_PROGRESS = 1 / (DISTANCE_TRAVEL * NOTE_SCALE_RATE + 1)

def init_layout():
    Layout.field_w = screen().w
    Layout.field_h = screen().h
    Layout.ring_distance = JUDGEMENT_DISTANCE * Options.ring_size
    # Change this when it's time to add orientation
    Layout.ring_center = Vec2(0, Options.ring_offset)

def wrap_pi(angle: float):
    return (angle + pi) % (2 * pi) - pi

def angle_to_yaxis(rad: float):
    return rad - pi / 2

def get_button_iterator():
    return enumerate(range(1, 9))

def get_horizontal_angle(button: float):
    # 8 buttons
    # each offset by 45 degrees (2 pi / 8)
    # the starting button is offset by 5 pi / 8
    angle = (-2.0 * button + 5.0) * pi / 8
    return wrap_pi(angle)

def get_vertical_angle(button: float):
    angle = (-2.0 * button + 1.0) * pi / 8
    return wrap_pi(angle)

def get_pos_from_center(button: float, distance: float) -> Vec2:
    return Layout.ring_center + Vec2(
        distance * cos(get_horizontal_angle(button)),
        distance * sin(get_horizontal_angle(button))
    )

def get_dist_from_center(pos: Vec2):
    return (pos - Layout.ring_center).magnitude

def layout_ring():
    return Rect.from_center(
        Layout.ring_center, 
        Vec2(Layout.field_h * Options.ring_size, Layout.field_h * Options.ring_size)
    ).as_quad()

def layout_note(progress: float, button: float):
    note_size = NOTE_BASE_SIZE * Options.note_scale
    pos = TRAVEL_DISTANCE_PROGRESS
    if progress <= END_SCALING_PROGRESS:
        note_size = note_size * clamp(unlerp(0, END_SCALING_PROGRESS, progress), 1e-4, 1)
    else:
        pos = remap(END_SCALING_PROGRESS, 1, pos, 1, progress)
    center = get_pos_from_center(button, pos * Layout.ring_distance)
    dimensions = Vec2(note_size, note_size)
    layout = Rect.from_center(center, dimensions).as_quad()
    return layout

def layout_line(progress: float):
    line_size = Layout.field_h * Options.ring_size * LINE_BASE_SIZE
    if progress <= END_SCALING_PROGRESS:
        line_size = line_size * TRAVEL_DISTANCE_PROGRESS
    else:
        line_size = line_size * remap(END_SCALING_PROGRESS, 1, TRAVEL_DISTANCE_PROGRESS, 1, progress)
    dimensions = Vec2(line_size, line_size)
    layout = Rect.from_center(Layout.ring_center, dimensions).as_quad()
    return layout

def get_line_alpha(progress: float):
    return unlerp_clamped(0, END_SCALING_PROGRESS, progress)

class ButtonHitBox(Record):
    angle: Interval
    distance: Interval

    def contains_point(self, point: Vec2) -> bool:
        from_center = (point - Layout.ring_center)
        return from_center.magnitude in self.distance \
            and from_center.angle in self.angle

    @staticmethod
    def from_button(button: int, angle: float | None = None, distance: float | None = None):
        center_angle = get_horizontal_angle(button)
        center_distance = Layout.ring_distance
        if angle is None:
            angle = Options.button_angle * pi / 180
        if distance is None:
            distance = Options.button_size * Layout.ring_distance * 2
        return ButtonHitBox(
            angle=Interval(center_angle - angle / 2, center_angle + angle / 2),
            distance=Interval(center_distance - distance / 2, center_distance + distance / 2)
        )

@level_data
class Hitboxes:
    button: Array[ButtonHitBox, Dim[8]]

def init_hitboxes():
    for i, b in get_button_iterator():
        Hitboxes.button[i] = ButtonHitBox.from_button(b)

def is_in_input_region(point: Vec2):
    return get_dist_from_center(point) <= (Layout.ring_distance * (1 + Options.button_size))