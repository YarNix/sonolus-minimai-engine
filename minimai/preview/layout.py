from math import atan2, degrees, floor, pi

from sonolus.script.array import Array, Dim
from sonolus.script.containers import VarArray
from sonolus.script.globals import level_data
from sonolus.script.interval import clamp
from sonolus.script.printing import PrintColor, PrintFormat, print_number
from sonolus.script.quad import Quad, Rect
from sonolus.script.record import Record
from sonolus.script.runtime import (
    HorizontalAlign,
    ScrollDirection,
    canvas,
    runtime_ui,
    safe_area,
    screen,
    set_skin_transform,
)
from sonolus.script.timing import beat_to_time
from sonolus.script.transform import Transform2d
from sonolus.script.vec import Vec2

from minimai.lib.game import Button, Sensor, SensorGroup, sensor_offset, sensor_to_group
from minimai.lib.layout import Orientation, get_orientation_angle
from minimai.lib.slide import SlideTrackKind, get_slide_area_count, get_slide_area_sensor
from minimai.lib.options import Options

# Lane positions, in lanes: 5 6 7 8 at 0..3, C at 4, 1 2 3 4 at 5..8. B, D and E sit 0.25, 0.5 and
# 0.75 lanes from their A, towards C.
CENTER_LANE = 4.0
LANE_MIN = -0.5
LANE_MAX = 8.5
SENSOR_GROUP_STEP = 0.25

LANE_W = 0.12
COLUMN_MARGIN_X = 0.1
COLUMN_W = (LANE_MAX - LANE_MIN) * LANE_W + 2 * COLUMN_MARGIN_X
# Above the columns: their end times. Below: the lane labels, then the progress bar.
COLUMN_MARGIN_TOP = 0.125
UI_GAP = 0.05
PROGRESS_H = 0.15
MENU_SIZE = 0.15
LABEL_AREA_H = 0.11
# Column height per second; a column holds up to 2 s in landscape (no safe area inset, UI scale 1).
UNITS_PER_SECOND = (2 - COLUMN_MARGIN_TOP - UI_GAP - PROGRESS_H - LABEL_AREA_H) / 2

LANE_LINE_W = 0.006
SENSOR_LINE_W = 0.003
BEAT_LINE_H = 0.004
BAR_LINE_H = 0.008
LANE_LINE_ALPHA = 0.35
SENSOR_LINE_ALPHA = 0.12
CENTER_LINE_ALPHA = 0.5
BAR_LINE_ALPHA = 0.6
BEAT_LINE_ALPHA = 0.3
HALF_BEAT_LINE_ALPHA = 0.12

TEXT_H = 0.08
TEXT_W = 0.5
# The BPM label's right edge, past the last lane's edge (into the column's margin).
BPM_LABEL_SHIFT = 0.06
# Lane labels, under each column: button numbers and C, with B / D / E marks above them.
LANE_NUMBER_H = 0.055
# The print box: digits fill about half of it, so this keeps them close to the C mark.
LANE_NUMBER_PRINT_H = 0.11
GROUP_MARK_H = 0.026
LANE_NUMBER_Y = -0.075
GROUP_MARK_Y = -0.03
# Width per unit of height of a group label sprite.
PREVIEW_LABEL_ASPECT = 1.0
# Width per unit of height of a slide shape label sprite; its shape is left-aligned in it.
PREVIEW_SHAPE_LABEL_ASPECT = 1.6

