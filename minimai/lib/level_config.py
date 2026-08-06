from sonolus.script.globals import level_data
from sonolus.script.debug import debug_log

from minimai.lib.options import Options

@level_data
class LevelConfig:
    noteSpeed: float


def init_level_config():
    LevelConfig.noteSpeed = 107.25 * (Options.tap_speed + 0.9975) ** 0.985558604 / 71.4184491

