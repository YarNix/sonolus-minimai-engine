from sonolus.script.engine import WatchMode

from minimai.lib.buckets import Buckets
from minimai.lib.effect import Effects
from minimai.lib.particle import BaseParticles
from minimai.lib.skin import BaseSkin
from minimai.watch.bpm_change import WatchBpmChange
from minimai.watch.each_line import WatchEachLine
from minimai.watch.initialization import WatchInitialization
from minimai.watch.note import WATCH_NOTE_ARCHETYPES
from minimai.watch.ring import WatchRing
from minimai.watch.update_spawn import update_spawn

watch_mode = WatchMode(
    archetypes=[
        WatchInitialization,
        WatchRing,
        WatchBpmChange,
        *WATCH_NOTE_ARCHETYPES,
        WatchEachLine,
    ],
    skin=BaseSkin,
    effects=Effects,
    particles=BaseParticles,
    buckets=Buckets,
    update_spawn=update_spawn,
)