# Taps, stars and holds: 1.09 lanes across; a hold is 0.64 of that wide.
NOTE_SIZE = 0.95 * 1.15 * LANE_W
HOLD_WIDTH = 0.64 * NOTE_SIZE
# Head and tail caps of the hold sprites: 58 px tall on a 122 px wide sprite.
HOLD_CAP_H = HOLD_WIDTH * 58 / 122
# How far a hold reaches past its head and end times, cap included: as far as a tap does.
HOLD_OVERHANG = NOTE_SIZE * 2 / 5
# The end point marks at a hold's head and end times: 64 px against a 180 px note.
HOLD_END_POINT_SIZE = NOTE_SIZE * 64 / 180
# The firework halo behind a note (``Mai Preview Firework``, its rays drawn from half its radius out).
# The rays start 0.21 notes out, inside the star's shallowest dip, so none floats free of a star.
FIREWORK_HALO_RADIUS = 0.42 * NOTE_SIZE
EACH_LINE_H = 0.012
# Touches and touch holds: their play sprites at 0.9 of a skin pixel per (unenlarged) note pixel.
TOUCH_PX = 0.9 * 0.95 * LANE_W / 180
TOUCH_FAN_W = 112 * TOUCH_PX
TOUCH_FAN_H = 82 * TOUCH_PX
# From the point to the middle of each closed fan.
TOUCH_FAN_OFFSET = 22.6 * TOUCH_PX
TOUCH_HOLD_FAN_OFFSET = 1.05 * TOUCH_FAN_OFFSET
TOUCH_POINT_SIZE = 1.2 * 32 * TOUCH_PX
# The bar from a touch hold's head to its end, in 4 equal parts coloured like its fans.
TOUCH_HOLD_BAR_W = 0.15 * LANE_W
TOUCH_HOLD_BAR_PARTS = 4
# Slide bars (``Mai Slide Path``, 70 x 94 px, pointing left in the sprite), at 1.1 skin pixels per
# (unenlarged) note pixel, one every 0.33 lanes along the track. The wait's are smaller.
SLIDE_PX = 1.1 * 0.95 * LANE_W / 180
SLIDE_BAR_W = 70 * SLIDE_PX
SLIDE_BAR_H = 94 * SLIDE_PX
SLIDE_BAR_SPACING = 0.33 * LANE_W
SLIDE_WAIT_SCALE = 0.8
# The wait's slide bars fade in from the slide's time to the start of its travel (ease-out quad).
SLIDE_WAIT_ALPHA_START = 0.2
SLIDE_WAIT_ALPHA_END = 0.8
# The wait's last slide bar is left out if it would sit closer than this (in spacings) to the travel's first.
SLIDE_WAIT_END_GAP = 0.6
# The shape label at the start of the travel, this far right of the wait's slide bars.
SHAPE_LABEL_H = 0.45 * LANE_W
SHAPE_LABEL_GAP = 0.05 * LANE_W

MAX_COLUMNS = 1000
# Combo bins, one per beat; notes judged later than this count in the last bin.
MAX_COMBO_BEATS = 2048


ColumnBeats = Array[int, Dim[1001]]
assert MAX_COLUMNS + 1 == ColumnBeats.size()
ComboBins = Array[int, Dim[2048]]
assert MAX_COMBO_BEATS == ComboBins.size()


@level_data
class PreviewData:
    # The end of the last note (chart time).
    max_time: float
    column_count: int
    # The beat each column starts on; one more entry for the end of the last column.
    column_beats: ColumnBeats
    # Notes judged in each beat; turned into running totals once the columns are built.
    combo: ComboBins


@level_data
class PreviewLayout:
    # The view (the screen as the player holds it), turned onto the screen by view_angle.
    view_angle: float
    view: Rect
    # The view's safe area, less the gap at its edges; the UI sits in it.
    ui_box: Rect
    column_bottom: float
    column_top: float
    # A column's time limit (2 s in landscape, longer in portrait).
    column_seconds: float


def report_end_time(time: float):
    """Preprocess: a note that lasts until ``time``."""
    PreviewData.max_time = max(PreviewData.max_time, time)


def report_judgment_beat(beat: float):
    """Preprocess: a scored note judged at ``beat`` (for the combo above each column)."""
    index = clamp(floor(beat), 0, MAX_COMBO_BEATS - 1)
    PreviewData.combo[index] += 1


def total_combo():
    """Preprocess, after every note: the bins become running totals."""
    total = 0
    for i in range(MAX_COMBO_BEATS):
        total += PreviewData.combo[i]
        PreviewData.combo[i] = total


def get_combo_at_column_end(col: int) -> int:
    """Notes judged before the column's end."""
    return PreviewData.combo[clamp(PreviewData.column_beats[col + 1] - 1, 0, MAX_COMBO_BEATS - 1)]


