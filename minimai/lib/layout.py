from enum import IntEnum, auto
from math import atan2, ceil, cos, floor, log, pi, sin, sqrt, tan, e
from typing import assert_never

from sonolus.script.globals import level_data
from sonolus.script.runtime import screen
from sonolus.script.quad import Quad, Rect
from sonolus.script.vec import Vec2
from sonolus.script.array import Array, Dim
from sonolus.script.containers import VarArray
from sonolus.script.record import Record
from sonolus.script.interval import Interval, lerp, lerp_clamped, unlerp, clamp, remap, unlerp_clamped
from sonolus.script.debug import assert_true, debug_log

from minimai.lib.game import Button, MirrorMode, Sensor, SensorGroup, sensor_offset, sensor_to_group
from minimai.lib.options import Options

@level_data
class Layout:
    field_w: float
    field_h: float
    ring_center: Vec2
    # Judgment ring radius in screen units: ring units (0 = center, 1 = judgment ring) to screen.
    ring_radius: float


# The skin art is drawn for a judgment ring this many pixels in radius.
SKIN_RING_RADIUS_PX = 480


def from_skin_px(value: int | float | Vec2):
    """Skin (texture) pixels to ring units."""
    return value / SKIN_RING_RADIUS_PX


# All layout constants are in ring units (0 = center, 1 = judgment ring).

# The ring sprite (1024 px) has its judgment ring 498 px from the center.
RING_SPRITE_SIZE = 1024 / 498
# Where the button hitboxes start, just outside the ring.
BUTTON_DISTANCE = 1.131105

# Notes appear at the spawn distance, scale in, then travel to the ring.
NOTE_SPAWN_DISTANCE = from_skin_px(122.5)
# Scale grown per ring unit travelled (0.265 per 100 skin px).
NOTE_SCALE_RATE = 0.265 / from_skin_px(100)
NOTE_SIZE = from_skin_px(180)
LINE_SIZE = from_skin_px(1080)
EACH_LINE_SIZE = from_skin_px(980)

HOLD_WIDTH = from_skin_px(122)
HOLD_CAP_LENGTH = from_skin_px(58)
HOLD_BODY_MIN_LENGTH = from_skin_px(24)
HOLD_END_POINT_SIZE = from_skin_px(64)

TOUCH_POINT_SIZE = from_skin_px(32)
TOUCH_JUST_BORDER_SIZE = from_skin_px(128)
TOUCH_OVERLAP_BORDER_SIZE = from_skin_px(228)
TOUCH_FAN_SIZE = from_skin_px(Vec2(112, 82))
# Fan center from the point: the offset, plus the travel at the start of the approach.
TOUCH_FAN_OFFSET = from_skin_px(22.6)
TOUCH_FAN_TRAVEL = from_skin_px(40)
TOUCH_HOLD_BORDER_SIZE = from_skin_px(Vec2(211, 210))

SLIDE_PATH_SIZE = from_skin_px(Vec2(70, 94))
WIFI_SLIDE_PATH_SIZES = Array(*(from_skin_px(size) for size in (
    Vec2(111, 68),
    Vec2(160, 90),
    Vec2(204, 110),
    Vec2(253, 136),
    Vec2(298, 154),
    Vec2(353, 179),
    Vec2(410, 205),
    Vec2(464, 226),
    Vec2(519, 251),
    Vec2(571, 271),
    Vec2(653, 313),
)))

class SlideOkShape(IntEnum):
    CURVE = 0
    STRAIGHT = auto()
    WIFI = auto()

SLIDE_OK_SIZES = Array(*(from_skin_px(size) for size in (Vec2(410, 180), Vec2(428, 140), Vec2(668, 188))))
# A straight slide OK that turns around also moves this far down its own (turned) sprite.
SLIDE_OK_TURN_SHIFT = from_skin_px(27)

class SlideOkPose(Record):
    # Of the slide from button 1.
    position: Vec2
    rotation: float
    shape: SlideOkShape
    # A straight or Wi-Fi slide OK turns around on the right side, else on the left.
    turn_on_right: bool

def slide_ok_pose(x: float, y: float, degrees: float, shape: SlideOkShape, turn_on_right: bool) -> SlideOkPose:
    return SlideOkPose(from_skin_px(Vec2(x, y)), degrees * pi / 180, shape, turn_on_right)

