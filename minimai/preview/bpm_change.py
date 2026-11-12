from sonolus.script.archetype import PreviewArchetype, StandardImport
from sonolus.script.printing import PrintColor, PrintFormat
from sonolus.script.runtime import HorizontalAlign
from sonolus.script.timing import beat_to_time
from sonolus.script.vec import Vec2

from minimai.lib import archetype_names
from minimai.preview.layout import LANE_MAX, lane_to_x, print_in_view, time_to_col, time_to_y


class PreviewBpmChange(PreviewArchetype):
    name = archetype_names.BPM_CHANGE

    beat: StandardImport.BEAT
    bpm: StandardImport.BPM

    def render(self):
        time = beat_to_time(self.beat)
        col = time_to_col(time)
        print_in_view(
            self.bpm,
            Vec2(lane_to_x(LANE_MAX, col), time_to_y(time, col)),
            Vec2(1, 0),
            fmt=PrintFormat.BPM,
            color=PrintColor.YELLOW,
            horizontal_align=HorizontalAlign.RIGHT,
        )
