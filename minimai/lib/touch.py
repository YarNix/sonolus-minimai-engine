from enum import IntEnum, auto
from typing import assert_never

from sonolus.script.interval import unlerp
from sonolus.script.runtime import time
from sonolus.script.quad import Quad

from minimai.lib.game import Sensor
from minimai.lib.options import Options
from minimai.lib.layout import layout_touch, get_touch_fan_alpha
from minimai.lib.layer import ZIndexes, get_z, LAYER_TOUCH
from minimai.lib.skin import ActiveSkin

class TouchKind(IntEnum):
    NORM_TOUCH = auto()
    EACH_TOUCH = auto()
    BREAK_TOUCH = auto()

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

def _point_draw(kind: TouchKind, layout: Quad, layer: ZIndexes, alpha: float = 1):
    match kind:
        case TouchKind.NORM_TOUCH:
            ActiveSkin.normal_touch_point.draw(layout, layer.tuple, alpha)
        case TouchKind.EACH_TOUCH:
            ActiveSkin.each_touch_point.draw(layout, layer.tuple, alpha)
        case TouchKind.BREAK_TOUCH:
            ActiveSkin.break_touch_point.draw(layout, layer.tuple, alpha)
        case _:
            assert_never(kind)

def _fan_draw(kind: TouchKind, layout: Quad, layer: ZIndexes, alpha: float = 1):
    match kind:
        case TouchKind.NORM_TOUCH:
            ActiveSkin.normal_touch_fan.draw(layout, layer.tuple, alpha)
        case TouchKind.EACH_TOUCH:
            ActiveSkin.each_touch_fan.draw(layout, layer.tuple, alpha)
        case TouchKind.BREAK_TOUCH:
            ActiveSkin.break_touch_fan.draw(layout, layer.tuple, alpha)
        case _:
            assert_never(kind)

def _border_1_draw(kind: TouchKind, layout: Quad, layer: ZIndexes, alpha: float = 1):
    ActiveSkin.touch_just_border.draw(layout, layer.tuple, alpha)

def get_touch_appear_duration(speed: float):
    close_speed = abs(Options.touch_speed * speed)
    close_duration = 3.209385682 * (close_speed ** -0.9549621752)
    return max(close_duration, 0.15)