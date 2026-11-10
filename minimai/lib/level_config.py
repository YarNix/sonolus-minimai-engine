from sonolus.script.globals import level_data
from sonolus.script.debug import debug_log

from minimai.lib.layout import from_skin_px
from minimai.lib.options import Options

@level_data
class LevelConfig:
    # Note travel speed, ring units per second.
    noteSpeed: float


def init_level_config():
    # The fitted speed is in reference units per second, 1 unit = 100 skin px.
    LevelConfig.noteSpeed = 107.25 * (Options.tap_speed + 0.9975) ** 0.985558604 / 71.4184491 * from_skin_px(100)

