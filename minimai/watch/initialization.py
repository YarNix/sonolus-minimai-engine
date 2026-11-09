from sonolus.script.archetype import WatchArchetype, callback, imported

from minimai.lib import archetype_names
from minimai.lib.buckets import init_buckets
from minimai.lib.effect import SfxMemory, init_sfx_memory, schedule_count_in
from minimai.lib.hitbox import init_hitboxes
from minimai.lib.layout import init_layout
from minimai.lib.level_config import init_level_config
from minimai.lib.particle import init_particles
from minimai.lib.scoring import init_life_challenge, init_score_multiplier
from minimai.lib.skin import init_skin
from minimai.lib.ui import init_ui
from minimai.watch.ring import WatchRing


class WatchInitialization(WatchArchetype):
    name = archetype_names.INITIALIZATION

    count_in_bpm: float = imported(name="countInBpm", default=0)
    # 0 when not a replay.
    replay_version: int = imported(name="replayVersion")

    @callback(order=1)
    def preprocess(self):
        init_level_config()
        init_layout()
        init_hitboxes()
        init_skin()
        init_particles()
        init_ui()
        init_buckets()
        init_life_challenge()
        init_score_multiplier()
        # The notes' score and life, once they have watch archetypes:
        # init_note_score(WATCH_NOTE_ARCHETYPES)
        # init_note_life(WATCH_NOTE_ARCHETYPES)
        WatchRing.spawn()
        init_sfx_memory()
        schedule_count_in(self.count_in_bpm, SfxMemory.first_note_time)
