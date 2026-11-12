from typing import assert_never, cast

from sonolus.script.archetype import entity_data
from sonolus.script.quad import Rect
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names
from minimai.lib.game import apply_button_mirror_option
from minimai.lib.note import NoteKind, is_ex
from minimai.lib.skin import BaseSkin
from minimai.preview.layer import LAYER_EX_OUTLINE, LAYER_FIREWORK, LAYER_NOTE, get_z
from minimai.preview.base import PreviewButtonBase
from minimai.preview.layout import (
    get_button_lane,
    layout_firework,
    layout_note,
    report_end_time,
    report_judgment_beat,
)



class PreviewBaseNote(PreviewButtonBase):
    kind: NoteKind = entity_data()

    def preprocess(self):
        self.kind = cast(NoteKind, self.key)
        self.button = apply_button_mirror_option(self.button)
        self.target_time = beat_to_time(self.beat)
        report_end_time(self.target_time)
        report_judgment_beat(self.beat)

    def render(self):
        lane = get_button_lane(self.button)
        if self.firework:
            draw_firework(lane, self.target_time)
        layout = layout_note(lane, self.target_time)
        draw_note_sprite(self.kind, layout, get_z(LAYER_NOTE, lane, self.target_time))
        if is_ex(self.kind):
            draw_note_ex_outline(self.kind, layout, get_z(LAYER_EX_OUTLINE, lane, self.target_time))


def draw_firework(lane: float, time: float):
    """The halo behind a note that sets off a firework."""
    BaseSkin.preview_firework.draw(layout_firework(lane, time), z=get_z(LAYER_FIREWORK, lane, time))


def draw_note_sprite(kind: NoteKind, layout: Rect, z: tuple):
    match kind:
        case NoteKind.NORM_TAP | NoteKind.EX_TAP:
            BaseSkin.normal_note.draw(layout, z=z)
        case NoteKind.BREAK_TAP | NoteKind.EX_BREAK_TAP:
            BaseSkin.break_note.draw(layout, z=z)
        case NoteKind.EACH_TAP | NoteKind.EX_EACH_TAP:
            BaseSkin.each_note.draw(layout, z=z)
        case NoteKind.NORM_STAR | NoteKind.EX_STAR:
            BaseSkin.normal_star.draw(layout, z=z)
        case NoteKind.BREAK_STAR | NoteKind.EX_BREAK_STAR:
            BaseSkin.break_star.draw(layout, z=z)
        case NoteKind.EACH_STAR | NoteKind.EX_EACH_STAR:
            BaseSkin.each_star.draw(layout, z=z)
        case NoteKind.DOUBLE_STAR | NoteKind.EX_DOUBLE_STAR:
            BaseSkin.double_star.draw(layout, z=z)
        case NoteKind.BREAK_DOUBLE_STAR | NoteKind.EX_BREAK_DOUBLE_STAR:
            BaseSkin.break_double_star.draw(layout, z=z)
        case NoteKind.EACH_DOUBLE_STAR | NoteKind.EX_EACH_DOUBLE_STAR:
            BaseSkin.each_double_star.draw(layout, z=z)
        case _:
            assert_never(kind)


def draw_note_ex_outline(kind: NoteKind, layout: Rect, z: tuple):
    match kind:
        case NoteKind.NORM_TAP | NoteKind.EX_TAP:
            BaseSkin.normal_note_ex_outline.draw(layout, z=z)
        case NoteKind.BREAK_TAP | NoteKind.EX_BREAK_TAP:
            BaseSkin.break_note_ex_outline.draw(layout, z=z)
        case NoteKind.EACH_TAP | NoteKind.EX_EACH_TAP:
            BaseSkin.each_note_ex_outline.draw(layout, z=z)
        case NoteKind.NORM_STAR | NoteKind.EX_STAR:
            BaseSkin.normal_star_ex_outline.draw(layout, z=z)
        case NoteKind.BREAK_STAR | NoteKind.EX_BREAK_STAR:
            BaseSkin.break_star_ex_outline.draw(layout, z=z)
        case NoteKind.EACH_STAR | NoteKind.EX_EACH_STAR:
            BaseSkin.each_star_ex_outline.draw(layout, z=z)
        case NoteKind.DOUBLE_STAR | NoteKind.EX_DOUBLE_STAR:
            BaseSkin.double_star_ex_outline.draw(layout, z=z)
        case NoteKind.BREAK_DOUBLE_STAR | NoteKind.EX_BREAK_DOUBLE_STAR:
            BaseSkin.break_double_star_ex_outline.draw(layout, z=z)
        case NoteKind.EACH_DOUBLE_STAR | NoteKind.EX_EACH_DOUBLE_STAR:
            BaseSkin.each_double_star_ex_outline.draw(layout, z=z)
        case _:
            assert_never(kind)


