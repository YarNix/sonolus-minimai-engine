from minimai.lib.hitbox import init_hitboxes
from minimai.lib.layout import init_layout
from minimai.lib.options import Options
from minimai.lib.particle import init_particles
from minimai.lib.skin import init_skin
from minimai.lib.ui import init_ui
from minimai.tutorial.framework import TUTORIAL_TAP_SPEED, TUTORIAL_TOUCH_SCALE, TUTORIAL_TOUCH_SPEED


def preprocess():
    init_layout(
        tap_speed=TUTORIAL_TAP_SPEED,
        touch_speed=TUTORIAL_TOUCH_SPEED,
        touch_scale=Options.touch_scale * TUTORIAL_TOUCH_SCALE,
    )
    init_hitboxes()
    init_ui()
    init_skin()
    init_particles()
