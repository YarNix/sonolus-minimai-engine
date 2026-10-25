from minimai.lib.layout import init_layout
# from minimai.lib.level_config import init_level_config
from minimai.lib.particle import init_particles
from minimai.lib.skin import init_skin
from minimai.lib.ui import init_ui


def preprocess():
    # init_level_config()
    init_layout()
    init_ui()
    init_skin()
    init_particles()