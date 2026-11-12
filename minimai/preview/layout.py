from math import degrees

from sonolus.script.array import Array, Dim
from sonolus.script.globals import level_data
from sonolus.script.printing import PrintColor, PrintFormat, print_number
from sonolus.script.quad import Rect
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
# Lane labels, under each column: button numbers and C, with B / D / E marks above them.
LANE_NUMBER_H = 0.055
# The print box: digits fill about half of it, so this keeps them close to the C mark.
LANE_NUMBER_PRINT_H = 0.11
GROUP_MARK_H = 0.026
LANE_NUMBER_Y = -0.075
GROUP_MARK_Y = -0.03
# Width per unit of height of a group label sprite.
PREVIEW_LABEL_ASPECT = 0.75
# Width per unit of height of a slide shape label sprite; its shape is left-aligned in it.
PREVIEW_SHAPE_LABEL_ASPECT = 1.6

MAX_COLUMNS = 1000


ColumnBeats = Array[int, Dim[1001]]
assert MAX_COLUMNS + 1 == ColumnBeats.size()


@level_data
class PreviewData:
    # The end of the last note (chart time).
    max_time: float
    column_count: int
    # The beat each column starts on; one more entry for the end of the last column.
    column_beats: ColumnBeats


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