def get_scroll_direction(orientation: Orientation) -> ScrollDirection:
    """The view's +x on the screen: the way the columns run."""
    result = ScrollDirection.LEFT_TO_RIGHT
    if orientation == Orientation.LANDSCAPE_REVERSED:
        result = ScrollDirection.RIGHT_TO_LEFT
    elif orientation == Orientation.PORTRAIT:
        result = ScrollDirection.BOTTOM_TO_TOP
    elif orientation == Orientation.PORTRAIT_REVERSED:
        result = ScrollDirection.TOP_TO_BOTTOM
    return result


def init_preview_layout():
    """Preprocess, after every note has reported its end time."""
    PreviewLayout.view_angle = get_orientation_angle(Options.orientation)
    s = screen()
    if Options.orientation == Orientation.PORTRAIT or Options.orientation == Orientation.PORTRAIT_REVERSED:
        PreviewLayout.view @= Rect(l=s.b, r=s.t, b=s.l, t=s.r)
    else:
        PreviewLayout.view @= s
    if Options.orientation != Orientation.LANDSCAPE:
        set_skin_transform(Transform2d.new().rotate(PreviewLayout.view_angle))
    PreviewLayout.ui_box @= to_view_rect(safe_area()).shrink(Vec2(UI_GAP, UI_GAP))
    PreviewLayout.column_bottom = (
        PreviewLayout.ui_box.b + PROGRESS_H * runtime_ui().progress_config.scale + LABEL_AREA_H
    )
    PreviewLayout.column_top = PreviewLayout.view.t - COLUMN_MARGIN_TOP
    PreviewLayout.column_seconds = get_column_height() / UNITS_PER_SECOND
    build_columns()
    total_combo()
    canvas().update(
        scroll_direction=get_scroll_direction(Options.orientation),
        size=COLUMN_W * PreviewData.column_count,
    )


def build_columns():
    """Each column ends on the last beat line within the time limit; a beat longer than the limit
    gets a column of its own."""
    beat = 0
    count = 0
    while (count == 0 or beat_to_time(beat) < PreviewData.max_time) and count < MAX_COLUMNS:
        PreviewData.column_beats[count] = beat
        start_time = beat_to_time(beat)
        end_beat = beat + 1
        while beat_to_time(end_beat + 1) <= start_time + PreviewLayout.column_seconds + 1e-6:
            end_beat += 1
        beat = end_beat
        count += 1
    PreviewData.column_beats[count] = beat
    PreviewData.column_count = count


def to_view(point: Vec2) -> Vec2:
    return point.rotate(-PreviewLayout.view_angle)


def to_screen(point: Vec2) -> Vec2:
    return point.rotate(PreviewLayout.view_angle)


def to_view_rect(rect: Rect) -> Rect:
    a = to_view(Vec2(rect.l, rect.b))
    b = to_view(Vec2(rect.r, rect.t))
    return Rect(l=min(a.x, b.x), r=max(a.x, b.x), b=min(a.y, b.y), t=max(a.y, b.y))


def get_column_height() -> float:
    return PreviewLayout.column_top - PreviewLayout.column_bottom


def get_column_start_time(col: int) -> float:
    return beat_to_time(PreviewData.column_beats[col])


def get_column_end_time(col: int) -> float:
    return beat_to_time(PreviewData.column_beats[col + 1])


def get_column_scale(col: int) -> float:
    """Units per second: the same in every column, except a 1-beat column squeezed to fit."""
    duration = get_column_end_time(col) - get_column_start_time(col)
    return get_column_height() / max(PreviewLayout.column_seconds, duration)


def time_to_col(time: float) -> int:
    """The column holding ``time`` (a time on a column boundary belongs to the later column)."""
    lo = 0
    hi = PreviewData.column_count - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if get_column_start_time(mid) <= time:
            lo = mid
        else:
            hi = mid - 1
    return lo


def time_to_y(time: float, col: int) -> float:
    return get_column_bottom() + (time - get_column_start_time(col)) * get_column_scale(col)


