from typing import cast

from sonolus.script.archetype import PreviewArchetype, StandardImport, entity_data, imported
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names
from minimai.lib.game import Button
from minimai.lib.hold import HoldKind
from minimai.preview.layout import report_end_time


class PreviewBaseHold(PreviewArchetype):
    button: Button = imported(default=1)
    firework: bool = imported(default=False)
    beat: StandardImport.BEAT
    hold_duration: float = imported(name="holdDuration", default=0)

    kind: HoldKind = entity_data()
    target_time: float = entity_data()
    end_time: float = entity_data()

    def preprocess(self):
        self.kind = cast(HoldKind, self.key)
        self.target_time = beat_to_time(self.beat)
        self.end_time = beat_to_time(self.beat + max(self.hold_duration, 0))
        report_end_time(self.end_time)


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