# By track * 2 + is_mirrored, as the reference player places them: x, y (skin px), rotation (degrees).
SLIDE_OK_POSES = Array(*(slide_ok_pose(*pose) for pose in (
    (0, 0, 0, SlideOkShape.STRAIGHT, False),  # NONE
    (0, 0, 0, SlideOkShape.STRAIGHT, False),  # NONE mirrored
    (    4.4,   464.5,     0.00, SlideOkShape.CURVE, False),  # CIRCLE_1
    (  325.3,   331.6,   -45.00, SlideOkShape.CURVE, True ),  # CIRCLE_1 mirrored
    (  326.0,   326.0,   -45.00, SlideOkShape.CURVE, False),  # CIRCLE_2
    (   -0.0,   461.0,     0.00, SlideOkShape.CURVE, True ),  # CIRCLE_2 mirrored
    (  464.0,    -1.0,   -90.00, SlideOkShape.CURVE, False),  # CIRCLE_3
    ( -328.8,   327.4,    45.00, SlideOkShape.CURVE, True ),  # CIRCLE_3 mirrored
    (  325.0,  -330.0,  -135.00, SlideOkShape.CURVE, False),  # CIRCLE_4
    ( -463.2,    -3.5,    90.00, SlideOkShape.CURVE, True ),  # CIRCLE_4 mirrored
    (   -4.0,  -465.0,  -180.00, SlideOkShape.CURVE, False),  # CIRCLE_5
    ( -326.0,  -331.6,   135.00, SlideOkShape.CURVE, True ),  # CIRCLE_5 mirrored
    ( -331.0,  -324.0,   135.00, SlideOkShape.CURVE, False),  # CIRCLE_6
    (    4.9,  -463.2,  -180.00, SlideOkShape.CURVE, True ),  # CIRCLE_6 mirrored
    ( -462.0,     7.0,    90.00, SlideOkShape.CURVE, False),  # CIRCLE_7
    (  331.6,  -321.7,  -135.00, SlideOkShape.CURVE, True ),  # CIRCLE_7 mirrored
    ( -324.0,   329.0,    45.00, SlideOkShape.CURVE, False),  # CIRCLE_8
    (  461.7,     3.5,   -90.00, SlideOkShape.CURVE, True ),  # CIRCLE_8 mirrored
    (  345.0,    20.0,   -67.35, SlideOkShape.STRAIGHT, False),  # LINE_3
    ( -239.8,   275.2,  -157.06, SlideOkShape.STRAIGHT, False),  # LINE_3 mirrored
    (  170.0,  -243.0,   -90.00, SlideOkShape.STRAIGHT, False),  # LINE_4
    ( -312.0,   -32.0,  -135.00, SlideOkShape.STRAIGHT, False),  # LINE_4 mirrored
    ( -108.0,  -230.0,  -112.80, SlideOkShape.STRAIGHT, False),  # LINE_5
    ( -108.0,  -230.0,  -112.80, SlideOkShape.STRAIGHT, False),  # LINE_5 mirrored
    (  122.0,   263.0,    67.50, SlideOkShape.STRAIGHT, False),  # CENTER_1
    (  122.0,   263.0,    67.50, SlideOkShape.STRAIGHT, False),  # CENTER_1 mirrored
    (  237.0,    85.0,    23.03, SlideOkShape.STRAIGHT, False),  # CENTER_2
    (  -84.0,   235.0,   113.21, SlideOkShape.STRAIGHT, False),  # CENTER_2 mirrored
    (  231.0,  -115.0,   -21.37, SlideOkShape.STRAIGHT, False),  # CENTER_3
    ( -230.0,   111.0,   158.53, SlideOkShape.STRAIGHT, False),  # CENTER_3 mirrored
    (   92.0,  -245.0,   -67.28, SlideOkShape.STRAIGHT, False),  # CENTER_4
    ( -244.0,   -92.0,  -155.87, SlideOkShape.STRAIGHT, False),  # CENTER_4 mirrored
    (  197.5,   226.2,    90.00, SlideOkShape.STRAIGHT, False),  # LOOP_IN_1
    (   20.3,   299.5,  -135.00, SlideOkShape.STRAIGHT, True ),  # LOOP_IN_1 mirrored
    (  302.8,    25.2,    45.00, SlideOkShape.STRAIGHT, False),  # LOOP_IN_2
    ( -196.3,   231.9,   -90.00, SlideOkShape.STRAIGHT, True ),  # LOOP_IN_2 mirrored
    (  234.5,  -195.6,     0.00, SlideOkShape.STRAIGHT, False),  # LOOP_IN_3
    ( -304.1,    27.5,   -45.00, SlideOkShape.STRAIGHT, True ),  # LOOP_IN_3 mirrored
    (   29.7,  -306.5,   -45.00, SlideOkShape.STRAIGHT, False),  # LOOP_IN_4
    ( -237.7,  -195.7,     0.00, SlideOkShape.STRAIGHT, True ),  # LOOP_IN_4 mirrored
    ( -197.3,  -240.2,   -90.00, SlideOkShape.STRAIGHT, False),  # LOOP_IN_5
    (  -30.4,  -309.4,    45.00, SlideOkShape.STRAIGHT, True ),  # LOOP_IN_5 mirrored
    ( -292.1,   -14.7,  -135.00, SlideOkShape.STRAIGHT, False),  # LOOP_IN_6
    (  196.2,  -217.0,    90.00, SlideOkShape.STRAIGHT, True ),  # LOOP_IN_6 mirrored
    ( -221.9,   194.4,  -180.00, SlideOkShape.STRAIGHT, False),  # LOOP_IN_7
    (  294.3,   -19.4,   135.00, SlideOkShape.STRAIGHT, True ),  # LOOP_IN_7 mirrored
    (  -20.3,   298.3,   135.34, SlideOkShape.STRAIGHT, False),  # LOOP_IN_8
    (  225.3,   196.6,   179.66, SlideOkShape.STRAIGHT, True ),  # LOOP_IN_8 mirrored
    (  319.0,   262.0,   123.46, SlideOkShape.STRAIGHT, False),  # LOOP_OUT_1
    (  -40.3,   410.8,  -168.46, SlideOkShape.STRAIGHT, True ),  # LOOP_OUT_1 mirrored
    (  456.4,   -34.4,    89.33, SlideOkShape.STRAIGHT, False),  # LOOP_OUT_2
    ( -347.0,   298.4,  -134.33, SlideOkShape.STRAIGHT, True ),  # LOOP_OUT_2 mirrored
    (  259.0,  -231.0,    10.68, SlideOkShape.STRAIGHT, False),  # LOOP_OUT_3
    ( -346.5,    19.8,   -55.68, SlideOkShape.STRAIGHT, True ),  # LOOP_OUT_3 mirrored
    (   79.0,  -247.0,   -66.12, SlideOkShape.STRAIGHT, False),  # LOOP_OUT_4
    ( -230.5,  -118.8,    21.12, SlideOkShape.STRAIGHT, True ),  # LOOP_OUT_4 mirrored
    ( -121.0,  -236.0,  -110.11, SlideOkShape.STRAIGHT, False),  # LOOP_OUT_5
    (  -81.3,  -252.4,    65.11, SlideOkShape.STRAIGHT, True ),  # LOOP_OUT_5 mirrored
    ( -265.7,   -51.3,  -145.83, SlideOkShape.STRAIGHT, False),  # LOOP_OUT_6
    (  151.6,  -224.2,   100.83, SlideOkShape.STRAIGHT, True ),  # LOOP_OUT_6 mirrored
    ( -247.2,   205.5,  -177.35, SlideOkShape.STRAIGHT, False),  # LOOP_OUT_7
    (  320.1,   -29.5,   132.35, SlideOkShape.STRAIGHT, True ),  # LOOP_OUT_7 mirrored
    (   22.2,   354.7,   154.02, SlideOkShape.STRAIGHT, False),  # LOOP_OUT_8
    (  235.1,   266.5,   160.98, SlideOkShape.STRAIGHT, True ),  # LOOP_OUT_8 mirrored
    (  225.1,   172.9,     0.00, SlideOkShape.STRAIGHT, False),  # REFLECT_2
    (  -36.9,   281.4,   -45.00, SlideOkShape.STRAIGHT, True ),  # REFLECT_2 mirrored
    (  254.3,  -118.8,   -22.71, SlideOkShape.STRAIGHT, False),  # REFLECT_3
    ( -263.8,    95.8,   -22.29, SlideOkShape.STRAIGHT, True ),  # REFLECT_3 mirrored
    (   21.9,  -297.1,   -45.25, SlideOkShape.STRAIGHT, False),  # REFLECT_4
    ( -225.5,  -194.6,     0.25, SlideOkShape.STRAIGHT, True ),  # REFLECT_4 mirrored
    ( -271.1,  -261.2,   -68.29, SlideOkShape.STRAIGHT, False),  # REFLECT_5
    (    7.0,  -376.4,    23.29, SlideOkShape.STRAIGHT, True ),  # REFLECT_5 mirrored
    (  -61.0,  -303.0,  -134.39, SlideOkShape.STRAIGHT, False),  # ZIG_ZAG
    ( -171.1,  -257.4,    89.39, SlideOkShape.STRAIGHT, True ),  # ZIG_ZAG mirrored
    ( -161.0,  -387.0,   157.43, SlideOkShape.WIFI, False),  # FAN
    ( -161.0,  -387.0,   157.43, SlideOkShape.WIFI, False),  # FAN mirrored
    (0, 0, 0, SlideOkShape.STRAIGHT, False),  # FAN_L
    (0, 0, 0, SlideOkShape.STRAIGHT, False),  # FAN_L mirrored
    (0, 0, 0, SlideOkShape.STRAIGHT, False),  # FAN_C
    (0, 0, 0, SlideOkShape.STRAIGHT, False),  # FAN_C mirrored
    (0, 0, 0, SlideOkShape.STRAIGHT, False),  # FAN_R
    (0, 0, 0, SlideOkShape.STRAIGHT, False),  # FAN_R mirrored
)))

