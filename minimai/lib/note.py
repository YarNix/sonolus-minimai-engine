from collections.abc import Iterable
from enum import IntEnum, auto
from math import pi
from typing import assert_never

from sonolus.script.quad import Quad
from sonolus.script.interval import unlerp
from sonolus.script.runtime import time
from sonolus.script.debug import assert_true

from minimai.lib.game import Button
from minimai.lib.skin import ActiveSkin
from minimai.lib.layout import Layout, get_line_alpha, layout_note, layout_line, get_button_angle_vertical, NOTE_SCALE_RATE, NOTE_SPAWN_DISTANCE
from minimai.lib.layer import ZIndexes, get_z, LAYER_NOTE, LAYER_NOTE_LINE, LAYER_OFFSET_EX
from minimai.lib.scoring import MAX_BREAK_WEIGHT, WeightedArchetype, init_life_loss


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

def is_ex(kind: NoteKind):
    ex_kinds = {
        NoteKind.EX_TAP, NoteKind.EX_EACH_TAP, NoteKind.EX_BREAK_TAP,
        NoteKind.EX_STAR, NoteKind.EX_EACH_STAR, NoteKind.EX_BREAK_STAR,
        NoteKind.EX_DOUBLE_STAR, NoteKind.EX_EACH_DOUBLE_STAR, NoteKind.EX_BREAK_DOUBLE_STAR
    }
    return kind in ex_kinds

def is_break(kind: NoteKind):
    break_kinds = {
        NoteKind.BREAK_TAP, NoteKind.EX_BREAK_TAP,
        NoteKind.BREAK_STAR, NoteKind.EX_BREAK_STAR,
        NoteKind.BREAK_DOUBLE_STAR, NoteKind.EX_BREAK_DOUBLE_STAR,
    }
    return kind in break_kinds

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

# Fake-rotate star (simai ``$$``): -440 deg/s, in half-turns per second.
FAKE_ROTATION_SPEED = 440 / 180


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
        # The EX outline goes over the note (z4 1; a break light layer is at 0.5).
        _ex_draw(kind, layout, get_z(LAYER_NOTE, target_time, etc=LAYER_OFFSET_EX))

    line_layout = layout_line(progress).rotate_centered(angle)
    line_alpha = get_line_alpha(progress)
    _line_draw(kind, line_layout, get_z(LAYER_NOTE_LINE, target_time), line_alpha)
        
def _note_draw(kind: NoteKind, layout: Quad, layer: ZIndexes, alpha: float = 1):
    match kind:
        case NoteKind.NORM_TAP | NoteKind.EX_TAP:
            ActiveSkin.normal_note.draw(layout, layer.tuple, alpha)
        case NoteKind.BREAK_TAP | NoteKind.EX_BREAK_TAP:
            ActiveSkin.break_note.draw(layout, layer.tuple, alpha)
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
    assert_true(speed != 0, "Speed 0 is not supported!")
    travel_speed = max(abs(Layout.note_speed * speed), 0.01)
    travel_time = (1 - NOTE_SPAWN_DISTANCE) / travel_speed
    scale_time = 1 / (NOTE_SCALE_RATE * travel_speed)
    appear_duration = scale_time + travel_time
    return max(appear_duration, 0.15)


def init_note_score(archetypes: Iterable[type[WeightedArchetype]]):
    for archetype in archetypes:
        if not archetype.is_scored:
            continue
        weight = MAX_BREAK_WEIGHT if is_break(archetype.key) else archetype.score_weight()
        archetype.archetype_score_multiplier = weight


def init_note_life(archetypes: Iterable[type[WeightedArchetype]]):
    for archetype in archetypes:
        if not archetype.is_scored:
            continue
        weight = MAX_BREAK_WEIGHT if is_break(archetype.key) else archetype.score_weight()
        init_life_loss(archetype, weight)
