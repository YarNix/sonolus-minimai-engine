from sonolus.script.globals import level_memory

from minimai.lib.effect import init_sfx_memory
from minimai.lib.layout import init_layout


@level_memory
class InitMemory:
    inited: bool


def init_common():
    """Play and watch preprocess: the state most archetypes read there. Every archetype calls it
    first; it runs once, in whichever comes first."""
    if InitMemory.inited:
        return
    InitMemory.inited = True
    init_layout()
    init_sfx_memory()
