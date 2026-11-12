from typing import assert_never, cast

from sonolus.script.archetype import PreviewArchetype, StandardImport, entity_data, imported
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names
from minimai.lib.game import Sensor, apply_sensor_mirror_option
from minimai.lib.skin import BaseSkin
from minimai.lib.touch_hold import TouchHoldKind
from minimai.preview.layout import (
    TOUCH_HOLD_BAR_PARTS,
    TOUCH_HOLD_FAN_OFFSET,
    get_sensor_lane,
    get_touch_hold_fan_angle,
    layout_touch_fan,
    layout_touch_hold_bar,
    layout_touch_point,
    report_end_time,
    report_judgment_beat,
    time_to_col,
)
from minimai.preview.note import Z_HOLD, Z_NOTE, draw_firework


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
        self.sensor = apply_sensor_mirror_option(self.sensor)
        self.target_time = beat_to_time(self.beat)
        end_beat = self.beat + max(self.hold_duration, 0)
        self.end_time = beat_to_time(end_beat)
        report_end_time(self.end_time)
        report_judgment_beat(end_beat)

    def render(self):
        """Closed at its head time, with a bar up to its end time in 4 equal parts coloured like its
        fans (in the order the border fills). The left sides' cross-sections (bars 3 and 4) run the
        other way across the border, so they're flipped to line up with the right sides'."""
        lane = get_sensor_lane(self.sensor)
        if self.firework:
            draw_firework(lane, self.end_time)
        part_duration = (self.end_time - self.target_time) / TOUCH_HOLD_BAR_PARTS
        for part in range(TOUCH_HOLD_BAR_PARTS):
            start = self.target_time + part * part_duration
            end = start + part_duration
            for col in range(time_to_col(start), time_to_col(end) + 1):
                BaseSkin.touch_hold_border_on_bars[part].draw(
                    layout_touch_hold_bar(lane, start, end, col, part >= 2), z=(Z_HOLD, self.target_time)
                )
        for i in range(4):
            BaseSkin.normal_touch_hold_fan[i].draw(
                layout_touch_fan(lane, self.target_time, get_touch_hold_fan_angle(i), TOUCH_HOLD_FAN_OFFSET),
                z=(Z_NOTE, self.target_time, 3 - i),
            )
        draw_touch_hold_point(self.kind, lane, self.target_time)


def draw_touch_hold_point(kind: TouchHoldKind, lane: float, time: float):
    layout = layout_touch_point(lane, time)
    z = (Z_NOTE, time, 4)
    match kind:
        case TouchHoldKind.NORM_TOUCH_HOLD | TouchHoldKind.EX_TOUCH_HOLD:
            BaseSkin.normal_touch_point.draw(layout, z=z)
        case TouchHoldKind.EACH_TOUCH_HOLD | TouchHoldKind.EX_EACH_TOUCH_HOLD:
            BaseSkin.each_touch_point.draw(layout, z=z)
        case TouchHoldKind.BREAK_TOUCH_HOLD | TouchHoldKind.EX_BREAK_TOUCH_HOLD:
            BaseSkin.break_touch_point.draw(layout, z=z)
        case _:
            assert_never(kind)


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