# Effects
TAP_EFFECT_SIZE = from_skin_px(400)
TOUCH_EFFECT_SIZE = from_skin_px(200)
HOLD_EFFECT_SIZE = from_skin_px(240)
JUDGE_TEXT_SIZE = from_skin_px(Vec2(223, 82))
FAST_LATE_SIZE = from_skin_px(Vec2(217, 76))
# Judge text toward the ring center from a button's effect: this, times (2 - Judge Text Distance).
BUTTON_JUDGE_TEXT_OFFSET = from_skin_px(100)
# Fast/late, further in from the judge text.
BUTTON_FAST_LATE_OFFSET = from_skin_px(66)
# The same for a touch, from its sensor.
TOUCH_JUDGE_TEXT_OFFSET = from_skin_px(66)
TOUCH_FAST_LATE_OFFSET = from_skin_px(56)
# Firework skin sprites. A ray: its width at the far end and its length from the firework's center.
# Touch feedback
TOUCH_FEEDBACK_RADIUS = from_skin_px(85)
TOUCH_FEEDBACK_CENTER_RADIUS = from_skin_px(22)
TOUCH_FEEDBACK_PETAL_SIZE = from_skin_px(Vec2(12, 26))
TOUCH_FEEDBACK_PETAL_START = from_skin_px(36)
TOUCH_FEEDBACK_PETAL_END = from_skin_px(121)
# Where the ring sprite's rim is, as a part of its half size.
TOUCH_FEEDBACK_RING_RIM = 0.9

FIREWORK_RAY_SIZE = from_skin_px(Vec2(88, 552))
FIREWORK_BALL_SIZE = from_skin_px(420)
FIREWORK_PALE_BALL_SIZE = from_skin_px(480)
FIREWORK_SPARKLE_SIZE = from_skin_px(56)
# Sparkles, from the firework's center: one group on the ball's edge, one out to the rays' reach.
FIREWORK_INNER_SPARKLE_DISTANCE = from_skin_px(197)
FIREWORK_OUTER_SPARKLE_MIN_DISTANCE = from_skin_px(230)
FIREWORK_OUTER_SPARKLE_MAX_DISTANCE = from_skin_px(500)

# Center counter glyphs at the big (integer) size.
# Every glyph sprite is one line box tall (COUNTER_GLYPH_WIDTHS, by COUNTER_GLYPHS);
# the digits fill COUNTER_DIGIT_HEIGHT of it, outline included, centered.
COUNTER_LINE_HEIGHT = from_skin_px(72)
COUNTER_DIGIT_HEIGHT = from_skin_px(61)
COUNTER_OUTLINE_WIDTH = from_skin_px(2.5)
COUNTER_GLYPH_WIDTHS = tuple(from_skin_px(width) for width in (*(53,) * 10, 36, 76, 53, 53, 66))
# An achievement's dot and decimals, and its %, against the big digits
COUNTER_SMALL_SIZE = 0.72
COUNTER_PERCENT_SIZE = 0.52
COUNTER_SMALL_TRACKING = from_skin_px(-2)
# A DX rank's stars
COUNTER_HEADER_HEIGHT = from_skin_px(79)
COUNTER_STAR_SIZE = 0.5
COUNTER_STAR_TRACKING = from_skin_px(-4)
# The life counter's backdrop (heart, ring and button marks), centered on the counter.
COUNTER_LIFE_SIZE = from_skin_px(276)

NOTE_END_SCALING_PROGRESS = 1 / ((1 - NOTE_SPAWN_DISTANCE) * NOTE_SCALE_RATE + 1)
TOUCH_END_SCALING_PROGGRESS = 0.2

def init_layout():
    Layout.field_w = screen().w
    Layout.field_h = screen().h
    Layout.ring_radius = Options.ring_size
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
    if group == SensorGroup.C:
        return 0.0
    offset = sensor_offset(sensor)
    match group:
        case SensorGroup.A | SensorGroup.B:
            angle = (-2.0 * offset + 3.0) * pi / 8
        case SensorGroup.D | SensorGroup.E:
            angle = (-2.0 * offset + 4.0) * pi / 8
        case _:
            assert_never(group)
    return wrap_pi(angle)

def _get_button_pos(button: Vec2, distance: float) -> Vec2:
    return Vec2.unit(get_button_angle_horizontal(button)) * distance

def layout_ring_pos(angle: float, distance: float) -> Vec2:
    """Screen position at ``angle`` and ``distance`` (ring units) from the ring center."""
    return Layout.ring_center + Vec2.unit(angle) * (distance * Layout.ring_radius)

def layout_ring_point(position: Vec2) -> Vec2:
    """Screen position of a point in ring units (relative to the ring center)."""
    return Layout.ring_center + position * Layout.ring_radius

def layout_px_size(size: float | Vec2, scale: float = 1.0):
    """A size in ring units to screen units, times an option scale."""
    return size * (Layout.ring_radius * scale)

def get_sensor_distance(group: SensorGroup) -> float:
    """Distance of a sensor group from the ring center, in ring units."""
    match group:
        case SensorGroup.A:
            return 0.833333
        case SensorGroup.B:
            return 0.458333
        case SensorGroup.C:
            return 0.0
        case SensorGroup.D:
            return 0.854167
        case SensorGroup.E:
            return 0.645833
        case _:
            assert_never(group)
            return 0.0

def get_sensor_pos_from_center(sensor: Sensor):
    return layout_ring_pos(get_sensor_angle_horizontal(sensor), get_sensor_distance(sensor_to_group(sensor)))

def get_dist_from_center(pos: Vec2):
    return (pos - Layout.ring_center).magnitude

def get_quad_from_center(button: Button, dist: float, size: Vec2) -> Quad:
    """A quad on the button's lane, ``dist`` ring units out, ``size`` in screen units."""
    center = layout_ring_pos(get_button_angle_horizontal(button), dist)
    return Rect.from_center(center, size).as_quad().rotate_centered(get_button_angle_vertical(button))

def apply_quad_mirror_option(quad: Quad) -> Quad:
    """``quad`` under the mirror option, about the ring center (unchanged when it's OFF)."""
    # The option as a 2x2 matrix: a reflection across the axis at angle t is
    # (cos 2t, sin 2t; sin 2t, -cos 2t), the 180 degree rotation is -1.
    mode = Options.mirror
    xx, xy, yx, yy = 1.0, 0.0, 0.0, 1.0
    if mode == MirrorMode.ROTATE_180:
        xx, yy = -1.0, -1.0
    elif mode != MirrorMode.OFF:
        axis = 0.0
        if mode == MirrorMode.LEFT_RIGHT:
            axis = pi / 2
        elif mode == MirrorMode.DIAGONAL_LEFT:
            axis = 3 * pi / 4
        elif mode == MirrorMode.DIAGONAL_RIGHT:
            axis = pi / 4
        xx, xy, yx, yy = cos(2 * axis), sin(2 * axis), sin(2 * axis), -cos(2 * axis)

    def transform(point: Vec2) -> Vec2:
        offset = point - Layout.ring_center
        return Layout.ring_center + Vec2(xx * offset.x + xy * offset.y, yx * offset.x + yy * offset.y)

    return Quad(bl=transform(quad.bl), tl=transform(quad.tl), tr=transform(quad.tr), br=transform(quad.br))

def layout_ring():
    size = layout_px_size(RING_SPRITE_SIZE)
    return Rect.from_center(Layout.ring_center, Vec2(size, size)).as_quad()

def layout_note(progress: float, button: Button):
    note_size = layout_px_size(NOTE_SIZE, Options.note_scale)
    pos = NOTE_SPAWN_DISTANCE
    if progress <= NOTE_END_SCALING_PROGRESS:
        note_size = note_size * clamp(unlerp(0, NOTE_END_SCALING_PROGRESS, progress), 1e-4, 1)
    else:
        pos = remap(NOTE_END_SCALING_PROGRESS, 1, pos, 1, progress)
    center = layout_ring_pos(get_button_angle_horizontal(button), pos)
    dimensions = Vec2(note_size, note_size)
    layout = Rect.from_center(center, dimensions).as_quad()
    return layout

