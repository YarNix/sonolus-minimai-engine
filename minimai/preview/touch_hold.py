from typing import cast

from sonolus.script.archetype import PreviewArchetype, StandardImport, entity_data, imported
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names
from minimai.lib.game import Sensor
from minimai.lib.touch_hold import TouchHoldKind
from minimai.preview.layout import report_end_time


class PreviewBaseTouchHold(PreviewArchetype):
    sensor: Sensor = imported()
    firework: bool = imported(default=False)
    beat: StandardImport.BEAT
    hold_duration: float = imported(name="holdDuration", default=0)

    kind: TouchHoldKind = entity_data()
    target_time: float = entity_data()
    end_time: float = entity_data()

    def preprocess(self):
        self.kind = cast(TouchHoldKind, self.key)
        self.target_time = beat_to_time(self.beat)
        self.end_time = beat_to_time(self.beat + max(self.hold_duration, 0))
        report_end_time(self.end_time)


PreviewNormalTouchHoldNote = PreviewBaseTouchHold.derive(
    archetype_names.NORMAL_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.NORM_TOUCH_HOLD
)
PreviewExTouchHoldNote = PreviewBaseTouchHold.derive(
    archetype_names.EX_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.EX_TOUCH_HOLD
)
PreviewEachTouchHoldNote = PreviewBaseTouchHold.derive(
    archetype_names.EACH_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.EACH_TOUCH_HOLD
)
PreviewExEachTouchHoldNote = PreviewBaseTouchHold.derive(
    archetype_names.EX_EACH_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.EX_EACH_TOUCH_HOLD
)
PreviewBreakTouchHoldNote = PreviewBaseTouchHold.derive(
    archetype_names.BREAK_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.BREAK_TOUCH_HOLD
)
PreviewExBreakTouchHoldNote = PreviewBaseTouchHold.derive(
    archetype_names.EX_BREAK_TOUCH_HOLD_NOTE, is_scored=True, key=TouchHoldKind.EX_BREAK_TOUCH_HOLD
)

PREVIEW_TOUCH_HOLD_ARCHETYPES = (
    PreviewNormalTouchHoldNote,
    PreviewExTouchHoldNote,
    PreviewEachTouchHoldNote,
    PreviewExEachTouchHoldNote,
    PreviewBreakTouchHoldNote,
    PreviewExBreakTouchHoldNote,
)
