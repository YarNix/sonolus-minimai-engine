from sonolus.script.engine import PlayMode

from minimai.play.initialization import Initialization
from minimai.play.input_manager import InputManager
from minimai.play.activity_manager import ActivityManager
from minimai.play.bpm_change import BpmChange
from minimai.play.note import NOTE_ARCHETYPES
from minimai.play.hold import HOLD_ARCHETYPES
from minimai.play.ring import Ring
from minimai.play.each_line import EachLine
from minimai.play.touch import TOUCH_ARCHETYPES
from minimai.play.touch_hold import TOUCH_HOLD_ARCHETYPES
from minimai.play.slide import SLIDE_ARCHETYPES

from minimai.lib.buckets import Buckets
from minimai.lib.effect import Effects
from minimai.lib.particle import BaseParticles
from minimai.lib.skin import BaseSkin

play_mode = PlayMode(
    archetypes=[
        Initialization,
        InputManager,
        ActivityManager,
        Ring,
        BpmChange,
        *NOTE_ARCHETYPES,
        *HOLD_ARCHETYPES,
        *TOUCH_ARCHETYPES,
        *TOUCH_HOLD_ARCHETYPES,
        *SLIDE_ARCHETYPES,
        EachLine,
    ],
    skin=BaseSkin,
    effects=Effects,
    particles=BaseParticles,
    buckets=Buckets,
)