def layout_line(progress: float):
    line_size = layout_px_size(LINE_SIZE)
    if progress <= NOTE_END_SCALING_PROGRESS:
        line_size = line_size * NOTE_SPAWN_DISTANCE
    else:
        line_size = line_size * remap(NOTE_END_SCALING_PROGRESS, 1, NOTE_SPAWN_DISTANCE, 1, progress)
    dimensions = Vec2(line_size, line_size)
    layout = Rect.from_center(Layout.ring_center, dimensions).as_quad()
    return layout

def layout_each_line(progress: float, start_button: Button):
    """The each line arc, scaled like the tap line, turned so its arc starts at ``start_button``
    (the sprites start at button 1 and run clockwise)."""
    line_size = layout_px_size(EACH_LINE_SIZE)
    if progress <= NOTE_END_SCALING_PROGRESS:
        line_size = line_size * NOTE_SPAWN_DISTANCE
    else:
        line_size = line_size * remap(NOTE_END_SCALING_PROGRESS, 1, NOTE_SPAWN_DISTANCE, 1, progress)
    layout = Rect.from_center(Layout.ring_center, Vec2(line_size, line_size)).as_quad()
    return layout.rotate_centered(-(start_button - 1) * pi / 4)

def get_line_alpha(progress: float):
    return unlerp_clamped(0, NOTE_END_SCALING_PROGRESS, progress)


class HoldLayout(Record):
    head: Quad
    body: Quad
    tail: Quad
    end_point: Quad
    # The tail has left the inner start point (the end point is drawn from then on).
    tail_visible: bool


def layout_hold(head_progress: float, tail_progress: float, button: Button) -> HoldLayout:
    # Ring units along the lane; the note scale multiplies the sprite sizes only.
    scale = Options.note_scale
    appear = 1.0
    head_pos = NOTE_SPAWN_DISTANCE
    tail_pos = NOTE_SPAWN_DISTANCE
    tail_visible = False
    if head_progress <= NOTE_END_SCALING_PROGRESS:
        appear = clamp(unlerp(0, NOTE_END_SCALING_PROGRESS, head_progress), 1e-4, 1)
    else:
        head_pos = min(remap(NOTE_END_SCALING_PROGRESS, 1, NOTE_SPAWN_DISTANCE, 1, head_progress), 1)
        if tail_progress > NOTE_END_SCALING_PROGRESS:
            tail_visible = True
            tail_pos = remap(NOTE_END_SCALING_PROGRESS, 1, NOTE_SPAWN_DISTANCE, 1, tail_progress)
            tail_pos = clamp(tail_pos, NOTE_SPAWN_DISTANCE, head_pos)

    width = layout_px_size(HOLD_WIDTH, scale * appear)
    cap = HOLD_CAP_LENGTH * scale * appear
    body = HOLD_BODY_MIN_LENGTH * scale * appear
    end_point_size = layout_px_size(HOLD_END_POINT_SIZE, scale * appear)

    return HoldLayout(
        head=get_quad_from_center(button, head_pos + body / 2 + cap / 2, Vec2(width, layout_px_size(cap))),
        body=get_quad_from_center(button, (head_pos + tail_pos) / 2, Vec2(width, layout_px_size(head_pos - tail_pos + body))),
        tail=get_quad_from_center(button, tail_pos - body / 2 - cap / 2, Vec2(width, layout_px_size(cap))),
        end_point=get_quad_from_center(button, tail_pos, Vec2(end_point_size, end_point_size)),
        tail_visible=tail_visible,
    )


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

    dot_size = layout_px_size(TOUCH_POINT_SIZE, Options.touch_scale)
    dot_rect = Rect.from_center(pos, Vec2(dot_size, dot_size))

    dist_progress = unlerp_clamped(0.4, 0, 0.42 - e ** (4.3 * progress - 5.15))
    fan_dist = layout_px_size(TOUCH_FAN_OFFSET + TOUCH_FAN_TRAVEL * (1 - dist_progress), Options.touch_scale)
    fan_size = layout_px_size(TOUCH_FAN_SIZE, Options.touch_scale)
    fan_rect = Rect.from_center(pos + Vec2(0, -fan_dist), fan_size)

    return TouchLayoutGroup(
        dot=dot_rect.as_quad(),
        bottom_fan=fan_rect.as_quad(),
        border=Rect.from_center(pos, layout_px_size(Vec2.one() * TOUCH_JUST_BORDER_SIZE, Options.touch_scale)).as_quad(),
    )

class TouchHoldLayoutGroup(Record):
    dot: Quad
    fan: Quad
    border: Quad

    def get_fan(self, index: int) -> Quad:
        return self.fan.rotate_about(3 * pi / 4 - index * pi / 2, pivot=self.dot.center)

def layout_touch_hold(progress: float, sensor: Sensor):
    pos = get_sensor_pos_from_center(sensor)

    dot_size = layout_px_size(TOUCH_POINT_SIZE, Options.touch_scale)
    dot_rect = Rect.from_center(pos, Vec2(dot_size, dot_size))

    # Same approach as a touch.
    dist_progress = unlerp_clamped(0.4, 0, 0.42 - e ** (4.3 * progress - 5.15))
    fan_dist = layout_px_size(TOUCH_FAN_OFFSET + TOUCH_FAN_TRAVEL * (1 - dist_progress), Options.touch_scale)
    fan_size = layout_px_size(TOUCH_FAN_SIZE, Options.touch_scale)
    fan_rect = Rect.from_center(pos + Vec2(0, -fan_dist), fan_size)

    border_size = layout_px_size(TOUCH_HOLD_BORDER_SIZE, Options.touch_scale)

    return TouchHoldLayoutGroup(
        dot=dot_rect.as_quad(),
        fan=fan_rect.as_quad(),
        border=Rect.from_center(pos, border_size).as_quad(),
    )

class TouchHoldBorderPiece(Record):
    """A piece of the partly filled touch hold border, drawn with that side's bar sprite."""
    # Border side, clockwise from the top-right one (0..3).
    side: int
    quad: Quad

