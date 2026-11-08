from collections.abc import Iterable
from enum import IntEnum, auto
from typing import assert_never

from sonolus.script.interval import unlerp
from sonolus.script.runtime import time
from sonolus.script.quad import Quad, Rect
from sonolus.script.vec import Vec2

from minimai.lib.game import Sensor
from minimai.lib.options import Options
from minimai.lib.layout import (
    TOUCH_OVERLAP_BORDER_SIZE, get_sensor_pos_from_center, get_touch_fan_alpha, layout_px_size, layout_touch,
)
from minimai.lib.layer import ZIndexes, get_z, LAYER_TOUCH, LAYER_TOUCH_OVERLAP
from minimai.lib.skin import ActiveSkin
from minimai.lib.scoring import MAX_BREAK_WEIGHT, WeightedArchetype, init_life_loss

class TouchKind(IntEnum):
    NORM_TOUCH = auto()
    EX_TOUCH = auto()

    EACH_TOUCH = auto()
    EX_EACH_TOUCH = auto()

    BREAK_TOUCH = auto()
    EX_BREAK_TOUCH = auto()


def is_ex_touch(kind: TouchKind) -> bool:
    return kind in {TouchKind.EX_TOUCH, TouchKind.EX_EACH_TOUCH, TouchKind.EX_BREAK_TOUCH}


def is_break_touch(kind: TouchKind) -> bool:
    return kind in {TouchKind.BREAK_TOUCH, TouchKind.EX_BREAK_TOUCH}


def draw_touch(kind: TouchKind, sensor: Sensor, start_time: float, target_time: float):
    progress = unlerp(start_time, target_time, time())
    if progress < 0:
        return
    layout = layout_touch(progress, sensor)
    # Z Order: Border > Point > Bottom Fan > Top Fan > Right Fan > Left Fan 
    if progress >= 1:
        _border_1_draw(kind, layout.border, get_z(LAYER_TOUCH, target_time, 5))
    _point_draw(kind, layout.dot, get_z(LAYER_TOUCH, target_time, 4))
    alpha = get_touch_fan_alpha(progress)
    _fan_draw(kind, layout.bottom_fan, get_z(LAYER_TOUCH, target_time, 3), alpha)
    _fan_draw(kind, layout.top_fan, get_z(LAYER_TOUCH, target_time, 2), alpha)
    _fan_draw(kind, layout.right_fan, get_z(LAYER_TOUCH, target_time, 1), alpha)
    _fan_draw(kind, layout.left_fan, get_z(LAYER_TOUCH, target_time, 0), alpha)

def draw_touch_overlap(kind: TouchKind, sensor: Sensor, count: int):
    size = layout_px_size(TOUCH_OVERLAP_BORDER_SIZE, Options.touch_scale)
    layout = Rect.from_center(get_sensor_pos_from_center(sensor), Vec2(size, size)).as_quad()
    layer = get_z(LAYER_TOUCH_OVERLAP, 0, count).tuple
    match kind:
        case TouchKind.NORM_TOUCH | TouchKind.EX_TOUCH:
            ActiveSkin.normal_touch_overlap_border[count - 2].draw(layout, layer)
        case TouchKind.EACH_TOUCH | TouchKind.EX_EACH_TOUCH:
            ActiveSkin.each_touch_overlap_border[count - 2].draw(layout, layer)
        case TouchKind.BREAK_TOUCH | TouchKind.EX_BREAK_TOUCH:
            ActiveSkin.break_touch_overlap_border[count - 2].draw(layout, layer)
        case _:
            assert_never(kind)

def _point_draw(kind: TouchKind, layout: Quad, layer: ZIndexes, alpha: float = 1):
    match kind:
        case TouchKind.NORM_TOUCH | TouchKind.EX_TOUCH:
            ActiveSkin.normal_touch_point.draw(layout, layer.tuple, alpha)
        case TouchKind.EACH_TOUCH | TouchKind.EX_EACH_TOUCH:
            ActiveSkin.each_touch_point.draw(layout, layer.tuple, alpha)
        case TouchKind.BREAK_TOUCH | TouchKind.EX_BREAK_TOUCH:
            ActiveSkin.break_touch_point.draw(layout, layer.tuple, alpha)
        case _:
            assert_never(kind)

def _fan_draw(kind: TouchKind, layout: Quad, layer: ZIndexes, alpha: float = 1):
    match kind:
        case TouchKind.NORM_TOUCH | TouchKind.EX_TOUCH:
            ActiveSkin.normal_touch_fan.draw(layout, layer.tuple, alpha)
        case TouchKind.EACH_TOUCH | TouchKind.EX_EACH_TOUCH:
            ActiveSkin.each_touch_fan.draw(layout, layer.tuple, alpha)
        case TouchKind.BREAK_TOUCH | TouchKind.EX_BREAK_TOUCH:
            ActiveSkin.break_touch_fan.draw(layout, layer.tuple, alpha)
        case _:
            assert_never(kind)

def _border_1_draw(kind: TouchKind, layout: Quad, layer: ZIndexes, alpha: float = 1):
    ActiveSkin.touch_just_border.draw(layout, layer.tuple, alpha)

def get_touch_appear_duration(speed: float):
    close_speed = abs(Options.touch_speed * speed)
    close_duration = 3.209385682 * (close_speed ** -0.9549621752)
    return max(close_duration, 0.15)


def init_touch_score(archetypes: Iterable[type[WeightedArchetype]]):
    for archetype in archetypes:
        if not archetype.is_scored:
            continue
        weight = MAX_BREAK_WEIGHT if is_break_touch(archetype.key) else archetype.score_weight()
        archetype.archetype_score_multiplier = weight


def init_touch_life(archetypes: Iterable[type[WeightedArchetype]]):
    for archetype in archetypes:
        if not archetype.is_scored:
            continue
        weight = MAX_BREAK_WEIGHT if is_break_touch(archetype.key) else archetype.score_weight()
        init_life_loss(archetype, weight)
