from sonolus.script.archetype import WatchArchetype, callback, imported

from minimai.lib import archetype_names
from minimai.lib.buckets import init_buckets
from minimai.lib.effect import SfxMemory, schedule_count_in
from minimai.lib.hitbox import init_hitboxes
from minimai.lib.hold import init_hold_life, init_hold_score
from minimai.lib.initialization import init_common
from minimai.lib.note import init_note_life, init_note_score
from minimai.lib.particle import init_particles
from minimai.lib.scoring import init_life_challenge, init_score_multiplier
from minimai.lib.skin import init_skin
from minimai.lib.slide import init_slide_life, init_slide_score
from minimai.lib.touch import init_touch_life, init_touch_score
from minimai.lib.touch_hold import init_touch_hold_life, init_touch_hold_score
from minimai.lib.ui import init_ui
from minimai.watch.activity_manager import WatchActivityManager
from minimai.watch.hold import WATCH_HOLD_ARCHETYPES
from minimai.watch.note import WATCH_NOTE_ARCHETYPES
from minimai.watch.ring import WatchRing
from minimai.watch.slide import WATCH_SLIDE_ARCHETYPES
from minimai.watch.touch import WATCH_TOUCH_ARCHETYPES
from minimai.watch.touch_hold import WATCH_TOUCH_HOLD_ARCHETYPES, schedule_riser


class WatchInitialization(WatchArchetype):
    name = archetype_names.INITIALIZATION

    count_in_bpm: float = imported(name="countInBpm", default=0)
    # 0 when not a replay.
    replay_version: int = imported(name="replayVersion")

    @callback(order=1)
    def preprocess(self):
        init_common()
        init_hitboxes()
        init_skin()
        init_particles()
        init_ui()
        init_buckets()
        init_life_challenge()
        init_score_multiplier()
        init_note_score(WATCH_NOTE_ARCHETYPES)
        init_note_life(WATCH_NOTE_ARCHETYPES)
        init_hold_score(WATCH_HOLD_ARCHETYPES)
        init_hold_life(WATCH_HOLD_ARCHETYPES)
        init_touch_score(WATCH_TOUCH_ARCHETYPES)
        init_touch_life(WATCH_TOUCH_ARCHETYPES)
        init_touch_hold_score(WATCH_TOUCH_HOLD_ARCHETYPES)
        init_touch_hold_life(WATCH_TOUCH_HOLD_ARCHETYPES)
        init_slide_score(WATCH_SLIDE_ARCHETYPES)
        init_slide_life(WATCH_SLIDE_ARCHETYPES)
        WatchRing.spawn()
        WatchActivityManager.spawn()
        schedule_count_in(self.count_in_bpm, SfxMemory.first_note_time)
        schedule_riser()
