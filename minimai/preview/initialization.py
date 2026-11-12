from sonolus.script.archetype import PreviewArchetype, callback
from sonolus.script.printing import PrintColor, PrintFormat
from sonolus.script.quad import Rect
from sonolus.script.runtime import HorizontalAlign
from sonolus.script.timing import beat_to_time
from sonolus.script.vec import Vec2

from minimai.lib import archetype_names
from minimai.lib.skin import BaseSkin
from minimai.preview.ui import init_preview_ui
from minimai.preview.layout import (
    BAR_LINE_ALPHA,
    BAR_LINE_H,
    BEAT_LINE_ALPHA,
    BEAT_LINE_H,
    CENTER_LANE,
    CENTER_LINE_ALPHA,
    COLUMN_MARGIN_TOP,
    GROUP_MARK_H,
    GROUP_MARK_Y,
    LANE_NUMBER_H,
    LANE_NUMBER_PRINT_H,
    LANE_NUMBER_Y,
    PREVIEW_LABEL_ASPECT,
    HALF_BEAT_LINE_ALPHA,
    LANE_LINE_ALPHA,
    LANE_LINE_W,
    LANE_MAX,
    LANE_MIN,
    SENSOR_GROUP_STEP,
    SENSOR_LINE_ALPHA,
    SENSOR_LINE_W,
    PreviewData,
    get_column_bottom,
    get_column_end_time,
    init_preview_layout,
    layout_horizontal_line,
    layout_vertical_line,
    lane_to_x,
    print_in_view,
    time_to_y,
)

BEATS_PER_BAR = 4

Z_LANE_LINE = -100
Z_BEAT_LINE = -99
Z_LABEL = -98


class PreviewInitialization(PreviewArchetype):
    name = archetype_names.INITIALIZATION

    @callback(order=1)
    def preprocess(self):
        init_preview_layout()
        init_preview_ui()

    def render(self):
        for col in range(PreviewData.column_count):
            draw_lanes(col)
            draw_beat_lines(col)
            draw_lane_labels(col)
            print_column_time(col)


def draw_lanes(col: int):
    for i in range(8):
        lane = i + 0.0
        toward_center = 1.0
        if i >= 4:
            lane = i + 1.0
            toward_center = -1.0
        BaseSkin.white_square.draw(layout_vertical_line(lane, col, LANE_LINE_W), z=Z_LANE_LINE, a=LANE_LINE_ALPHA)
        for step in range(1, 4):
            sub_lane = lane + toward_center * step * SENSOR_GROUP_STEP
            BaseSkin.white_square.draw(
                layout_vertical_line(sub_lane, col, SENSOR_LINE_W), z=Z_LANE_LINE, a=SENSOR_LINE_ALPHA
            )
    BaseSkin.white_square.draw(layout_vertical_line(CENTER_LANE, col, LANE_LINE_W), z=Z_LANE_LINE, a=CENTER_LINE_ALPHA)


def draw_beat_lines(col: int):
    beat = PreviewData.column_beats[col]
    end_beat = PreviewData.column_beats[col + 1]
    while beat <= end_beat:
        if beat % BEATS_PER_BAR == 0:
            BaseSkin.white_square.draw(layout_horizontal_line(beat_to_time(beat), col, BAR_LINE_H), z=Z_BEAT_LINE, a=BAR_LINE_ALPHA)
        else:
            BaseSkin.white_square.draw(layout_horizontal_line(beat_to_time(beat), col, BEAT_LINE_H), z=Z_BEAT_LINE, a=BEAT_LINE_ALPHA)
        if beat < end_beat:
            BaseSkin.white_square.draw(
                layout_horizontal_line(beat_to_time(beat + 0.5), col, BEAT_LINE_H), z=Z_BEAT_LINE, a=HALF_BEAT_LINE_ALPHA
            )
        beat += 1


def print_column_time(col: int):
    """The column's end time, above its top left corner."""
    end_time = get_column_end_time(col)
    print_in_view(
        end_time,
        Vec2(lane_to_x(LANE_MIN, col), time_to_y(end_time, col) + COLUMN_MARGIN_TOP / 4),
        Vec2(0, 0),
        fmt=PrintFormat.TIME,
        decimal_places=2,
        color=PrintColor.CYAN,
        horizontal_align=HorizontalAlign.LEFT,
    )


def draw_lane_labels(col: int):
    """Under the column: the button numbers and C, with the B / D / E marks above them."""
    number_y = get_column_bottom() + LANE_NUMBER_Y
    mark_y = get_column_bottom() + GROUP_MARK_Y
    for i in range(8):
        button = i + 5
        lane = i + 0.0
        toward_center = 1.0
        if i >= 4:
            button = i - 3
            lane = i + 1.0
            toward_center = -1.0
        print_in_view(
            button,
            Vec2(lane_to_x(lane, col), number_y),
            Vec2(0.5, 0.5),
            fmt=PrintFormat.NUMBER,
            decimal_places=0,
            color=PrintColor.NEUTRAL,
            horizontal_align=HorizontalAlign.CENTER,
            height=LANE_NUMBER_PRINT_H,
        )
        # B, D, E (labels 0, 2, 3).
        for step in range(1, 4):
            label = step - 1
            if step > 1:
                label = step
            x = lane_to_x(lane + toward_center * step * SENSOR_GROUP_STEP, col)
            BaseSkin.preview_group_labels[label].draw(
                Rect.from_center(Vec2(x, mark_y), Vec2(GROUP_MARK_H * PREVIEW_LABEL_ASPECT, GROUP_MARK_H)),
                z=Z_LABEL,
            )
    # C, as big as the numbers.
    BaseSkin.preview_group_labels[1].draw(
        Rect.from_center(
            Vec2(lane_to_x(CENTER_LANE, col), number_y), Vec2(LANE_NUMBER_H * PREVIEW_LABEL_ASPECT, LANE_NUMBER_H)
        ),
        z=Z_LABEL,
    )
