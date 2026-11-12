from __future__ import annotations

from sonolus.script.archetype import EntityRef, PreviewArchetype, imported

from minimai.lib import archetype_names
from minimai.lib.skin import BaseSkin
from minimai.preview.layer import get_each_line_z
from minimai.preview.base import PreviewButtonBase
from minimai.preview.layout import LANE_MAX, LANE_MIN, get_button_lane, layout_each_line


class PreviewEachLine(PreviewArchetype):
    name = archetype_names.EACH_LINE

    left_ref: EntityRef[PreviewButtonBase] = imported(name="left")
    right_ref: EntityRef[PreviewButtonBase] = imported(name="right")

    def render(self):
        """A flat line at the notes' time between their lanes, wrapping round the column's edges
        (as the ring does between 4 and 5) when that way is shorter. Opposite buttons are as far
        apart either way, so they get both lines."""
        left = self.left_ref.get()
        right = self.right_ref.get()
        steps = (right.button - left.button + 8) % 8
        if steps == 0:
            return
        a = get_button_lane(left.button)
        b = get_button_lane(right.button)
        low = min(a, b)
        high = max(a, b)
        direct = high - low
        wrapped = (low - LANE_MIN) + (LANE_MAX - high)
        time = left.target_time
        if steps == 4 or direct <= wrapped:
            draw_each_line(low, high, time)
        if steps == 4 or wrapped < direct:
            draw_each_line(LANE_MIN, low, time)
            draw_each_line(high, LANE_MAX, time)


def draw_each_line(from_lane: float, to_lane: float, time: float):
    BaseSkin.preview_each_line.draw(layout_each_line(from_lane, to_lane, time), z=get_each_line_z(time))
