from sonolus.script.archetype import WatchArchetype

from minimai.lib import archetype_names
from minimai.lib.ring import draw_ring


class WatchRing(WatchArchetype):
    name = archetype_names.RING

    def spawn_time(self) -> float:
        return -1e8

    def despawn_time(self) -> float:
        return 1e8

    def update_parallel(self):
        draw_ring()
