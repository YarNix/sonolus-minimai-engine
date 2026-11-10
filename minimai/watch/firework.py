from sonolus.script.archetype import WatchArchetype, entity_memory
from sonolus.script.vec import Vec2

from minimai.lib import archetype_names
from minimai.lib.firework import draw_firework, get_firework_end_time


class WatchFirework(WatchArchetype):
    """A firework, spawned by a note's preprocess (``spawn_firework``)."""
    name = archetype_names.FIREWORK

    center: Vec2 = entity_memory()
    start_time: float = entity_memory()
    seed: float = entity_memory()

    def spawn_time(self) -> float:
        return self.start_time

    def despawn_time(self) -> float:
        return get_firework_end_time(self.start_time)

    def update_parallel(self):
        draw_firework(self.center, self.start_time, self.seed)