def get_column_bottom() -> float:
    return PreviewLayout.column_bottom


def get_column_top(col: int) -> float:
    return time_to_y(get_column_end_time(col), col)


def get_column_left(col: int) -> float:
    return PreviewLayout.view.l + col * COLUMN_W


def lane_to_x(lane: float, col: int) -> float:
    return get_column_left(col) + COLUMN_MARGIN_X + (lane - LANE_MIN) * LANE_W


def get_button_lane(button: Button) -> float:
    """5 6 7 8 on the left, 1 2 3 4 on the right."""
    result = button + 4.0
    if button >= 5:
        result = button - 5.0
    return result


def get_sensor_lane(sensor: Sensor) -> float:
    group = sensor_to_group(sensor)
    result = CENTER_LANE
    if group != SensorGroup.C:
        button = sensor_offset(sensor) + 1
        step = 0.0
        match group:
            case SensorGroup.B:
                step = 1.0
            case SensorGroup.D:
                step = 2.0
            case SensorGroup.E:
                step = 3.0
            case _:
                step = 0.0
        toward_center = 1.0
        if button <= 4:
            toward_center = -1.0
        result = get_button_lane(button) + toward_center * step * SENSOR_GROUP_STEP
    return result


def layout_vertical_line(lane: float, col: int, width: float) -> Rect:
    x = lane_to_x(lane, col)
    return Rect(l=x - width / 2, r=x + width / 2, b=get_column_bottom(), t=get_column_top(col))


def layout_horizontal_line(time: float, col: int, height: float) -> Rect:
    y = time_to_y(time, col)
    return Rect(l=lane_to_x(LANE_MIN, col), r=lane_to_x(LANE_MAX, col), b=y - height / 2, t=y + height / 2)


def print_in_view(
    value: float,
    position: Vec2,
    pivot: Vec2,
    *,
    fmt: PrintFormat,
    color: PrintColor,
    horizontal_align: HorizontalAlign,
    decimal_places: int = -1,
    height: float = TEXT_H,
):
    """``print_number`` at a view position: the skin transform doesn't turn prints."""
    print_number(
        value,
        fmt=fmt,
        decimal_places=decimal_places,
        anchor=to_screen(position),
        pivot=pivot,
        dimensions=Vec2(TEXT_W, height),
        rotation=degrees(PreviewLayout.view_angle),
        color=color,
        horizontal_align=horizontal_align,
    )


def layout_note(lane: float, time: float) -> Rect:
    col = time_to_col(time)
    return Rect.from_center(Vec2(lane_to_x(lane, col), time_to_y(time, col)), Vec2(NOTE_SIZE, NOTE_SIZE))


def layout_firework(lane: float, time: float) -> Rect:
    col = time_to_col(time)
    return Rect.from_center(
        Vec2(lane_to_x(lane, col), time_to_y(time, col)), Vec2(2 * FIREWORK_HALO_RADIUS, 2 * FIREWORK_HALO_RADIUS)
    )


def layout_each_line(left_lane: float, right_lane: float, time: float) -> Rect:
    col = time_to_col(time)
    y = time_to_y(time, col)
    return Rect(
        l=lane_to_x(min(left_lane, right_lane), col),
        r=lane_to_x(max(left_lane, right_lane), col),
        b=y - EACH_LINE_H / 2,
        t=y + EACH_LINE_H / 2,
    )


def layout_hold_body(lane: float, start_time: float, end_time: float, col: int) -> Rect:
    """The part of a hold body that falls in column ``col``: from its head time to its end time,
    reaching past both up to the caps."""
    x = lane_to_x(lane, col)
    bottom = time_to_y(max(start_time, get_column_start_time(col)), col)
    top = time_to_y(min(end_time, get_column_end_time(col)), col)
    if time_to_col(start_time) == col:
        bottom -= HOLD_OVERHANG - HOLD_CAP_H
    if time_to_col(end_time) == col:
        top += HOLD_OVERHANG - HOLD_CAP_H
    return Rect(l=x - HOLD_WIDTH / 2, r=x + HOLD_WIDTH / 2, b=bottom, t=max(top, bottom))


