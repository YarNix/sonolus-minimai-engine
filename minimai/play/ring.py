
from sonolus.script.quad import Quad, QuadLike, Rect
from sonolus.script.record import Record
from sonolus.script.sprite import Sprite
from sonolus.script.vec import Vec2
from sonolus.script.archetype import PlayArchetype, shared_memory

from minimai.lib import archetype_names
from minimai.lib.options import Options
from minimai.lib.skin import ActiveSkin
from minimai.lib.layer import get_z, LAYER_RING
from minimai.lib.layout import layout_ring

class Ring(PlayArchetype):
    name = archetype_names.RING

    def spawn_order(self) -> float:
        return -1e8

    def update_parallel(self):
        layout = layout_ring()
        z = get_z(LAYER_RING)
        ActiveSkin.ring.draw(layout, z.tuple)