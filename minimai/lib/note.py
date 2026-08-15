from enum import IntEnum, auto
from math import atan, ceil, cos, floor, log, pi, sin
from typing import assert_never

from sonolus.script.quad import Quad
from sonolus.script.vec import Vec2
from sonolus.script.sprite import Sprite
from sonolus.script.interval import unlerp
from sonolus.script.runtime import time
from sonolus.script.bucket import Bucket

from minimai.lib.skin import ActiveSkin
from minimai.lib.level_config import LevelConfig
from minimai.lib.layout import Button, get_line_alpha, layout_note, layout_line, get_button_angle_vertical, DISTANCE_TRAVEL, NOTE_SCALE_RATE
from minimai.lib.layer import ZIndexes, get_z, LAYER_NOTE, LAYER_EX, LAYER_NOTE_LINE
from minimai.lib.buckets import Buckets


class NoteKind(IntEnum):
    NORM_TAP = auto()
    EX_TAP = auto()

    EACH_TAP = auto()
    EX_EACH_TAP = auto()

    BREAK_TAP = auto()
    EX_BREAK_TAP = auto()

    NORM_STAR = auto()
    EX_STAR = auto()

    EACH_STAR = auto()
    EX_EACH_STAR = auto()

    BREAK_STAR = auto()
    EX_BREAK_STAR = auto()

    DOUBLE_STAR = auto()
    EX_DOUBLE_STAR = auto()

    EACH_DOUBLE_STAR = auto()
    EX_EACH_DOUBLE_STAR = auto()

    BREAK_DOUBLE_STAR = auto()
    EX_BREAK_DOUBLE_STAR = auto()

def get_note_bucket(kind: NoteKind) -> Bucket:
    result = Bucket(-1)
    match kind:
        case NoteKind.NORM_TAP | NoteKind.EACH_TAP \
            | NoteKind.NORM_STAR | NoteKind.EACH_STAR \
            | NoteKind.DOUBLE_STAR | NoteKind.EACH_DOUBLE_STAR:
            result @= Buckets.standard_tap
        case NoteKind.BREAK_TAP | NoteKind.BREAK_STAR | NoteKind.BREAK_DOUBLE_STAR:
            result @= Buckets.break_tap
        case NoteKind.EX_TAP | NoteKind.EX_EACH_TAP | NoteKind.EX_BREAK_TAP \
            | NoteKind.EX_STAR | NoteKind.EX_EACH_STAR | NoteKind.EX_BREAK_STAR \
            | NoteKind.EX_DOUBLE_STAR | NoteKind.EX_EACH_DOUBLE_STAR | NoteKind.EX_BREAK_DOUBLE_STAR:
            result @= Buckets.ex_tap
        # case NoteKind.OTHER
        #    result @= Bucket(-1)
        case _:
            assert_never(kind)
    return result

def is_ex(kind: NoteKind):
    ex_kinds = {
        NoteKind.EX_TAP, NoteKind.EX_EACH_TAP, NoteKind.EX_BREAK_TAP,
        NoteKind.EX_STAR, NoteKind.EX_EACH_STAR, NoteKind.EX_BREAK_STAR,
        NoteKind.EX_DOUBLE_STAR, NoteKind.EX_EACH_DOUBLE_STAR, NoteKind.EX_BREAK_DOUBLE_STAR
    }
    return kind in ex_kinds

def is_star(kind: NoteKind):
    star_kinds = {
        NoteKind.NORM_STAR, NoteKind.EX_STAR,
        NoteKind.EACH_STAR, NoteKind.EX_EACH_STAR,
        NoteKind.BREAK_STAR, NoteKind.EX_BREAK_STAR,
        NoteKind.DOUBLE_STAR, NoteKind.EX_DOUBLE_STAR,
        NoteKind.EACH_DOUBLE_STAR, NoteKind.EX_EACH_DOUBLE_STAR, 
        NoteKind.BREAK_DOUBLE_STAR, NoteKind.EX_BREAK_DOUBLE_STAR,
    }
    return kind in star_kinds

def get_note_angle(speed: float):
    return time() * -pi * speed

def draw_note(
    kind: NoteKind,
    button: Button,
    start_time: float,
    target_time: float,
    note_angle: float,
):
    progress = unlerp(start_time, target_time, time())
    if progress < 0:
        return
    angle = get_button_angle_vertical(button)
    layout = layout_note(progress, button).rotate_centered(angle + note_angle)
    _note_draw(kind, layout, get_z(LAYER_NOTE, target_time))
    if is_ex(kind):
        _ex_draw(kind, layout, get_z(LAYER_EX, target_time))

    line_layout = layout_line(progress).rotate_centered(angle)
    line_alpha = get_line_alpha(progress)
    _line_draw(kind, line_layout, get_z(LAYER_NOTE_LINE, target_time), line_alpha)
        
