from sonolus.script.archetype import PlayArchetype, entity_memory
from sonolus.script.runtime import time
from sonolus.script.vec import Vec2

from minimai.lib import archetype_names
from minimai.lib.firework import draw_firework, get_firework_end_time


class Firework(PlayArchetype):
    """A firework, spawned by a hit note with the firework flag (``spawn_firework``)."""
    name = archetype_names.FIREWORK

    center: Vec2 = entity_memory()
    start_time: float = entity_memory()
    # Picks the firework's layout (ray hues, sparkle places) so no two look the same.
    seed: float = entity_memory()

    def update_parallel(self):
        if time() >= get_firework_end_time(self.start_time):
            self.despawn = True
            return
        draw_firework(self.center, self.start_time, self.seed)