def layout_hold_tail_cap(lane: float, time: float) -> Rect:
    """The v cap, its tip ``HOLD_OVERHANG`` under the head time."""
    col = time_to_col(time)
    x = lane_to_x(lane, col)
    y = time_to_y(time, col) - HOLD_OVERHANG
    return Rect(l=x - HOLD_WIDTH / 2, r=x + HOLD_WIDTH / 2, b=y, t=y + HOLD_CAP_H)


def layout_hold_head_cap(lane: float, time: float) -> Rect:
    """The ^ cap, its tip ``HOLD_OVERHANG`` over the end time."""
    col = time_to_col(time)
    x = lane_to_x(lane, col)
    y = time_to_y(time, col) + HOLD_OVERHANG
    return Rect(l=x - HOLD_WIDTH / 2, r=x + HOLD_WIDTH / 2, b=y - HOLD_CAP_H, t=y)


def layout_hold_end_point(lane: float, time: float) -> Rect:
    col = time_to_col(time)
    return Rect.from_center(
        Vec2(lane_to_x(lane, col), time_to_y(time, col)), Vec2(HOLD_END_POINT_SIZE, HOLD_END_POINT_SIZE)
    )


def get_note_center(lane: float, time: float) -> Vec2:
    col = time_to_col(time)
    return Vec2(lane_to_x(lane, col), time_to_y(time, col))


def layout_touch_point(lane: float, time: float) -> Rect:
    return Rect.from_center(get_note_center(lane, time), Vec2(TOUCH_POINT_SIZE, TOUCH_POINT_SIZE))


def layout_touch_fan(lane: float, time: float, angle: float, offset: float) -> Quad:
    """A closed fan, its tip toward the point: the one under the point, turned ``angle``
    counterclockwise about it."""
    center = get_note_center(lane, time)
    fan = Rect.from_center(center + Vec2(0, -offset), Vec2(TOUCH_FAN_W, TOUCH_FAN_H))
    return fan.as_quad().rotate_about(angle, pivot=center)


def get_touch_fan_angle(index: int) -> float:
    """Touch fans: under, right of, over and left of the point."""
    return index * pi / 2


def get_touch_hold_fan_angle(index: int) -> float:
    """Touch hold fans 1..4 (index 0..3): top right, bottom right, bottom left, top left."""
    return 3 * pi / 4 - index * pi / 2


def layout_touch_hold_bar(lane: float, start_time: float, end_time: float, col: int, flipped: bool) -> Quad:
    """The part of a touch hold bar (or of one of its parts) from ``start_time`` to ``end_time`` that
    falls in column ``col``. The bar sprites are border cross-sections, so they lie on their side;
    ``flipped`` turns one the other way."""
    x = lane_to_x(lane, col)
    bottom = time_to_y(max(start_time, get_column_start_time(col)), col)
    top = time_to_y(min(end_time, get_column_end_time(col)), col)
    left = x - TOUCH_HOLD_BAR_W / 2
    right = x + TOUCH_HOLD_BAR_W / 2
    if flipped:
        left, right = right, left
    return Quad(bl=Vec2(right, bottom), br=Vec2(right, top), tr=Vec2(left, top), tl=Vec2(left, bottom))


# Slides: a track on the lanes, straight runs over every sensor of its judgment areas, turning only
# where it turns back across the lanes or wraps round the column's edges, with one slope (lanes per
# second) for the whole travel.

class SlideTrackPoint(Record):
    lane: float
    time: float
    # The track jumps here (from the other edge of the column) instead of running on from the last point.
    jump: bool


SlideTrackPoints = VarArray[SlideTrackPoint, Dim[40]]
SensorList = VarArray[Sensor, Dim[16]]


def get_sensor_ring_angle(sensor: Sensor) -> float:
    """Degrees clockwise from the top of the ring (C has none: -1)."""
    group = sensor_to_group(sensor)
    result = -1.0
    if group == SensorGroup.A or group == SensorGroup.B:
        result = 22.5 + 45 * sensor_offset(sensor)
    elif group == SensorGroup.D or group == SensorGroup.E:
        result = 45.0 * sensor_offset(sensor)
    return result


