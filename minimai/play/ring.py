from sonolus.script.archetype import PlayArchetype

from minimai.lib import archetype_names
from minimai.lib.ring import draw_ring

class Ring(PlayArchetype):
    name = archetype_names.RING

    def spawn_order(self) -> float:
        return -1e8

    def update_parallel(self):
        draw_ring()
