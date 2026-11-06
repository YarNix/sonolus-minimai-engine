from collections.abc import Iterable
from enum import IntEnum, auto
from typing import assert_never

from sonolus.script.interval import unlerp
from sonolus.script.quad import Quad
from sonolus.script.runtime import time

from minimai.lib.game import Sensor
from minimai.lib.hold import HoldState
from minimai.lib.layer import LAYER_TOUCH, LAYER_TOUCH_HOLD_BORDER, ZIndexes, get_z
from minimai.lib.layout import TouchHoldBorderLayout, get_touch_fan_alpha, layout_touch_hold
from minimai.lib.skin import ActiveSkin
from minimai.lib.scoring import MAX_BREAK_WEIGHT, WeightedArchetype, init_life_loss


class TouchHoldKind(IntEnum):
    NORM_TOUCH_HOLD = auto()
    EACH_TOUCH_HOLD = auto()
    BREAK_TOUCH_HOLD = auto()

def draw_touch_hold(
    kind: TouchHoldKind,
    sensor: Sensor,
    start_time: float,
    target_time: float,
    end_time: float,
    state: HoldState,
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
        _border_draw(state, border_progress, sensor, layout.border, get_z(LAYER_TOUCH_HOLD_BORDER, target_time))


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


def _border_draw(state: HoldState, progress: float, sensor: Sensor, full: Quad, layer: ZIndexes):
    if progress <= 0:
        return
    is_on = state == HoldState.DEFAULT or state == HoldState.PRESSED
    if progress >= 1:
        if is_on:
            ActiveSkin.touch_hold_border_on.draw(full, layer.tuple)
        else:
            ActiveSkin.touch_hold_border_off.draw(full, layer.tuple)
        return
    for piece in TouchHoldBorderLayout.build(progress, sensor).pieces:
        if is_on:
            ActiveSkin.touch_hold_border_on_bars[piece.side].draw(piece.quad, layer.tuple)
        else:
            ActiveSkin.touch_hold_border_off_bars[piece.side].draw(piece.quad, layer.tuple)


def init_touch_hold_score(archetypes: Iterable[type[WeightedArchetype]]):
    for archetype in archetypes:
        if not archetype.is_scored:
            continue
        weight = MAX_BREAK_WEIGHT if archetype.key == TouchHoldKind.BREAK_TOUCH_HOLD else archetype.score_weight()
        archetype.archetype_score_multiplier = weight


def init_touch_hold_life(archetypes: Iterable[type[WeightedArchetype]]):
    for archetype in archetypes:
        if not archetype.is_scored:
            continue
        weight = MAX_BREAK_WEIGHT if archetype.key == TouchHoldKind.BREAK_TOUCH_HOLD else archetype.score_weight()
        init_life_loss(archetype, weight)
