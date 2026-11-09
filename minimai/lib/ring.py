from sonolus.script.vec import Vec2

from minimai.lib.layer import LAYER_RING, get_z
from minimai.lib.layout import apply_quad_mirror_option, layout_ring
from minimai.lib.options import Options
from minimai.lib.skin import ActiveSkin


def draw_ring():
    layout = layout_ring()
    z = get_z(LAYER_RING)
    ActiveSkin.ring.draw(layout, z.tuple)
    if ActiveSkin.sensor_outline.is_available and Options.sensor_alpha > 0:
        outline_layout = apply_quad_mirror_option(layout.scale_centered(Vec2.one() * (10.0 / 9.0)))
        outline_z = get_z(LAYER_RING, 0, -1)
        ActiveSkin.sensor_outline.draw(outline_layout, outline_z.tuple, Options.sensor_alpha)
