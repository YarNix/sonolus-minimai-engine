from math import cos, floor, log, pi, sin, e
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

from minimai.lib.game import Button, Sensor, SensorGroup, sensor_offset, sensor_to_group
from minimai.lib.level_config import LevelConfig
from minimai.lib.options import Options

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
TOUCH_DISTANCE_START = 0.12
TOUCH_DISTANCE_END = 0.0468

NOTE_SCALE_RATE = 0.265
NOTE_BASE_SIZE = 0.3828
LINE_BASE_SIZE = 1.095
TOUCH_DOT_BASE_SIZE = 0.076
TOUCH_FAN_BASE_SIZE = Vec2(112, 82) / 112 * 0.2514
SLIDE_PATH_BASE_SIZE = Vec2(70, 94) / 480
SLIDE_UNIT = 4.8
WIFI_SLIDE_PATH_BASE_SIZES = Array(*(size / 480 for size in (
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

def get_pos_from_center(angle: float, distance: float) -> Vec2:
    return Layout.ring_center + Vec2.unit(angle) * distance

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
    note_size = NOTE_BASE_SIZE * Layout.ring_distance * Options.note_scale
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

    dot_size = TOUCH_DOT_BASE_SIZE * Layout.ring_distance * Options.touch_scale
    dot_rect = Rect.from_center(pos, Vec2(dot_size, dot_size))

    dist_progress = unlerp_clamped(0.4, 0, 0.42 - e ** (4.3 * progress - 5.15))
    fan_dist = lerp(TOUCH_DISTANCE_START, TOUCH_DISTANCE_END, dist_progress) * Layout.ring_distance * Options.touch_scale
    fan_size = TOUCH_FAN_BASE_SIZE * Layout.ring_distance * Options.touch_scale
    fan_rect = Rect.from_center(pos + Vec2(0, -fan_dist), fan_size)

    return TouchLayoutGroup(
        dot=dot_rect.as_quad(),
        bottom_fan=fan_rect.as_quad(),
        border=dot_rect.scale_centered(Vec2(4, 4)).as_quad(),
    )

def get_touch_fan_alpha(progress: float):
    return unlerp_clamped(0, TOUCH_END_SCALING_PROGGRESS, progress)

class SlidePoint(Record):
    position: Vec2   # ring-unit (0 = center, 1 = ring)
    rotation: float  # radians, in the canonical orientation

SlideTrackPointArray = VarArray[SlidePoint, Dim[65]]

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

# Slide building functions use "slide unit" for position
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
        mid = (start + (stop - start) * progress) / SLIDE_UNIT
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
            position=(center + Vec2.unit(angle) * radius) / SLIDE_UNIT,
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
    build_line_track_points(Vec2(2.019, 3.996), Vec2(4.201, -1.272), 13),
    build_line_track_points(Vec2(1.837, 3.965), Vec2(1.837, -4.027), 18),
    build_line_track_points(Vec2(1.657, 4.000), Vec2(-1.583, -3.823), 19),
    # Center
    connect_tracks(
        build_line_track_points(Vec2(1.657, 4.012), Vec2(0.037,  0.096), 10, fixed_rotation=True, rotation=67.5 * pi / 180),
        build_line_track_points(Vec2(0.113, 0.268), Vec2(1.733,  4.184), 10)
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.657, 4.012), Vec2(0.037, 0.096), 10, fixed_rotation=True, rotation=67.5 * pi / 180),
        build_line_track_points(Vec2(0.317, 0.124), Vec2(3.816, 1.602), 9)
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.657, 4.012), Vec2(0.037, 0.096), 10, fixed_rotation=True, rotation=67.5 * pi / 180),
        build_line_track_points(Vec2(0.344, -0.165), Vec2(3.863, -1.593), 9)
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.657, 4.012), Vec2(0.037, 0.096), 10, fixed_rotation=True, rotation=67.5 * pi / 180),
        build_line_track_points(Vec2(0.191, -0.380), Vec2(1.670, -3.879), 9)
    ),
    # Inner loop
    connect_tracks(
        build_line_track_points(Vec2(1.503, 4.102), Vec2(-1.170, 1.445), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0.0, 0.0), 1.85, 16, 143.564, 14.591),
        build_line_track_points(Vec2(1.848, 0.550), Vec2(1.839, 3.847), 8)
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.501, 4.101), Vec2(-1.185, 1.430), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0.0, 0.0), 1.85, 13, 144.289, 14.664),
        build_line_track_points(Vec2(1.762, -0.852), Vec2(4.098, 1.498), 8)
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.502, 4.102), Vec2(-1.177, 1.438), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0.0, 0.0), 1.85, 10, 143.916, 14.625),
        build_line_track_points(Vec2(0.651, -1.848), Vec2(3.957, -1.838), 8)
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.503, 4.103), Vec2(-1.169, 1.446), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0.0, 0.0), 1.85, 6, 143.534, 14.586),
        build_line_track_points(Vec2(-1.169, -1.446), Vec2(1.503, -4.103), 9)
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.504, 4.104), Vec2(-1.158, 1.458), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0.0, 0.0), 1.85, 4, 142.964, 14.520),
        build_line_track_points(Vec2(-1.848, -0.680), Vec2(-1.838, -3.964), 8)
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.499, 4.099), Vec2(-1.204, 1.411), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0.0, 0.0), 1.85, 25, 145.216, 14.757),
        build_line_track_points(Vec2(-1.744, 0.870), Vec2(-4.095, -1.495), 8, rotation_offset=2 * pi)
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.525, 4.125), Vec2(-1.282, 1.334), 10, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0.0, 0.0), 1.85, 21, 148.932, 14.875),
        build_line_track_points(Vec2(-0.334, 1.849), Vec2(-3.853, 1.839), 9),
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.501, 4.101), Vec2(-1.183, 1.433), 9, fixed_rotation=True, rotation=45.2 * pi / 180),
        build_arc_track_points(Vec2(0.0, 0.0), 1.85, 19, 144.173, 14.653),
        build_line_track_points(Vec2(0.906, 1.708), Vec2(-1.443, 4.043), 8),
    ),
    # Outer loop
    connect_tracks(
        build_line_track_points(Vec2(1.637, 4.003), Vec2(0.230, 1.010), 8),
        build_arc_track_points(Vec2(2.2, -0.03), 2.23, 21, 164.156, 12.057, -4.0),
        build_line_track_points(Vec2(3.511, 1.960), Vec2(2.192, 3.906), 6),
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.637, 4.003), Vec2(0.230, 1.010), 8),
        build_arc_track_points(Vec2(2.2, -0.03), 2.23, 18, 164.135, 12.055, -4.0),
        build_line_track_points(Vec2(4.439, 0.807), Vec2(4.440, 1.272), 2),
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.633, 4.019), Vec2(0.230, 1.030), 8),
        build_arc_track_points(Vec2(2.2, -0.03), 2.23, 11, 163.772, 12.074, -4.0),
        build_line_track_points(Vec2(3.216, -2.094), Vec2(4.146, -1.894), 3),
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.639, 4.007), Vec2(0.244, 1.011), 8),
        build_arc_track_points(Vec2(2.2, -0.03), 2.23, 35, 163.948, 12.095, -4.0),
        build_line_track_points(Vec2(0.566, -1.765), Vec2(1.578, -3.900), 6, rotation_offset=2 * pi),
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.631, 4.005), Vec2(0.213, 1.042), 8),
        build_arc_track_points(Vec2(2.2, -0.03), 2.23, 31, 163.747, 12.071, -4.0),
        build_line_track_points(Vec2(-0.150, 0.071), Vec2(-1.633, -3.908), 10, rotation_offset=2 * pi),
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.642, 3.996), Vec2(0.223, 1.033), 8),
        build_arc_track_points(Vec2(2.2, -0.03), 2.23, 28, 163.555, 12.113, -4.0),
        build_line_track_points(Vec2(0.364, 1.385), Vec2(-3.937, -1.506), 12, rotation_offset=2 * pi),
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.642, 3.996), Vec2(0.223, 1.033), 8),
        build_arc_track_points(Vec2(2.2, -0.03), 2.23, 25, 163.502, 12.109, -4.0),
        build_line_track_points(Vec2(1.577, 2.173), Vec2(-4.070, 1.865), 13, rotation_offset=2 * pi),
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.630, 4.004), Vec2(0.223, 1.033), 8),
        build_arc_track_points(Vec2(2.2, -0.03), 2.23, 23, 163.444, 12.121, -4.0),
        build_line_track_points(Vec2(2.540, 2.272), Vec2(-1.278, 4.155), 10),
    ),
    # Refect
    connect_tracks(
        build_line_track_points(Vec2(1.398, 4.253), Vec2(-4.309, 1.889), 14),
        build_line_track_points(Vec2(-4.149, 1.845), Vec2(3.869, 1.845), 18),
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.398, 4.253), Vec2(-4.309, 1.889), 14),
        build_line_track_points(Vec2(-4.162, 1.736), Vec2(4.097, -1.681), 20),
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.398, 4.253), Vec2(-4.309, 1.889), 14),
        build_line_track_points(Vec2(-4.255, 1.650), Vec2(1.438, -4.022), 18),
    ),
    connect_tracks(
        build_line_track_points(Vec2(1.398, 4.253), Vec2(-4.309, 1.889), 14),
        build_line_track_points(Vec2(-4.307, 1.609), Vec2(-1.989, -4.079), 14),
    ),
    # Zigzag
    connect_tracks(
        build_line_track_points(Vec2(1.508, 4.102), Vec2(-1.642, 0.955), 11),
        build_line_track_points(Vec2(-1.423, 0.587), Vec2(1.636, -0.666), 8),
        build_line_track_points(Vec2(1.660, -0.933), Vec2(-1.676, -4.266), 11),
    ),
    # Wifi path
    build_line_track_points(Vec2(1.578, 3.894), Vec2(-1.225, -2.868), 11, fixed_rotation=True, rotation=0.0, progress_exponent=1.164),
    # Wifi stars paths
    build_line_track_points(_get_button_pos(1, SLIDE_UNIT), _get_button_pos(6, SLIDE_UNIT), 11, fixed_rotation=True, rotation=0.0),
    build_line_track_points(_get_button_pos(1, SLIDE_UNIT), _get_button_pos(5, SLIDE_UNIT), 11, fixed_rotation=True, rotation=0.0),
    build_line_track_points(_get_button_pos(1, SLIDE_UNIT), _get_button_pos(4, SLIDE_UNIT), 11, fixed_rotation=True, rotation=0.0),
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
    center = Layout.ring_center + point.position * Layout.ring_distance
    size = SLIDE_PATH_BASE_SIZE * Options.slide_scale * Layout.ring_distance
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
    center = Layout.ring_center + position.rotate(angle_offset) * Layout.ring_distance
    size = WIFI_SLIDE_PATH_BASE_SIZES[index] * Options.slide_scale * Layout.ring_distance
    layout = Rect.from_center(center, size).as_quad()
    if not is_mirrored:
        layout @= layout.scale_centered(Vec2(-1, 1))
    return layout.rotate_centered(angle_offset)

def layout_slide_head(progress: float, star_points: SlideTrackPointArray, button: Button, is_mirrored: bool):
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
        
    center = Layout.ring_center + point.position * Layout.ring_distance
    note_size = NOTE_BASE_SIZE * Layout.ring_distance * Options.note_scale
    layout = Rect.from_center(center, Vec2(note_size, note_size)).as_quad()
    return layout

