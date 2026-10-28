from enum import IntEnum, auto
from typing import assert_never

from sonolus.script.interval import unlerp
from sonolus.script.quad import Quad
from sonolus.script.runtime import time

from minimai.lib.game import Sensor
from minimai.lib.layer import LAYER_TOUCH, LAYER_TOUCH_HOLD_BORDER, ZIndexes, get_z
from minimai.lib.layout import TouchHoldBorderLayout, get_touch_fan_alpha, layout_touch_hold
from minimai.lib.skin import ActiveSkin


class TouchHoldKind(IntEnum):
    NORM_TOUCH_HOLD = auto()
    EACH_TOUCH_HOLD = auto()
    BREAK_TOUCH_HOLD = auto()


class TouchHoldBorderState(IntEnum):
    # Not released (yet): the coloured border.
    ON = auto()
    # Released during the body: the grey border.
    OFF = auto()


def draw_touch_hold(
    kind: TouchHoldKind,
    sensor: Sensor,
    start_time: float,
    target_time: float,
    end_time: float,
    border_state: TouchHoldBorderState,
):
    progress = unlerp(start_time, target_time, time())
    if progress < 0:
        return
    layout = layout_touch_hold(progress, sensor)
    # Z order: point > fans 1..4 (fan 1 on top); the border is on its own layer below every touch.
    _point_draw(kind, layout.dot, get_z(LAYER_TOUCH, target_time, 0, 4))
    alpha = get_touch_fan_alpha(progress)
    for i in range(4):
        ActiveSkin.normal_touch_hold_fan[i].draw(layout.get_fan(i), get_z(LAYER_TOUCH, target_time, 0, 3 - i).tuple, alpha)

    if time() >= target_time:
        # The border fills from the head time to the end.
        border_progress = 1.0
        if end_time > target_time:
            border_progress = min((time() - target_time) / (end_time - target_time), 1)
        _border_draw(border_state, border_progress, sensor, layout.border, get_z(LAYER_TOUCH_HOLD_BORDER, target_time))


def _point_draw(kind: TouchHoldKind, layout: Quad, layer: ZIndexes):
    match kind:
        case TouchHoldKind.NORM_TOUCH_HOLD:
            ActiveSkin.normal_touch_point.draw(layout, layer.tuple)
        case TouchHoldKind.EACH_TOUCH_HOLD:
            ActiveSkin.each_touch_point.draw(layout, layer.tuple)
        case TouchHoldKind.BREAK_TOUCH_HOLD:
            ActiveSkin.break_touch_point.draw(layout, layer.tuple)
        case _:
            assert_never(kind)


def _border_draw(state: TouchHoldBorderState, progress: float, sensor: Sensor, full: Quad, layer: ZIndexes):
    if progress <= 0:
        return
    if progress >= 1:
        if state == TouchHoldBorderState.ON:
            ActiveSkin.touch_hold_border_on.draw(full, layer.tuple)
        else:
            ActiveSkin.touch_hold_border_off.draw(full, layer.tuple)
        return
    for piece in TouchHoldBorderLayout.build(progress, sensor).pieces:
        if state == TouchHoldBorderState.ON:
            ActiveSkin.touch_hold_border_on_bars[piece.side].draw(piece.quad, layer.tuple)
        else:
            ActiveSkin.touch_hold_border_off_bars[piece.side].draw(piece.quad, layer.tuple)
