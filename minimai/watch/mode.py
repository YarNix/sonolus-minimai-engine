from sonolus.script.engine import WatchMode

from minimai.lib.buckets import Buckets
from minimai.lib.effect import Effects
from minimai.lib.particle import BaseParticles
from minimai.lib.skin import BaseSkin
from minimai.watch.activity_manager import WatchActivityManager
from minimai.watch.bpm_change import WatchBpmChange
from minimai.watch.center_counter import WatchCenterCounter
from minimai.watch.each_line import WatchEachLine
from minimai.watch.firework import WatchFirework
from minimai.watch.hold import WATCH_HOLD_ARCHETYPES
from minimai.watch.initialization import WatchInitialization
from minimai.watch.judge_text import WatchJudgeText
from minimai.watch.note import WATCH_NOTE_ARCHETYPES
from minimai.watch.ring import WatchRing
from minimai.watch.slide import WATCH_SLIDE_ARCHETYPES
from minimai.watch.slide_ok import WatchSlideOk
from minimai.watch.touch import WATCH_TOUCH_ARCHETYPES
from minimai.watch.touch_hold import WATCH_TOUCH_HOLD_ARCHETYPES
from minimai.watch.update_spawn import update_spawn

watch_mode = WatchMode(
    archetypes=[
        WatchInitialization,
        WatchRing,
        WatchActivityManager,
        WatchCenterCounter,
        WatchBpmChange,
        *WATCH_NOTE_ARCHETYPES,
        *WATCH_HOLD_ARCHETYPES,
        *WATCH_TOUCH_ARCHETYPES,
        *WATCH_TOUCH_HOLD_ARCHETYPES,
        *WATCH_SLIDE_ARCHETYPES,
        WatchEachLine,
        WatchJudgeText,
        WatchFirework,
        WatchSlideOk,
    ],
    skin=BaseSkin,
    effects=Effects,
    particles=BaseParticles,
    buckets=Buckets,
    update_spawn=update_spawn,
)