class TouchHoldBorderLayout(Record):
    """The touch hold border layout as bar pieces.

    The border sprite is a rounded diamond.
    Each side is one colour from the corner before it to the corner after.
    Per side: half corner, straight side, half corner.
    """
    # Rectangles per half corner (45 degrees).
    CORNER_STEPS = 6
    # Per side: CORNER_STEPS pieces for each of the two half corners and 1 for the straight part.
    Pieces = VarArray[TouchHoldBorderPiece, Dim[52]]  # (6 + 6 + 1) * 4 = 52

    pieces: Pieces

    # Pixel distance of the side from the center
    SIDE_DISTANCE = 66.5
    # Arc of the border on each corner
    CORNER_RADIUS = 34.25
    # Half the thickness of the ring.
    RING_HALF = 13
    # Distance from the center to the corner arc centers.
    CORNER_DISTANCE = (SIDE_DISTANCE - CORNER_RADIUS) * sqrt(2)

    @classmethod
    def build(cls, progress: float, sensor: Sensor):
        straight_start = atan2(cls.CORNER_RADIUS / sqrt(2), cls.CORNER_DISTANCE + cls.CORNER_RADIUS / sqrt(2))
        straight_end = pi / 2 - straight_start

        layout = cls(pieces=cls.Pieces.new())
        sweep = clamp(progress, 0, 1) * 2 * pi
        for side in range(4):
            if sweep > side * pi / 2:
                # Built for the top-right side (y up, pixels), then turned to its place.
                phi = min(sweep - side * pi / 2, pi / 2)
                top_corner = Vec2(0, cls.CORNER_DISTANCE)
                right_corner = Vec2(cls.CORNER_DISTANCE, 0)
                # Angles around each corner's center: the top corner's half runs from pi / 2 down
                # to pi / 4, the right corner's from pi / 4 down to 0.
                top_end = pi / 4
                if phi < straight_start:
                    top_end = cls.ray_angle(phi, top_corner, pi / 2, pi / 4)
                layout.add_arc(sensor, side, top_corner, pi / 2, top_end)
                if phi > straight_start:
                    straight_from = top_corner + Vec2.unit(pi / 4) * cls.CORNER_RADIUS
                    along = Vec2.unit(-pi / 4)
                    length = cls.CORNER_DISTANCE * sqrt(2)
                    if phi < straight_end:
                        ray = Vec2(sin(phi), cos(phi))
                        hit = ray * (cls.SIDE_DISTANCE * sqrt(2) / (ray.x + ray.y))
                        length = clamp((hit - straight_from).dot(along), 0, length)
                    straight_to = straight_from + along * length
                    normal = Vec2.unit(pi / 4) * cls.RING_HALF
                    layout.add_piece(
                        sensor, side, straight_from + normal, straight_from - normal,
                        straight_to - normal, straight_to + normal,
                    )
                if phi > straight_end:
                    right_end = 0.0
                    if phi < pi / 2:
                        right_end = cls.ray_angle(phi, right_corner, pi / 4, 0)
                    layout.add_arc(sensor, side, right_corner, pi / 4, right_end)
        return layout

    @classmethod
    def ray_angle(cls, phi: float, corner_center: Vec2, start: float, end: float) -> float:
        """Angle around ``corner_center`` (clamped to ``end``..``start``) where the sweep ray at
        ``phi`` (clockwise from 12 o'clock) crosses the corner's centerline arc."""
        ray = Vec2(sin(phi), cos(phi))
        b = ray.dot(corner_center)
        disc = b * b - (corner_center.dot(corner_center) - cls.CORNER_RADIUS ** 2)
        result = start
        if disc >= 0:
            hit = ray * (b + sqrt(disc))
            result = clamp(atan2(hit.y - corner_center.y, hit.x - corner_center.x), end, start)
        return result

    def add_piece(self, sensor: Sensor, side: int, bl: Vec2, tl: Vec2, tr: Vec2, br: Vec2):
        """Adds a piece given in border pixels of the top-right side (y up), turned clockwise to
        ``side`` and placed on the sensor."""
        center = get_sensor_pos_from_center(sensor)
        # Screen size of one border sprite pixel.
        scale = layout_px_size(from_skin_px(1), Options.touch_scale)
        angle = -side * pi / 2
        self.pieces.append(TouchHoldBorderPiece(
            side=side,
            quad=Quad(
                bl=center + bl.rotate(angle) * scale,
                tl=center + tl.rotate(angle) * scale,
                tr=center + tr.rotate(angle) * scale,
                br=center + br.rotate(angle) * scale,
            ),
        ))

    def add_arc(self, sensor: Sensor, side: int, corner_center: Vec2, start_angle: float, end_angle: float):
        """Clockwise arc around ``corner_center`` from ``start_angle`` down to ``end_angle``,
        as up to ``CORNER_STEPS`` rectangles across the bar."""
        if start_angle - end_angle < 1e-4:
            return
        # Near the outer edge of the glow, which the skin transform puts at twice the ring's half thickness.
        meet = self.CORNER_RADIUS + 2 * self.RING_HALF - 8
        step = pi / 4 / self.CORNER_STEPS
        count = ceil((start_angle - end_angle) / step - 1e-4)
        for i in range(count):
            angle_from = start_angle - i * step
            angle_to = max(start_angle - (i + 1) * step, end_angle)
            mid = Vec2.unit((angle_from + angle_to) / 2)
            # Clockwise along the arc, half the width.
            across = mid.rotate(-pi / 2) * (meet * tan((angle_from - angle_to) / 2))
            inner = corner_center + mid * (self.CORNER_RADIUS - self.RING_HALF)
            outer = corner_center + mid * (self.CORNER_RADIUS + self.RING_HALF)
            self.add_piece(sensor, side, outer - across, inner - across, inner + across, outer + across)

def get_touch_fan_alpha(progress: float):
    return unlerp_clamped(0, TOUCH_END_SCALING_PROGGRESS, progress)

class SlidePoint(Record):
    position: Vec2   # ring-unit (0 = center, 1 = ring)
    rotation: float  # radians, in the canonical orientation

SlideTrackPointArray = VarArray[SlidePoint, Dim[100]]

def empty_track_points() -> SlideTrackPointArray:
    return SlideTrackPointArray.new()

def connect_tracks(*tracks: SlideTrackPointArray):
    final = SlideTrackPointArray.new()
    for track in tracks:
        final.extend(track)
    return final

def build_circle_track_points(sample_count: int) -> SlideTrackPointArray:
    assert_true(sample_count >= 0 and sample_count <= 63)
    if sample_count == 0:
        return empty_track_points()

    points = SlideTrackPointArray.new()
    start_angle = get_button_angle_horizontal(1)

    for i in range(sample_count):
        angle = start_angle - (i + 1) * (pi / 32)
        point = SlidePoint(position=Vec2.unit(angle), rotation=angle + pi / 2)
        points.append(point)
    return points

# Slide building functions take positions in skin pixels (judgment ring at 480 px)
def build_line_track_points(
    start: Vec2,
    stop: Vec2,
    sample_count: int,
    fixed_rotation: bool = False,
    rotation: float = 0.0,
    progress_exponent: float = 1.0,
    rotation_offset: float = 0.0,
) -> SlideTrackPointArray:
    """Build a straight track from endpoints and a sample count."""
    points = SlideTrackPointArray.new()
    if not fixed_rotation:
        rotation = (stop - start).angle + pi
    rotation += rotation_offset
    for i in range(sample_count):
        progress = unlerp_clamped(0, sample_count - 1, i)
        if progress_exponent != 1.0:
            progress = progress ** progress_exponent
        mid = from_skin_px(start + (stop - start) * progress)
        point = SlidePoint(position=mid, rotation=rotation)
        points.append(point)
    return points

def build_arc_track_points(
    center: Vec2,
    radius: float,
    sample_count: int,
    phase_degrees: float,
    step_degrees: float,
    rotation_offset_degrees: float = 0.0,
):
    """Build a circular arc track using a phase and angular step."""
    points = SlideTrackPointArray.new()
    phase = phase_degrees * pi / 180
    step = step_degrees * pi / 180
    rotation_offset = rotation_offset_degrees * pi / 180
    for i in range(sample_count):
        angle = phase + i * step
        point = SlidePoint(
            position=from_skin_px(center + Vec2.unit(angle) * radius),
            rotation=angle - pi / 2 + rotation_offset
        )
        points.append(point)
    return points