def _note_draw(kind: NoteKind, layout: Quad, layer: ZIndexes, alpha: float = 1):
    match kind:
        case NoteKind.NORM_TAP | NoteKind.EX_TAP:
            ActiveSkin.normal_note.draw(layout, layer.tuple, alpha)
        case NoteKind.BREAK_TAP | NoteKind.EX_BREAK_TAP:
            ActiveSkin.break_note_dark.draw(layout, layer.tuple, alpha)
            pulse = max(sin(time() * pi * 4), 0)
            layer.z4 = layer.z4 + 1
            ActiveSkin.break_note_light.draw(layout, layer.tuple, pulse * alpha)
        case NoteKind.EACH_TAP | NoteKind.EX_EACH_TAP:
            ActiveSkin.each_note.draw(layout, layer.tuple, alpha)

        case NoteKind.NORM_STAR | NoteKind.EX_STAR:
            ActiveSkin.normal_star.draw(layout, layer.tuple, alpha)
        case NoteKind.BREAK_STAR | NoteKind.EX_BREAK_STAR:
            ActiveSkin.break_star.draw(layout, layer.tuple, alpha)
        case NoteKind.EACH_STAR | NoteKind.EX_EACH_STAR:
            ActiveSkin.each_star.draw(layout, layer.tuple, alpha)

        case NoteKind.DOUBLE_STAR | NoteKind.EX_DOUBLE_STAR:
            ActiveSkin.double_star.draw(layout, layer.tuple, alpha)
        case NoteKind.BREAK_DOUBLE_STAR | NoteKind.EX_BREAK_DOUBLE_STAR:
            ActiveSkin.break_double_star.draw(layout, layer.tuple, alpha)
        case NoteKind.EACH_DOUBLE_STAR | NoteKind.EX_EACH_DOUBLE_STAR:
            ActiveSkin.each_double_star.draw(layout, layer.tuple, alpha)
        
        case _:
            assert_never(kind)
            return

def _line_draw(kind: NoteKind, layout: Quad, layer: ZIndexes, alpha: float = 1):
    match kind:
        case NoteKind.NORM_TAP | NoteKind.EX_TAP:
            ActiveSkin.normal_line.draw(layout, layer.tuple, alpha)
        case NoteKind.NORM_STAR | NoteKind.EX_STAR | NoteKind.DOUBLE_STAR | NoteKind.EX_DOUBLE_STAR:
            ActiveSkin.star_line.draw(layout, layer.tuple, alpha)
        case NoteKind.BREAK_TAP | NoteKind.EX_BREAK_TAP \
            | NoteKind.BREAK_STAR | NoteKind.EX_BREAK_STAR \
            | NoteKind.BREAK_DOUBLE_STAR | NoteKind.EX_BREAK_DOUBLE_STAR:
            ActiveSkin.break_line.draw(layout, layer.tuple, alpha)
        case NoteKind.EACH_TAP | NoteKind.EX_EACH_TAP \
            | NoteKind.EACH_STAR | NoteKind.EX_EACH_STAR \
            | NoteKind.EACH_DOUBLE_STAR | NoteKind.EX_EACH_DOUBLE_STAR:
            ActiveSkin.each_line.draw(layout, layer.tuple, alpha)
        case _:
            assert_never(kind)
            return

def _ex_draw(kind: NoteKind, layout: Quad, layer: ZIndexes, alpha: float = 1):
    match kind:
        case NoteKind.NORM_TAP | NoteKind.EX_TAP:
            ActiveSkin.normal_note_ex_outline.draw(layout, layer.tuple, alpha)
        case NoteKind.BREAK_TAP | NoteKind.EX_BREAK_TAP:
            ActiveSkin.break_note_ex_outline.draw(layout, layer.tuple, alpha)
        case NoteKind.EACH_TAP | NoteKind.EX_EACH_TAP:
            ActiveSkin.each_note_ex_outline.draw(layout, layer.tuple, alpha)

        case NoteKind.NORM_STAR | NoteKind.EX_STAR:
            ActiveSkin.normal_star_ex_outline.draw(layout, layer.tuple, alpha)
        case NoteKind.BREAK_STAR | NoteKind.EX_BREAK_STAR:
            ActiveSkin.break_star_ex_outline.draw(layout, layer.tuple, alpha)
        case NoteKind.EACH_STAR | NoteKind.EX_EACH_STAR:
            ActiveSkin.each_star_ex_outline.draw(layout, layer.tuple, alpha)

        case NoteKind.DOUBLE_STAR | NoteKind.EX_DOUBLE_STAR:
            ActiveSkin.double_star_ex_outline.draw(layout, layer.tuple, alpha)
        case NoteKind.BREAK_DOUBLE_STAR | NoteKind.EX_BREAK_DOUBLE_STAR:
            ActiveSkin.break_double_star_ex_outline.draw(layout, layer.tuple, alpha)
        case NoteKind.EACH_DOUBLE_STAR | NoteKind.EX_EACH_DOUBLE_STAR:
            ActiveSkin.each_double_star_ex_outline.draw(layout, layer.tuple, alpha)

        case _:
            assert_never(kind)
            return

def get_tap_appear_duration(speed: float):
    travel_speed = abs(LevelConfig.noteSpeed * speed)
    travel_time = DISTANCE_TRAVEL / travel_speed
    scale_time = 1 / (NOTE_SCALE_RATE * travel_speed)
    appear_duration = scale_time + travel_time
    return max(appear_duration, 0.15)