from sonolus.script.engine import WatchMode

from minimai.lib.buckets import Buckets
from minimai.lib.effect import Effects
from minimai.lib.particle import BaseParticles
from minimai.lib.skin import BaseSkin
from minimai.watch.update_spawn import update_spawn

watch_mode = WatchMode(
    archetypes=[],
    skin=BaseSkin,
    effects=Effects,
    particles=BaseParticles,
    buckets=Buckets,
    update_spawn=update_spawn,
)
