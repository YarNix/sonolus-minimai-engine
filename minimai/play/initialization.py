from sonolus.script.archetype import EntityRef, PlayArchetype, callback, exported, imported

from minimai.lib import archetype_names
from minimai.lib.buckets import init_buckets
from minimai.lib.effect import schedule_count_in
from minimai.lib.layout import init_layout
from minimai.lib.hitbox import init_hitboxes
from minimai.lib.level_config import init_level_config
from minimai.lib.hold import init_hold_life, init_hold_score
from minimai.lib.note import init_note_life, init_note_score
from minimai.lib.scoring import init_score_multiplier, init_life_challenge
from minimai.lib.slide import init_slide_life, init_slide_score
from minimai.lib.touch import init_touch_life, init_touch_score
from minimai.lib.touch_hold import init_touch_hold_life, init_touch_hold_score
from minimai.lib.particle import init_particles
from minimai.lib.skin import init_skin
from minimai.lib.ui import init_ui
from minimai.play.input_manager import InputManager
from minimai.play.activity_manager import ActivityManager, SfxMemory
from minimai.play.ring import Ring
from minimai.play.center_counter import CenterCounter
from minimai.lib.counter import CenterDisplay
from minimai.lib.options import Options
from minimai.play.hold import HOLD_ARCHETYPES
from minimai.play.note import NOTE_ARCHETYPES
from minimai.play.slide import SLIDE_ARCHETYPES
from minimai.play.touch import TOUCH_ARCHETYPES
from minimai.play.touch_hold import TOUCH_HOLD_ARCHETYPES

def init_score():
    init_score_multiplier()
    init_note_score(NOTE_ARCHETYPES)
    init_hold_score(HOLD_ARCHETYPES)
    init_touch_score(TOUCH_ARCHETYPES)
    init_touch_hold_score(TOUCH_HOLD_ARCHETYPES)
    init_slide_score(SLIDE_ARCHETYPES)

def init_life():
    init_note_life(NOTE_ARCHETYPES)
    init_hold_life(HOLD_ARCHETYPES)
    init_touch_life(TOUCH_ARCHETYPES)
    init_touch_hold_life(TOUCH_HOLD_ARCHETYPES)
    init_slide_life(SLIDE_ARCHETYPES)

class Initialization(PlayArchetype):
    name = archetype_names.INITIALIZATION

    count_in_bpm: float = imported(name="countInBpm", default=0)

    @callback(order=-1)
    def preprocess(self):
        SfxMemory.first_note_time = 1e9
        init_level_config()
        init_layout()
        init_hitboxes()
        init_skin()
        init_particles()
        init_ui()
        init_buckets()
        init_life_challenge()
        init_score()
        init_life()
        # init_play_common()

    def initialize(self):
        schedule_count_in(self.count_in_bpm, SfxMemory.first_note_time)
        InputManager.spawn()
        ActivityManager.spawn()
        Ring.spawn()
        if Options.center_display != CenterDisplay.OFF or Options.life_challenge > 0:
            CenterCounter.spawn()

    def spawn_order(self) -> float:
        return -1e8

    def should_spawn(self) -> bool:
        return True

    def update_parallel(self):
        self.despawn = True
