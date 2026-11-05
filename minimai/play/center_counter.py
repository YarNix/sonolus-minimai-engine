from sonolus.script.archetype import PlayArchetype

from minimai.lib import archetype_names
from minimai.lib.counter import draw_center_counter


class CenterCounter(PlayArchetype):
    name = archetype_names.CENTER_COUNTER

    def spawn_order(self) -> float:
        return -1e8

    def update_parallel(self):
        draw_center_counter()