SLIDE_TRACK_POINTS = Array(
    empty_track_points(),
    # Circle
    build_circle_track_points(63),
    build_circle_track_points(7),
    build_circle_track_points(15),
    build_circle_track_points(23),
    build_circle_track_points(31),
    build_circle_track_points(39),
    build_circle_track_points(47),
    build_circle_track_points(55),
    # Straight
    build_line_track_points(Vec2(201.9, 399.6), Vec2(420.1, -127.2), 13),
    build_line_track_points(Vec2(183.7, 396.5), Vec2(183.7, -402.7), 18),
    build_line_track_points(Vec2(165.7, 400), Vec2(-158.3, -382.3), 19),
    # Center
    connect_tracks(
        build_line_track_points(Vec2(165.7, 401.2), Vec2(3.7, 9.6), 10, fixed_rotation=True, rotation=67.5 * pi / 180),
        build_line_track_points(Vec2(11.3, 26.8), Vec2(173.3, 418.4), 10)
    ),
    connect_tracks(
        build_line_track_points(Vec2(165.7, 401.2), Vec2(3.7, 9.6), 10, fixed_rotation=True, rotation=67.5 * pi / 180),
        build_line_track_points(Vec2(31.7, 12.4), Vec2(381.6, 160.2), 9)
    ),
    connect_tracks(
        build_line_track_points(Vec2(165.7, 401.2), Vec2(3.7, 9.6), 10, fixed_rotation=True, rotation=67.5 * pi / 180),
        build_line_track_points(Vec2(34.4, -16.5), Vec2(386.3, -159.3), 9)
    ),
    connect_tracks(
        build_line_track_points(Vec2(165.7, 401.2), Vec2(3.7, 9.6), 10, fixed_rotation=True, rotation=67.5 * pi / 180),
        build_line_track_points(Vec2(19.1, -38), Vec2(167, -387.9), 9)
    ),
    # Inner loop
    connect_tracks(
        build_line_track_points(Vec2(150.3, 410.2), Vec2(-117, 144.5), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0, 0), 185, 16, 143.564, 14.591),
        build_line_track_points(Vec2(184.8, 55), Vec2(183.9, 384.7), 8)
    ),
    connect_tracks(
        build_line_track_points(Vec2(150.1, 410.1), Vec2(-118.5, 143), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0, 0), 185, 13, 144.289, 14.664),
        build_line_track_points(Vec2(176.2, -85.2), Vec2(409.8, 149.8), 8)
    ),
    connect_tracks(
        build_line_track_points(Vec2(150.2, 410.2), Vec2(-117.7, 143.8), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0, 0), 185, 10, 143.916, 14.625),
        build_line_track_points(Vec2(65.1, -184.8), Vec2(395.7, -183.8), 8)
    ),
    connect_tracks(
        build_line_track_points(Vec2(150.3, 410.3), Vec2(-116.9, 144.6), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0, 0), 185, 6, 143.534, 14.586),
        build_line_track_points(Vec2(-116.9, -144.6), Vec2(150.3, -410.3), 9)
    ),
    connect_tracks(
        build_line_track_points(Vec2(150.4, 410.4), Vec2(-115.8, 145.8), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0, 0), 185, 4, 142.964, 14.520),
        build_line_track_points(Vec2(-184.8, -68), Vec2(-183.8, -396.4), 8)
    ),
    connect_tracks(
        build_line_track_points(Vec2(149.9, 409.9), Vec2(-120.4, 141.1), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0, 0), 185, 25, 145.216, 14.757),
        build_line_track_points(Vec2(-174.4, 87), Vec2(-409.5, -149.5), 8, rotation_offset=2 * pi)
    ),
    connect_tracks(
        build_line_track_points(Vec2(152.5, 412.5), Vec2(-128.2, 133.4), 10, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0, 0), 185, 21, 148.932, 14.875),
        build_line_track_points(Vec2(-33.4, 184.9), Vec2(-385.3, 183.9), 9),
    ),
    connect_tracks(
        build_line_track_points(Vec2(150.1, 410.1), Vec2(-118.3, 143.3), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0, 0), 185, 19, 144.173, 14.653),
        build_line_track_points(Vec2(90.6, 170.8), Vec2(-144.3, 404.3), 8),
    ),
    # Outer loop
    connect_tracks(
        build_line_track_points(Vec2(163.7, 400.3), Vec2(23, 101), 8),
        build_arc_track_points(Vec2(220, -3), 223, 21, 164.156, 12.057, -4.0),
        build_line_track_points(Vec2(351.1, 196), Vec2(219.2, 390.6), 6),
    ),
    connect_tracks(
        build_line_track_points(Vec2(163.7, 400.3), Vec2(23, 101), 8),
        build_arc_track_points(Vec2(220, -3), 223, 18, 164.135, 12.055, -4.0),
        build_line_track_points(Vec2(443.9, 80.7), Vec2(444, 127.2), 2),
    ),
    connect_tracks(
        build_line_track_points(Vec2(163.3, 401.9), Vec2(23, 103), 8),
        build_arc_track_points(Vec2(220, -3), 223, 11, 163.772, 12.074, -4.0),
        build_line_track_points(Vec2(321.6, -209.4), Vec2(414.6, -189.4), 3),
    ),
    connect_tracks(
        build_line_track_points(Vec2(163.9, 400.7), Vec2(24.4, 101.1), 8),
        build_arc_track_points(Vec2(220, -3), 223, 35, 163.948, 12.095, -4.0),
        build_line_track_points(Vec2(56.6, -176.5), Vec2(157.8, -390), 6, rotation_offset=2 * pi),
    ),
    connect_tracks(
        build_line_track_points(Vec2(163.1, 400.5), Vec2(21.3, 104.2), 8),
        build_arc_track_points(Vec2(220, -3), 223, 31, 163.747, 12.071, -4.0),
        build_line_track_points(Vec2(-15, 7.1), Vec2(-163.3, -390.8), 10, rotation_offset=2 * pi),
    ),
    connect_tracks(
        build_line_track_points(Vec2(164.2, 399.6), Vec2(22.3, 103.3), 8),
        build_arc_track_points(Vec2(220, -3), 223, 28, 163.555, 12.113, -4.0),
        build_line_track_points(Vec2(36.4, 138.5), Vec2(-393.7, -150.6), 12, rotation_offset=2 * pi),
    ),
    connect_tracks(
        build_line_track_points(Vec2(164.2, 399.6), Vec2(22.3, 103.3), 8),
        build_arc_track_points(Vec2(220, -3), 223, 25, 163.502, 12.109, -4.0),
        build_line_track_points(Vec2(157.7, 217.3), Vec2(-407, 186.5), 13, rotation_offset=2 * pi),
    ),
    connect_tracks(
        build_line_track_points(Vec2(163, 400.4), Vec2(22.3, 103.3), 8),
        build_arc_track_points(Vec2(220, -3), 223, 23, 163.444, 12.121, -4.0),
        build_line_track_points(Vec2(254, 227.2), Vec2(-127.8, 415.5), 10),
    ),
    # Refect
    connect_tracks(
        build_line_track_points(Vec2(139.8, 425.3), Vec2(-430.9, 188.9), 14),
        build_line_track_points(Vec2(-414.9, 184.5), Vec2(386.9, 184.5), 18),
    ),
    connect_tracks(
        build_line_track_points(Vec2(139.8, 425.3), Vec2(-430.9, 188.9), 14),
        build_line_track_points(Vec2(-416.2, 173.6), Vec2(409.7, -168.1), 20),
    ),
    connect_tracks(
        build_line_track_points(Vec2(139.8, 425.3), Vec2(-430.9, 188.9), 14),
        build_line_track_points(Vec2(-425.5, 165), Vec2(143.8, -402.2), 18),
    ),
    connect_tracks(
        build_line_track_points(Vec2(139.8, 425.3), Vec2(-430.9, 188.9), 14),
        build_line_track_points(Vec2(-430.7, 160.9), Vec2(-198.9, -407.9), 14),
    ),
    # Zigzag
    connect_tracks(
        build_line_track_points(Vec2(150.8, 410.2), Vec2(-164.2, 95.5), 11),
        build_line_track_points(Vec2(-142.3, 58.7), Vec2(163.6, -66.6), 8),
        build_line_track_points(Vec2(166, -93.3), Vec2(-167.6, -426.6), 11),
    ),
    # Wifi path
    build_line_track_points(Vec2(157.8, 389.4), Vec2(-122.5, -286.8), 11, fixed_rotation=True, rotation=0.0, progress_exponent=1.164),
    # Wifi stars paths
    build_line_track_points(_get_button_pos(1, SKIN_RING_RADIUS_PX), _get_button_pos(6, SKIN_RING_RADIUS_PX), 11, fixed_rotation=True, rotation=0.0),
    build_line_track_points(_get_button_pos(1, SKIN_RING_RADIUS_PX), _get_button_pos(5, SKIN_RING_RADIUS_PX), 11, fixed_rotation=True, rotation=0.0),
    build_line_track_points(_get_button_pos(1, SKIN_RING_RADIUS_PX), _get_button_pos(4, SKIN_RING_RADIUS_PX), 11, fixed_rotation=True, rotation=0.0),
)

