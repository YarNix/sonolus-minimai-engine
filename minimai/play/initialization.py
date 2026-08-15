from sonolus.script.archetype import EntityRef, PlayArchetype, callback, exported, imported

from minimai.lib import archetype_names
# from minimai.lib.baseevent import init_event_list
from minimai.lib.buckets import init_buckets
from minimai.lib.layout import init_layout
from minimai.lib.hitbox import init_hitboxes
from minimai.lib.level_config import init_level_config
# from minimai.lib.note import init_life, init_score
from minimai.lib.particle import init_particles
from minimai.lib.skin import init_skin
from minimai.lib.ui import init_ui
from minimai.play.input_manager import InputManager
from minimai.play.ring import Ring


class Initialization(PlayArchetype):
    name = archetype_names.INITIALIZATION

    @callback(order=-1)
    def preprocess(self):
        init_level_config()
        init_layout()
        init_hitboxes()
        init_skin()
        init_particles()
        init_ui()
        init_buckets()
        # init_score(NOTE_ARCHETYPES)
        # init_life(NOTE_ARCHETYPES, self.initial_life)
        # init_play_common()
        # init_event_list(self.first_camera_ref)

    def initialize(self):
        InputManager.spawn()
        Ring.spawn()

    def spawn_order(self) -> float:
        return -1e8

    def should_spawn(self) -> bool:
        return True

    def update_parallel(self):
        self.despawn = True