def wrap_degrees(value: float) -> float:
    return value - 360 * floor(value / 360)


def crosses_bottom(a: Sensor, b: Sensor) -> bool:
    """Whether going the short way round the ring from ``a`` to ``b`` passes the bottom (between 4
    and 5), where the lanes are cut."""
    angle_a = get_sensor_ring_angle(a)
    angle_b = get_sensor_ring_angle(b)
    result = False
    if angle_a >= 0 and angle_b >= 0:
        turn = wrap_degrees(angle_b - angle_a + 180) - 180
        to_bottom = wrap_degrees(180 - angle_a)
        if turn > 0:
            result = 0 < to_bottom <= turn
        elif turn < 0:
            result = 0 < wrap_degrees(angle_a - 180) <= -turn
    return result


def get_wrap_distance(lane_a: float, lane_b: float) -> float:
    """Lanes from ``lane_a`` out to its side's edge, plus in from the other edge to ``lane_b``."""
    out = lane_a - LANE_MIN
    if lane_a > CENTER_LANE:
        out = LANE_MAX - lane_a
    back = LANE_MAX - lane_b
    if lane_b < CENTER_LANE:
        back = lane_b - LANE_MIN
    return out + back


def build_slide_track(
    track: SlideTrackKind, button: Button, is_mirrored: bool, start_time: float, end_time: float
) -> SlideTrackPoints:
    sensors = SensorList.new()
    for i in range(get_slide_area_count(track)):
        sensors.append(get_slide_area_sensor(track, i, 0, button, is_mirrored))
    count = len(sensors)

    # The turning points: the ends, where the path turns back across the lanes, and both ends of a wrap.
    kept = VarArray[int, Dim[16]].new()
    kept.append(0)
    for i in range(1, count - 1):
        before = get_sensor_lane(sensors[i]) - get_sensor_lane(sensors[i - 1])
        after = get_sensor_lane(sensors[i + 1]) - get_sensor_lane(sensors[i])
        if (
            before * after < 0
            or crosses_bottom(sensors[i - 1], sensors[i])
            or crosses_bottom(sensors[i], sensors[i + 1])
        ):
            kept.append(i)
    if count > 1:
        kept.append(count - 1)

    # One slope: time follows the lanes crossed.
    total = 0.0
    for k in range(1, len(kept)):
        total += get_run_length(sensors, kept[k - 1], kept[k])

    path = SlideTrackPoints.new()
    path.append(SlideTrackPoint(lane=get_sensor_lane(sensors[0]), time=start_time, jump=False))
    done = 0.0
    for k in range(1, len(kept)):
        a = kept[k - 1]
        b = kept[k]
        lane_a = get_sensor_lane(sensors[a])
        lane_b = get_sensor_lane(sensors[b])
        length = get_run_length(sensors, a, b)
        time_a = get_track_time(start_time, end_time, done, total, k - 1, len(kept) - 1)
        time_b = get_track_time(start_time, end_time, done + length, total, k, len(kept) - 1)
        if b == a + 1 and crosses_bottom(sensors[a], sensors[b]):
            out_edge = LANE_MIN
            in_edge = LANE_MAX
            out_length = lane_a - LANE_MIN
            if lane_a > CENTER_LANE:
                out_edge = LANE_MAX
                in_edge = LANE_MIN
                out_length = LANE_MAX - lane_a
            edge_time = time_a + (time_b - time_a) * out_length / max(length, 1e-6)
            path.append(SlideTrackPoint(lane=out_edge, time=edge_time, jump=False))
            path.append(SlideTrackPoint(lane=in_edge, time=edge_time, jump=True))
        path.append(SlideTrackPoint(lane=lane_b, time=time_b, jump=False))
        done += length
    return path


def get_run_length(sensors: SensorList, a: int, b: int) -> float:
    lane_a = get_sensor_lane(sensors[a])
    lane_b = get_sensor_lane(sensors[b])
    result = abs(lane_b - lane_a)
    if b == a + 1 and crosses_bottom(sensors[a], sensors[b]):
        result = get_wrap_distance(lane_a, lane_b)
    return result