def build_slide_star_points(track_points: SlideTrackPointArray, end_button: Button) -> SlideTrackPointArray:
    assert_true(len(track_points) > 1, "Can't build a track with less than 2 points!")
    star_points = SlideTrackPointArray.new()
    rotation_offset = pi / 10
    star_points.append(SlidePoint(
        position=Vec2.unit(get_button_angle_horizontal(1)),
        rotation=track_points[0].rotation + rotation_offset
    ))
    for point in track_points:
        star_points.append(SlidePoint(
            position=point.position,
            rotation=point.rotation + rotation_offset
        ))
    star_points.append(SlidePoint(
        position=Vec2.unit(get_button_angle_horizontal(end_button)),
        rotation=lerp(track_points[-2].rotation, track_points[-1].rotation, 2.0) + rotation_offset
    ))
    return star_points

SLIDE_FADE_IN_MAX_ALPHA = 0.5

def get_slide_path_alpha(start_time: float, target_time: float, current_time: float) -> float:
    if current_time < start_time:
        return 0.0
    end_time = target_time - 0.05
    if current_time > end_time:
        return 1.0
    fade_in_duration = clamp(end_time - start_time, 0, 0.2)
    fade_in_cutoff = start_time + fade_in_duration
    if current_time > fade_in_cutoff:
        return SLIDE_FADE_IN_MAX_ALPHA
    alpha = remap(start_time, fade_in_cutoff, 0, SLIDE_FADE_IN_MAX_ALPHA, current_time)
    return alpha

def slide_point_transform(point: SlidePoint, button: Button, is_mirrored: bool) -> SlidePoint:
    angle_offset = get_button_angle_horizontal(button) - get_button_angle_horizontal(1)
    new_position = +point.position
    new_rotation = point.rotation
    if is_mirrored:
        new_position.x = -new_position.x
        angle_offset -= pi / 4
        new_rotation = pi - point.rotation
    return SlidePoint(new_position.rotate(angle_offset), new_rotation + angle_offset)

def layout_slide_path(index: int, track_points: SlideTrackPointArray, button: Button, is_mirrored: bool):
    point = slide_point_transform(track_points[index], button, is_mirrored)
    center = layout_ring_point(point.position)
    size = layout_px_size(SLIDE_PATH_SIZE, Options.slide_scale)
    layout = Rect.from_center(center, size).as_quad().rotate_centered(point.rotation)
    return layout

def layout_wifi_slide_path(
    index: int,
    track_points: SlideTrackPointArray,
    button: Button,
    is_mirrored: bool,
):
    point = track_points[index]
    angle_offset = get_button_angle_horizontal(button) - get_button_angle_horizontal(1)
    position = +point.position
    if is_mirrored:
        position.x = -position.x
        angle_offset -= pi / 4
    center = layout_ring_point(position.rotate(angle_offset))
    size = layout_px_size(WIFI_SLIDE_PATH_SIZES[index], Options.slide_scale)
    layout = Rect.from_center(center, size).as_quad()
    if not is_mirrored:
        layout @= layout.scale_centered(Vec2(-1, 1))
    return layout.rotate_centered(angle_offset)

def layout_slide_head(
    progress: float,
    star_points: SlideTrackPointArray,
    button: Button,
    is_mirrored: bool,
    rotate_head: bool = True,
):
    point_count = len(star_points)
    point_progress = progress * (point_count - 1)
    point = SlidePoint(Vec2.zero(), 0)
    if progress <= 0:
        point @= slide_point_transform(star_points[0], button, is_mirrored)
    elif progress >= 1:
        point @= slide_point_transform(star_points[-1], button, is_mirrored)
    else:
        index = int(point_progress)
        fraction = point_progress - index
        point_a = slide_point_transform(star_points[index], button, is_mirrored)
        point_b = slide_point_transform(star_points[index + 1], button, is_mirrored)
        point.position @= Vec2(
            lerp(point_a.position.x, point_b.position.x, fraction),
            lerp(point_a.position.y, point_b.position.y, fraction),
        )
        point.rotation = lerp(point_a.rotation, point_b.rotation, fraction)
        
    center = layout_ring_point(point.position)
    note_size = layout_px_size(NOTE_SIZE, Options.note_scale)
    layout = Rect.from_center(center, Vec2(note_size, note_size)).as_quad()
    if rotate_head:
        layout @= layout.rotate_centered(point.rotation)
    return layout



def get_sensor_effect_angle(sensor: Sensor) -> float:
    """Direction from the ring center through ``sensor``: effects there face it. Straight up for C."""
    result = pi / 2
    if sensor_to_group(sensor) != SensorGroup.C:
        result = get_sensor_angle_horizontal(sensor)
    return result

def layout_effect_quad(angle: float, distance: float, size: Vec2) -> Quad:
    """A ``size`` (screen units) quad ``distance`` ring units out at ``angle``, its top facing out."""
    center = layout_ring_pos(angle, distance)
    return Rect.from_center(center, size).as_quad().rotate_centered(angle - pi / 2)

def layout_counter_glyph(left: float, width: float, scale: float, size: float = 1.0) -> Quad:
    """A counter glyph's cell,
    ``width`` wide at the big size, drawn at ``size`` of it on the big digits' baseline.
    ``left`` is its left edge from the string's center; the whole string is scaled by ``scale``."""
    center = Vec2(left + width * size / 2, -COUNTER_DIGIT_HEIGHT / 2 * (1 - size))
    cell = Vec2(width, COUNTER_LINE_HEIGHT) * size
    return Rect.from_center(layout_ring_point(center * scale), layout_px_size(cell, scale)).as_quad()

def layout_counter_backdrop(size: float, scale: float) -> Quad:
    """A ``size`` square behind the counter, centered on it, scaled with it by ``scale``."""
    return Rect.from_center(layout_ring_point(Vec2(0, 0)), layout_px_size(Vec2(size, size), scale)).as_quad()

def layout_counter_header_glyph(left: float, width: float, scale: float, size: float) -> Quad:
    """Like ``layout_counter_glyph``, in the header row above the counter, centered on it."""
    center = Vec2(left + width * size / 2, COUNTER_HEADER_HEIGHT)
    cell = Vec2(width, COUNTER_LINE_HEIGHT) * size
    return Rect.from_center(layout_ring_point(center * scale), layout_px_size(cell, scale)).as_quad()

