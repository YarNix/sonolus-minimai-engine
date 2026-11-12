from typing import cast

from sonolus.script.archetype import PreviewArchetype, StandardImport, entity_data, imported
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names
from minimai.lib.game import Button
from minimai.lib.note import NoteKind
from minimai.preview.layout import report_end_time


class PreviewBaseNote(PreviewArchetype):
    button: Button = imported(default=1)
    firework: bool = imported(default=False)
    beat: StandardImport.BEAT

    kind: NoteKind = entity_data()
    target_time: float = entity_data()

    def preprocess(self):
        self.kind = cast(NoteKind, self.key)
        self.target_time = beat_to_time(self.beat)
        report_end_time(self.target_time)


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
