from enum import IntEnum, auto
from typing import assert_never

from sonolus.script.interval import unlerp
from sonolus.script.quad import Quad
from sonolus.script.runtime import time

from minimai.lib.game import Button
from minimai.lib.layer import (
    LAYER_OFFSET_BODY,
    LAYER_OFFSET_EX,
    LAYER_OFFSET_HEAD,
    LAYER_OFFSET_POINT,
    LAYER_OFFSET_TAIL,
    LAYER_NOTE,
    LAYER_NOTE_LINE,
    ZIndexes,
    get_z,
)
from minimai.lib.layout import HoldLayout, get_button_angle_vertical, get_line_alpha, layout_hold, layout_line
from minimai.lib.skin import ActiveSkin, BodySpriteSet, BreakBodySpriteSet, ActiveBodySpriteSet


class HoldKind(IntEnum):
    NORM_HOLD = auto()
    EX_HOLD = auto()

    EACH_HOLD = auto()
    EX_EACH_HOLD = auto()

    BREAK_HOLD = auto()
    EX_BREAK_HOLD = auto()

class HoldState(IntEnum):
    DEFAULT = 0 # In the approach state neither held or released
    PRESSED = auto()
    RELEASED = auto()
    RELEASED_GRACE = auto()


def is_ex_hold(kind: HoldKind) -> bool:
    return kind in {HoldKind.EX_HOLD, HoldKind.EX_EACH_HOLD, HoldKind.EX_BREAK_HOLD}


def is_break_hold(kind: HoldKind) -> bool:
    return kind in {HoldKind.BREAK_HOLD, HoldKind.EX_BREAK_HOLD}


def draw_hold(
    kind: HoldKind,
    button: Button,
    start_time: float,
    target_time: float,
    end_time: float,
    state: HoldState,
):
    progress = unlerp(start_time, target_time, time())
    if progress < 0:
        return
    tail_progress = unlerp(start_time, target_time, time() - (end_time - target_time))
    layout = layout_hold(progress, tail_progress, button)

    if layout.tail_visible:
        _end_point_draw(kind, layout.end_point, get_z(LAYER_NOTE, target_time, LAYER_OFFSET_POINT))
    _body_draw(kind, state, layout, target_time)
    if is_ex_hold(kind):
        _ex_draw(kind, layout, target_time)

    line_progress = min(progress, 1)
    line_layout = layout_line(line_progress).rotate_centered(get_button_angle_vertical(button))
    _line_draw(kind, line_layout, get_z(LAYER_NOTE_LINE, target_time), get_line_alpha(line_progress))


def _draw_body_set(sprites: BodySpriteSet, layout: HoldLayout, target_time: float, z_offset: int = 0):
    sprites.body.draw(layout.body, get_z(LAYER_NOTE, target_time, LAYER_OFFSET_BODY, z_offset).tuple)
    sprites.tail.draw(layout.tail, get_z(LAYER_NOTE, target_time, LAYER_OFFSET_TAIL, z_offset).tuple)
    sprites.head.draw(layout.head, get_z(LAYER_NOTE, target_time, LAYER_OFFSET_HEAD, z_offset).tuple)


def _draw_break_body_set(sprites: BreakBodySpriteSet, layout: HoldLayout, target_time: float):
    sprites.body.draw(layout.body, get_z(LAYER_NOTE, target_time, LAYER_OFFSET_BODY).tuple)
    sprites.tail.draw(layout.tail, get_z(LAYER_NOTE, target_time, LAYER_OFFSET_TAIL).tuple)
    sprites.head.draw(layout.head, get_z(LAYER_NOTE, target_time, LAYER_OFFSET_HEAD).tuple)


def _draw_active_body_set(sprites: ActiveBodySpriteSet, layout: HoldLayout, target_time: float):
    sprites.body.draw(layout.body, get_z(LAYER_NOTE, target_time, LAYER_OFFSET_BODY).tuple)
    sprites.tail.draw(layout.tail, get_z(LAYER_NOTE, target_time, LAYER_OFFSET_TAIL).tuple)
    sprites.head.draw(layout.head, get_z(LAYER_NOTE, target_time, LAYER_OFFSET_HEAD).tuple)


def _body_draw(kind: HoldKind, state: HoldState, layout: HoldLayout, target_time: float):
    if state == HoldState.RELEASED or state == HoldState.RELEASED_GRACE:
        _draw_body_set(ActiveSkin.hold_note_off, layout, target_time)
        return
    is_on = state == HoldState.PRESSED
    match kind:
        case HoldKind.NORM_HOLD | HoldKind.EX_HOLD:
            if is_on:
                _draw_active_body_set(ActiveSkin.hold_note_on, layout, target_time)
            else:
                _draw_body_set(ActiveSkin.hold_note, layout, target_time)
        case HoldKind.EACH_HOLD | HoldKind.EX_EACH_HOLD:
            if is_on:
                _draw_active_body_set(ActiveSkin.each_hold_note_on, layout, target_time)
            else:
                _draw_body_set(ActiveSkin.each_hold_note, layout, target_time)
        case HoldKind.BREAK_HOLD | HoldKind.EX_BREAK_HOLD:
            if is_on:
                _draw_active_body_set(ActiveSkin.break_hold_note_on, layout, target_time)
            else:
                _draw_break_body_set(ActiveSkin.break_hold_note, layout, target_time)
        case _:
            assert_never(kind)


def _ex_draw(kind: HoldKind, layout: HoldLayout, target_time: float):
    match kind:
        case HoldKind.NORM_HOLD | HoldKind.EX_HOLD:
            _draw_body_set(ActiveSkin.hold_note_ex_outline, layout, target_time, LAYER_OFFSET_EX)
        case HoldKind.EACH_HOLD | HoldKind.EX_EACH_HOLD:
            _draw_body_set(ActiveSkin.each_hold_note_ex_outline, layout, target_time, LAYER_OFFSET_EX)
        case HoldKind.BREAK_HOLD | HoldKind.EX_BREAK_HOLD:
            _draw_body_set(ActiveSkin.break_hold_note_ex_outline, layout, target_time, LAYER_OFFSET_EX)
        case _:
            assert_never(kind)


def _end_point_draw(kind: HoldKind, layout: Quad, layer: ZIndexes):
    match kind:
        case HoldKind.NORM_HOLD | HoldKind.EX_HOLD:
            ActiveSkin.hold_note_end_point.draw(layout, layer.tuple)
        case HoldKind.EACH_HOLD | HoldKind.EX_EACH_HOLD:
            ActiveSkin.each_hold_note_end_point.draw(layout, layer.tuple)
        case HoldKind.BREAK_HOLD | HoldKind.EX_BREAK_HOLD:
            ActiveSkin.break_hold_note_end_point.draw(layout, layer.tuple)
        case _:
            assert_never(kind)


def _line_draw(kind: HoldKind, layout: Quad, layer: ZIndexes, alpha: float):
    match kind:
        case HoldKind.NORM_HOLD | HoldKind.EX_HOLD:
            ActiveSkin.normal_line.draw(layout, layer.tuple, alpha)
        case HoldKind.EACH_HOLD | HoldKind.EX_EACH_HOLD:
            ActiveSkin.each_line.draw(layout, layer.tuple, alpha)
        case HoldKind.BREAK_HOLD | HoldKind.EX_BREAK_HOLD:
            ActiveSkin.break_line.draw(layout, layer.tuple, alpha)
        case _:
            assert_never(kind)
