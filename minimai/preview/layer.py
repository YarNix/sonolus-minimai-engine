from minimai.preview.layout import CENTER_LANE

# Draw order, bottom to top. The frame (lines and lane labels) is under every note.
LAYER_LANE_LINE = -3
LAYER_BEAT_LINE = -2
LAYER_LANE_LABEL = -1
LAYER_FIREWORK = 0
LAYER_EACH_LINE = 1
LAYER_TOUCH_HOLD_BAR = 2
LAYER_TOUCH = 3
LAYER_HOLD = 4
LAYER_SLIDE_WAIT = 5
LAYER_SLIDE = 6
LAYER_SHAPE_LABEL = 7
LAYER_HOLD_END_POINT = 8
LAYER_NOTE = 9
LAYER_EX_OUTLINE = 10

# Within a touch: its fans, then its point on top.
TOUCH_POINT_ORDER = 4


def get_z(layer: int, lane: float, time: float, order: int = 0) -> tuple[float, float, float, float]:
    """Within a layer, a note further from the column's center (C) is drawn over a nearer one (1 under
    2 under 3, 8 under 7 under 6), then a later one over an earlier one, then by ``order``."""
    return layer, abs(lane - CENTER_LANE), time, order


def get_frame_z(layer: int) -> tuple[float, float, float, float]:
    return layer, 0, 0, 0


def get_hold_z(time: float, lane: float, ex_outline: bool) -> tuple[float, float, float, float]:
    """A hold's caps and body; its EX outline goes over every note."""
    layer = LAYER_HOLD
    if ex_outline:
        layer = LAYER_EX_OUTLINE
    return get_z(layer, lane, time)


def get_touch_fan_z(lane: float, time: float, index: int) -> tuple[float, float, float, float]:
    return get_z(LAYER_TOUCH, lane, time, index)


def get_touch_hold_fan_z(lane: float, time: float, index: int) -> tuple[float, float, float, float]:
    """Fan 1 on top, as in play."""
    return get_z(LAYER_TOUCH, lane, time, 3 - index)


def get_touch_point_z(lane: float, time: float) -> tuple[float, float, float, float]:
    return get_z(LAYER_TOUCH, lane, time, TOUCH_POINT_ORDER)


def get_each_line_z(time: float) -> tuple[float, float, float, float]:
    return get_z(LAYER_EACH_LINE, CENTER_LANE, time)
