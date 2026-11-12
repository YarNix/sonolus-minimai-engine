from typing import assert_never, cast

from sonolus.script.archetype import entity_data, imported
from sonolus.script.quad import Rect
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names
from minimai.lib.game import apply_button_mirror_option
from minimai.lib.hold import HoldKind, is_ex_hold
from minimai.lib.skin import BaseSkin
from minimai.preview.base import PreviewButtonBase
from minimai.preview.layout import (
    get_button_lane,
    layout_hold_body,
    layout_hold_end_point,
    layout_hold_head_cap,
    layout_hold_tail_cap,
    report_end_time,
    report_judgment_beat,
    time_to_col,
)
from minimai.preview.note import Z_EX_OUTLINE, Z_HOLD, Z_HOLD_END_POINT, draw_firework


class PreviewBaseHold(PreviewButtonBase):
    hold_duration: float = imported(name="holdDuration", default=0)

    kind: HoldKind = entity_data()
    end_time: float = entity_data()

    def preprocess(self):
        self.kind = cast(HoldKind, self.key)
        self.button = apply_button_mirror_option(self.button)
        self.target_time = beat_to_time(self.beat)
        end_beat = self.beat + max(self.hold_duration, 0)
        self.end_time = beat_to_time(end_beat)
        report_end_time(self.end_time)
        report_judgment_beat(end_beat)

    def render(self):
        """An upright hexagon reaching half a note past the head and end times (the v and ^ caps at
        its ends), with an end point mark at each of the two times (one for a zero-length hold)."""
        lane = get_button_lane(self.button)
        if self.firework:
            draw_firework(lane, self.end_time)
        ex = is_ex_hold(self.kind)
        for col in range(time_to_col(self.target_time), time_to_col(self.end_time) + 1):
            body = layout_hold_body(lane, self.target_time, self.end_time, col)
            draw_hold_part(self.kind, HoldPart.BODY, body, self.target_time, False)
            if ex:
                draw_hold_part(self.kind, HoldPart.BODY, body, self.target_time, True)
        tail = layout_hold_tail_cap(lane, self.target_time)
        head = layout_hold_head_cap(lane, self.end_time)
        draw_hold_part(self.kind, HoldPart.TAIL, tail, self.target_time, False)
        draw_hold_part(self.kind, HoldPart.HEAD, head, self.target_time, False)
        if ex:
            draw_hold_part(self.kind, HoldPart.TAIL, tail, self.target_time, True)
            draw_hold_part(self.kind, HoldPart.HEAD, head, self.target_time, True)
        draw_hold_end_point(self.kind, layout_hold_end_point(lane, self.target_time), self.target_time)
        if self.end_time > self.target_time:
            draw_hold_end_point(self.kind, layout_hold_end_point(lane, self.end_time), self.target_time)


class HoldPart:
    HEAD = 0
    BODY = 1
    TAIL = 2


def draw_hold_part(kind: HoldKind, part: int, layout: Rect, time: float, ex_outline: bool):
    """Breaks use their light sprites (no pulse in a still picture)."""
    z = (Z_HOLD, time)
    if ex_outline:
        z = (Z_EX_OUTLINE, time)
    match kind:
        case HoldKind.NORM_HOLD | HoldKind.EX_HOLD:
            if ex_outline:
                draw_by_part(part, layout, z, BaseSkin.hold_note_head_ex_outline, BaseSkin.hold_note_body_ex_outline, BaseSkin.hold_note_tail_ex_outline)
            else:
                draw_by_part(part, layout, z, BaseSkin.hold_note_head, BaseSkin.hold_note_body, BaseSkin.hold_note_tail)
        case HoldKind.EACH_HOLD | HoldKind.EX_EACH_HOLD:
            if ex_outline:
                draw_by_part(part, layout, z, BaseSkin.each_hold_note_head_ex_outline, BaseSkin.each_hold_note_body_ex_outline, BaseSkin.each_hold_note_tail_ex_outline)
            else:
                draw_by_part(part, layout, z, BaseSkin.each_hold_note_head, BaseSkin.each_hold_note_body, BaseSkin.each_hold_note_tail)
        case HoldKind.BREAK_HOLD | HoldKind.EX_BREAK_HOLD:
            if ex_outline:
                draw_by_part(part, layout, z, BaseSkin.break_hold_note_head_ex_outline, BaseSkin.break_hold_note_body_ex_outline, BaseSkin.break_hold_note_tail_ex_outline)
            else:
                draw_by_part(part, layout, z, BaseSkin.break_hold_note_head_light, BaseSkin.break_hold_note_body_light, BaseSkin.break_hold_note_tail_light)
        case _:
            assert_never(kind)


def draw_hold_end_point(kind: HoldKind, layout: Rect, time: float):
    z = (Z_HOLD_END_POINT, time)
    match kind:
        case HoldKind.NORM_HOLD | HoldKind.EX_HOLD:
            BaseSkin.hold_note_end_point.draw(layout, z=z)
        case HoldKind.EACH_HOLD | HoldKind.EX_EACH_HOLD:
            BaseSkin.each_hold_note_end_point.draw(layout, z=z)
        case HoldKind.BREAK_HOLD | HoldKind.EX_BREAK_HOLD:
            BaseSkin.break_hold_note_end_point.draw(layout, z=z)
        case _:
            assert_never(kind)


def draw_by_part(part: int, layout: Rect, z: tuple, head, body, tail):
    if part == HoldPart.HEAD:
        head.draw(layout, z=z)
    elif part == HoldPart.BODY:
        body.draw(layout, z=z)
    else:
        tail.draw(layout, z=z)


PreviewNormalHoldNote = PreviewBaseHold.derive(archetype_names.NORMAL_HOLD_NOTE, is_scored=True, key=HoldKind.NORM_HOLD)
PreviewExHoldNote = PreviewBaseHold.derive(archetype_names.EX_HOLD_NOTE, is_scored=True, key=HoldKind.EX_HOLD)
PreviewEachHoldNote = PreviewBaseHold.derive(archetype_names.EACH_HOLD_NOTE, is_scored=True, key=HoldKind.EACH_HOLD)
PreviewExEachHoldNote = PreviewBaseHold.derive(archetype_names.EX_EACH_HOLD_NOTE, is_scored=True, key=HoldKind.EX_EACH_HOLD)
PreviewBreakHoldNote = PreviewBaseHold.derive(archetype_names.BREAK_HOLD_NOTE, is_scored=True, key=HoldKind.BREAK_HOLD)
PreviewExBreakHoldNote = PreviewBaseHold.derive(archetype_names.EX_BREAK_HOLD_NOTE, is_scored=True, key=HoldKind.EX_BREAK_HOLD)

PREVIEW_HOLD_ARCHETYPES = (
    PreviewNormalHoldNote,
    PreviewExHoldNote,
    PreviewEachHoldNote,
    PreviewExEachHoldNote,
    PreviewBreakHoldNote,
    PreviewExBreakHoldNote,
)
