from sonolus.script.archetype import PlayArchetype, entity_memory
from sonolus.script.runtime import time
from sonolus.script.sprite import Sprite

from minimai.lib import archetype_names
from minimai.lib.game import ArcadeJudgment
from minimai.lib.layer import ZIndexes
from minimai.lib.layout import SlideOkLayout
from minimai.lib.slide_ok import draw_slide_ok, get_slide_ok_end_time, get_slide_ok_sprite


class SlideOk(PlayArchetype):
    """A slide OK, spawned by a judged final slide (``spawn_slide_ok``)."""
    name = archetype_names.SLIDE_OK

    judgment: ArcadeJudgment = entity_memory()
    error: float = entity_memory()
    layout: SlideOkLayout = entity_memory()
    start_time: float = entity_memory()
    z: ZIndexes = entity_memory()

    sprite: Sprite = entity_memory()

    def initialize(self):
        self.sprite @= get_slide_ok_sprite(self.layout, self.judgment, self.error)

    def update_parallel(self):
        if time() >= get_slide_ok_end_time(self.start_time):
            self.despawn = True
            return
        draw_slide_ok(self.sprite, self.layout.quad, self.start_time, self.z)
