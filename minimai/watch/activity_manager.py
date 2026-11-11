from sonolus.script.archetype import WatchArchetype, callback
from sonolus.script.runtime import is_replay

from minimai.lib import archetype_names
from minimai.lib.judge_text import clear_judge_text_slots
from minimai.lib.touch_feedback import draw_input_feedbacks, draw_touch_feedbacks, replay_input, replay_touch_feedback
from minimai.lib.touch_overlap import clear_touch_overlaps, draw_touch_overlaps


class WatchActivityManager(WatchArchetype):
    """Per-frame state shared between entities: touch overlaps, judge text slots, and the replay's
    touch feedback and held input."""
    name = archetype_names.ACTIVITY_MANAGER

    def spawn_time(self) -> float:
        return -1e8

    def despawn_time(self) -> float:
        return 1e8

    # Before the touches and judge texts register.
    @callback(order=-1)
    def update_sequential(self):
        clear_touch_overlaps()
        clear_judge_text_slots()
        if is_replay():
            replay_touch_feedback()
            replay_input()

    def update_parallel(self):
        draw_touch_overlaps()
        draw_touch_feedbacks()
        draw_input_feedbacks()
