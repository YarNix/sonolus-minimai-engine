from typing import cast

from sonolus.script.archetype import PreviewArchetype, StandardImport, entity_data, imported
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names
from minimai.lib.game import Sensor
from minimai.lib.touch import TouchKind
from minimai.preview.layout import report_end_time


class PreviewBaseTouch(PreviewArchetype):
    sensor: Sensor = imported()
    firework: bool = imported(default=False)
    beat: StandardImport.BEAT

    kind: TouchKind = entity_data()
    target_time: float = entity_data()

    def preprocess(self):
        self.kind = cast(TouchKind, self.key)
        self.target_time = beat_to_time(self.beat)
        report_end_time(self.target_time)


PreviewNormalTouchNote = PreviewBaseTouch.derive(archetype_names.NORMAL_TOUCH_NOTE, is_scored=True, key=TouchKind.NORM_TOUCH)
PreviewExTouchNote = PreviewBaseTouch.derive(archetype_names.EX_TOUCH_NOTE, is_scored=True, key=TouchKind.EX_TOUCH)
PreviewBreakTouchNote = PreviewBaseTouch.derive(archetype_names.BREAK_TOUCH_NOTE, is_scored=True, key=TouchKind.BREAK_TOUCH)
PreviewExBreakTouchNote = PreviewBaseTouch.derive(archetype_names.EX_BREAK_TOUCH_NOTE, is_scored=True, key=TouchKind.EX_BREAK_TOUCH)
PreviewEachTouchNote = PreviewBaseTouch.derive(archetype_names.EACH_TOUCH_NOTE, is_scored=True, key=TouchKind.EACH_TOUCH)
PreviewExEachTouchNote = PreviewBaseTouch.derive(archetype_names.EX_EACH_TOUCH_NOTE, is_scored=True, key=TouchKind.EX_EACH_TOUCH)

PREVIEW_TOUCH_ARCHETYPES = (
    PreviewNormalTouchNote,
    PreviewExTouchNote,
    PreviewBreakTouchNote,
    PreviewExBreakTouchNote,
    PreviewEachTouchNote,
    PreviewExEachTouchNote,
)