def get_track_time(start_time: float, end_time: float, done: float, total: float, index: int, last: int) -> float:
    """By the lanes crossed; evenly by turning point if the path never leaves its lane."""
    fraction = index / max(last, 1)
    if total > 0:
        fraction = done / total
    return start_time + (end_time - start_time) * fraction


def get_slide_track_length(path: SlideTrackPoints) -> float:
    total = 0.0
    for i in range(1, len(path)):
        if not path[i].jump:
            a = path[i - 1]
            b = path[i]
            for col in range(time_to_col(min(a.time, b.time)), time_to_col(max(a.time, b.time)) + 1):
                piece = clip_to_column(a, b, col)
                if piece.inside:
                    total += (piece.end - piece.start).magnitude
    return total


def get_clip_times(a: SlideTrackPoint, b: SlideTrackPoint, col: int) -> Vec2:
    """The part of the run from ``a`` to ``b`` inside column ``col``, as fractions of the run (x to y)."""
    lo = 0.0
    hi = 1.0
    duration = b.time - a.time
    if duration > 0:
        lo = max(0.0, (get_column_start_time(col) - a.time) / duration)
        hi = min(1.0, (get_column_end_time(col) - a.time) / duration)
    return Vec2(lo, hi)


def get_piece_fraction(a: SlideTrackPoint, b: SlideTrackPoint, col: int, u: float) -> float:
    clip = get_clip_times(a, b, col)
    return clip.x + (clip.y - clip.x) * u


class ColumnPiece(Record):
    inside: bool
    start: Vec2
    end: Vec2


def clip_to_column(a: SlideTrackPoint, b: SlideTrackPoint, col: int) -> ColumnPiece:
    """The run's ends inside column ``col``, in view coordinates; not ``inside`` if no part of it is
    (a run at a single time is in that time's column)."""
    clip = get_clip_times(a, b, col)
    inside = clip.x <= clip.y
    if b.time <= a.time:
        inside = time_to_col(a.time) == col
    time_lo = a.time + (b.time - a.time) * clip.x
    time_hi = a.time + (b.time - a.time) * clip.y
    lane_lo = a.lane + (b.lane - a.lane) * clip.x
    lane_hi = a.lane + (b.lane - a.lane) * clip.y
    return ColumnPiece(
        inside=inside,
        start=Vec2(lane_to_x(lane_lo, col), time_to_y(time_lo, col)),
        end=Vec2(lane_to_x(lane_hi, col), time_to_y(time_hi, col)),
    )


def layout_slide_bar(center: Vec2, direction: Vec2, scale: float) -> Quad:
    """A slide bar pointing along ``direction`` (the sprite points left)."""
    angle = pi / 2
    if direction.magnitude > 0:
        angle = atan2(direction.y, direction.x)
    rect = Rect.from_center(center, Vec2(SLIDE_BAR_W, SLIDE_BAR_H) * scale)
    return rect.as_quad().rotate_about(angle - pi, pivot=center)


def build_wait_track(lane: float, start_time: float, end_time: float) -> SlideTrackPoints:
    """A slide's wait: straight up its start lane."""
    track = SlideTrackPoints.new()
    track.append(SlideTrackPoint(lane=lane, time=start_time, jump=False))
    track.append(SlideTrackPoint(lane=lane, time=end_time, jump=False))
    return track


def layout_shape_label(lane: float, time: float) -> Rect:
    """Left-aligned just right of the wait's slide bars, sitting on the start of the travel: the sprite's
    baseline is 0.32 of its height up, so even "-" stays clear of a beat line there."""
    col = time_to_col(time)
    left = lane_to_x(lane, col) + SLIDE_BAR_H * SLIDE_WAIT_SCALE / 2 + SHAPE_LABEL_GAP
    y = time_to_y(time, col)
    return Rect(l=left, r=left + SHAPE_LABEL_H * PREVIEW_SHAPE_LABEL_ASPECT, b=y - SHAPE_LABEL_H, t=y)