PreviewNormalTapNote = PreviewBaseNote.derive(archetype_names.NORMAL_TAP_NOTE, is_scored=True, key=NoteKind.NORM_TAP)
PreviewExTapNote = PreviewBaseNote.derive(archetype_names.EX_TAP_NOTE, is_scored=True, key=NoteKind.EX_TAP)
PreviewEachTapNote = PreviewBaseNote.derive(archetype_names.EACH_TAP_NOTE, is_scored=True, key=NoteKind.EACH_TAP)
PreviewExEachTapNote = PreviewBaseNote.derive(archetype_names.EX_EACH_TAP_NOTE, is_scored=True, key=NoteKind.EX_EACH_TAP)
PreviewBreakTapNote = PreviewBaseNote.derive(archetype_names.BREAK_TAP_NOTE, is_scored=True, key=NoteKind.BREAK_TAP)
PreviewExBreakTapNote = PreviewBaseNote.derive(archetype_names.EX_BREAK_TAP_NOTE, is_scored=True, key=NoteKind.EX_BREAK_TAP)

PreviewNormalStarNote = PreviewBaseNote.derive(archetype_names.NORMAL_STAR_NOTE, is_scored=True, key=NoteKind.NORM_STAR)
PreviewExStarNote = PreviewBaseNote.derive(archetype_names.EX_STAR_NOTE, is_scored=True, key=NoteKind.EX_STAR)
PreviewEachStarNote = PreviewBaseNote.derive(archetype_names.EACH_STAR_NOTE, is_scored=True, key=NoteKind.EACH_STAR)
PreviewExEachStarNote = PreviewBaseNote.derive(archetype_names.EX_EACH_STAR_NOTE, is_scored=True, key=NoteKind.EX_EACH_STAR)
PreviewBreakStarNote = PreviewBaseNote.derive(archetype_names.BREAK_STAR_NOTE, is_scored=True, key=NoteKind.BREAK_STAR)
PreviewExBreakStarNote = PreviewBaseNote.derive(archetype_names.EX_BREAK_STAR_NOTE, is_scored=True, key=NoteKind.EX_BREAK_STAR)

PreviewDoubleStarNote = PreviewBaseNote.derive(archetype_names.DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.DOUBLE_STAR)
PreviewExDoubleStarNote = PreviewBaseNote.derive(archetype_names.EX_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.EX_DOUBLE_STAR)
PreviewEachDoubleStarNote = PreviewBaseNote.derive(archetype_names.EACH_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.EACH_DOUBLE_STAR)
PreviewExEachDoubleStarNote = PreviewBaseNote.derive(archetype_names.EX_EACH_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.EX_EACH_DOUBLE_STAR)
PreviewBreakDoubleStarNote = PreviewBaseNote.derive(archetype_names.BREAK_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.BREAK_DOUBLE_STAR)
PreviewExBreakDoubleStarNote = PreviewBaseNote.derive(archetype_names.EX_BREAK_DOUBLE_STAR_NOTE, is_scored=True, key=NoteKind.EX_BREAK_DOUBLE_STAR)

PREVIEW_NOTE_ARCHETYPES = (
    PreviewNormalTapNote,
    PreviewExTapNote,
    PreviewEachTapNote,
    PreviewExEachTapNote,
    PreviewBreakTapNote,
    PreviewExBreakTapNote,
    PreviewNormalStarNote,
    PreviewExStarNote,
    PreviewEachStarNote,
    PreviewExEachStarNote,
    PreviewBreakStarNote,
    PreviewExBreakStarNote,
    PreviewDoubleStarNote,
    PreviewExDoubleStarNote,
    PreviewEachDoubleStarNote,
    PreviewExEachDoubleStarNote,
    PreviewBreakDoubleStarNote,
    PreviewExBreakDoubleStarNote,
)
