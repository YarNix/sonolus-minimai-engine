from sonolus.script.archetype import WatchArchetype, callback

from minimai.lib import archetype_names
from minimai.lib.touch_overlap import clear_touch_overlaps, draw_touch_overlaps


class WatchActivityManager(WatchArchetype):
    """Per-frame state shared between entities: touch overlaps."""
    name = archetype_names.ACTIVITY_MANAGER

    def spawn_time(self) -> float:
        return -1e8

    def despawn_time(self) -> float:
        return 1e8

    # Before the touches register.
    @callback(order=-1)
    def update_sequential(self):
        clear_touch_overlaps()

    def update_parallel(self):
        draw_touch_overlaps()