def layout_tap_effect(button: Button) -> Quad:
    size = layout_px_size(TAP_EFFECT_SIZE, Options.effect_size)
    return layout_effect_quad(get_button_angle_horizontal(button), 1, Vec2(size, size))

def layout_hold_effect(button: Button) -> Quad:
    size = layout_px_size(HOLD_EFFECT_SIZE, Options.effect_size)
    return layout_effect_quad(get_button_angle_horizontal(button), 1, Vec2(size, size))

def layout_touch_effect(sensor: Sensor) -> Quad:
    size = layout_px_size(TOUCH_EFFECT_SIZE, Options.effect_size)
    return layout_effect_quad(
        get_sensor_effect_angle(sensor), get_sensor_distance(sensor_to_group(sensor)), Vec2(size, size)
    )

def layout_touch_hold_effect(sensor: Sensor) -> Quad:
    """A touch hold ends with a tap effect on its sensor."""
    size = layout_px_size(TAP_EFFECT_SIZE, Options.effect_size)
    return layout_effect_quad(
        get_sensor_effect_angle(sensor), get_sensor_distance(sensor_to_group(sensor)), Vec2(size, size)
    )

def layout_touch_hold_glow(sensor: Sensor) -> Quad:
    size = layout_px_size(HOLD_EFFECT_SIZE, Options.effect_size)
    return layout_effect_quad(
        get_sensor_effect_angle(sensor), get_sensor_distance(sensor_to_group(sensor)), Vec2(size, size)
    )

def layout_touch_feedback_center(sensor: Sensor) -> Vec2:
    """A sensors (and the buttons) on the ring, the others at their sensor."""
    result = get_sensor_pos_from_center(sensor)
    if sensor_to_group(sensor) == SensorGroup.A:
        result @= layout_ring_pos(get_button_angle_horizontal(sensor - Sensor.A1 + 1), 1)
    return result

def layout_touch_feedback_ring(center: Vec2, radius: float) -> Quad:
    """A ring sprite with its rim at ``radius`` (ring units)."""
    side = layout_px_size(2 * radius / TOUCH_FEEDBACK_RING_RIM)
    return Rect.from_center(center, Vec2(side, side)).as_quad()

def layout_touch_feedback_petal(center: Vec2, angle: float, progress: float, scale: float) -> Quad:
    """A petal pointing out at ``angle``, ``progress`` of the way from its start to its end distance."""
    distance = lerp(TOUCH_FEEDBACK_PETAL_START, TOUCH_FEEDBACK_PETAL_END, progress)
    position = center + Vec2.unit(angle) * layout_px_size(distance)
    size = layout_px_size(TOUCH_FEEDBACK_PETAL_SIZE, scale)
    return Rect.from_center(position, size).as_quad().rotate_centered(angle - pi / 2)

def layout_button_firework_center(button: Button) -> Vec2:
    return layout_ring_pos(get_button_angle_horizontal(button), 1)

def layout_sensor_firework_center(sensor: Sensor) -> Vec2:
    return get_sensor_pos_from_center(sensor)

def layout_firework_ray(center: Vec2, angle: float, start: float, end: float) -> Quad:
    """A ray out from ``center`` at ``angle``, from ``start`` to ``end`` of its length:
    its sprite's bottom edge at the start (the center, until the ray draws away from it)."""
    size = layout_px_size(FIREWORK_RAY_SIZE, Options.effect_size)
    out = Vec2.unit(angle)
    side = Vec2.unit(angle - pi / 2) * (size.x / 2)
    base = center + out * (size.y * start)
    tip = center + out * (size.y * end)
    return Quad(bl=base - side, tl=tip - side, tr=tip + side, br=base + side)

def layout_firework_ball(center: Vec2, size: float, scale: float) -> Quad:
    side = layout_px_size(size, Options.effect_size * scale)
    return Rect.from_center(center, Vec2(side, side)).as_quad()

def layout_firework_sparkle(center: Vec2, angle: float, distance: float, scale: float) -> Quad:
    side = layout_px_size(FIREWORK_SPARKLE_SIZE, Options.effect_size * scale)
    position = center + Vec2.unit(angle) * layout_px_size(distance, Options.effect_size)
    return Rect.from_center(position, Vec2(side, side)).as_quad()


class JudgeTextLayout(Record):
    text: Quad
    # Fast/late below the judge text, and in its place when the judge text isn't shown.
    fast_late: Quad
    fast_late_alone: Quad

def layout_judge_text_at(angle: float, distance: float, text_offset: float, fast_late_offset: float) -> JudgeTextLayout:
    text_distance = distance - text_offset * (2 - Options.judge_text_distance)
    text_size = layout_px_size(JUDGE_TEXT_SIZE)
    fast_late_size = layout_px_size(FAST_LATE_SIZE)
    return JudgeTextLayout(
        text=layout_effect_quad(angle, text_distance, text_size),
        fast_late=layout_effect_quad(angle, text_distance - fast_late_offset, fast_late_size),
        fast_late_alone=layout_effect_quad(angle, text_distance, fast_late_size),
    )

def layout_button_judge_text(button: Button) -> JudgeTextLayout:
    """Taps, stars and holds."""
    return layout_judge_text_at(
        get_button_angle_horizontal(button), 1, BUTTON_JUDGE_TEXT_OFFSET, BUTTON_FAST_LATE_OFFSET
    )

def layout_touch_judge_text(sensor: Sensor) -> JudgeTextLayout:
    return layout_judge_text_at(
        get_sensor_effect_angle(sensor),
        get_sensor_distance(sensor_to_group(sensor)),
        TOUCH_JUDGE_TEXT_OFFSET,
        TOUCH_FAST_LATE_OFFSET,
    )

def layout_touch_hold_judge_text(sensor: Sensor) -> JudgeTextLayout:
    """Placed like a button's, from the sensor."""
    return layout_judge_text_at(
        get_sensor_effect_angle(sensor),
        get_sensor_distance(sensor_to_group(sensor)),
        BUTTON_JUDGE_TEXT_OFFSET,
        BUTTON_FAST_LATE_OFFSET,
    )


class SlideOkLayout(Record):
    quad: Quad
    shape: SlideOkShape
    is_right: bool

def layout_slide_ok(track: int, start_button: Button, is_mirrored: bool, end_button: Button) -> SlideOkLayout:
    index = track * 2
    if is_mirrored:
        index += 1
    pose = SLIDE_OK_POSES[index]
    shape = pose.shape
    # Right: the curve runs clockwise, the Wi-Fi ends in the upper half, a straight one ends in the right half.
    is_right = end_button <= 4
    if shape == SlideOkShape.CURVE:
        is_right = not is_mirrored
    elif shape == SlideOkShape.WIFI:
        is_right = end_button <= 2 or end_button >= 7
    offset = get_button_angle_horizontal(start_button) - get_button_angle_horizontal(1)
    position = pose.position.rotate(offset)
    rotation = pose.rotation + offset
    if shape != SlideOkShape.CURVE and is_right == pose.turn_on_right:
        rotation += pi
        if shape == SlideOkShape.STRAIGHT:
            position += Vec2.unit(rotation - pi / 2) * SLIDE_OK_TURN_SHIFT
    size = layout_px_size(SLIDE_OK_SIZES[shape])
    quad = Rect.from_center(layout_ring_point(position), size).as_quad().rotate_centered(rotation)
    return SlideOkLayout(quad=quad, shape=shape, is_right=is_right)
