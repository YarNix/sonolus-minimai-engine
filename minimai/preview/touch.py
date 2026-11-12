from typing import assert_never, cast

from sonolus.script.archetype import PreviewArchetype, StandardImport, entity_data, imported
from sonolus.script.quad import QuadLike
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names
from minimai.lib.game import Sensor, apply_sensor_mirror_option
from minimai.lib.skin import BaseSkin
from minimai.lib.touch import TouchKind
from minimai.preview.layout import (
    TOUCH_FAN_OFFSET,
    get_sensor_lane,
    get_touch_fan_angle,
    layout_touch_fan,
    layout_touch_point,
    report_end_time,
    report_judgment_beat,
)
from minimai.preview.note import Z_NOTE, draw_firework


class PreviewBaseTouch(PreviewArchetype):
    sensor: Sensor = imported()
    firework: bool = imported(default=False)
    beat: StandardImport.BEAT

    kind: TouchKind = entity_data()
    target_time: float = entity_data()

    def preprocess(self):
        self.kind = cast(TouchKind, self.key)
        self.sensor = apply_sensor_mirror_option(self.sensor)
        self.target_time = beat_to_time(self.beat)
        report_end_time(self.target_time)
        report_judgment_beat(self.beat)

    def render(self):
        """Closed, as at its hit time: the point with the four fans around it."""
        lane = get_sensor_lane(self.sensor)
        if self.firework:
            draw_firework(lane, self.target_time)
        for i in range(4):
            draw_touch_part(
                self.kind,
                False,
                layout_touch_fan(lane, self.target_time, get_touch_fan_angle(i), TOUCH_FAN_OFFSET),
                self.target_time,
                i,
            )
        draw_touch_part(self.kind, True, layout_touch_point(lane, self.target_time), self.target_time, 4)


def draw_touch_part(kind: TouchKind, is_point: bool, layout: QuadLike, time: float, order: int):
    z = (Z_NOTE, time, order)
    match kind:
        case TouchKind.NORM_TOUCH | TouchKind.EX_TOUCH:
            if is_point:
                BaseSkin.normal_touch_point.draw(layout, z=z)
            else:
                BaseSkin.normal_touch_fan.draw(layout, z=z)
        case TouchKind.EACH_TOUCH | TouchKind.EX_EACH_TOUCH:
            if is_point:
                BaseSkin.each_touch_point.draw(layout, z=z)
            else:
                BaseSkin.each_touch_fan.draw(layout, z=z)
        case TouchKind.BREAK_TOUCH | TouchKind.EX_BREAK_TOUCH:
            if is_point:
                BaseSkin.break_touch_point.draw(layout, z=z)
            else:
                BaseSkin.break_touch_fan.draw(layout, z=z)
        case _:
            assert_never(kind)


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
