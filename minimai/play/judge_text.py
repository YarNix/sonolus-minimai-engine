from sonolus.script.archetype import PlayArchetype, entity_memory
from sonolus.script.array import Array, Dim
from sonolus.script.globals import level_memory
from sonolus.script.quad import Quad
from sonolus.script.runtime import time
from sonolus.script.sprite import Sprite

from minimai.lib import archetype_names
from minimai.lib.judge_text import JUDGE_TEXT_SLOT_COUNT, draw_judge_text, get_judge_text_end_time

IndexMemory = Array[int, Dim[74]]
TimingMemory = Array[float, Dim[74]]
# Pylance complains if we use variable instead of a literal number so this check is here
assert JUDGE_TEXT_SLOT_COUNT == IndexMemory.size()
assert JUDGE_TEXT_SLOT_COUNT == TimingMemory.size()

@level_memory
class JudgeTextMemory:
    # The newest text per slot (0 = none yet).
    latest_index: IndexMemory
    latest_start_time: TimingMemory


class JudgeText(PlayArchetype):
    """A judge text and fast/late, spawned by a judged note (``spawn_judge_text``)."""
    name = archetype_names.JUDGE_TEXT

    text: Sprite = entity_memory()
    shine: Sprite = entity_memory()
    text_quad: Quad = entity_memory()
    fast_late: Sprite = entity_memory()
    fast_late_quad: Quad = entity_memory()
    start_time: float = entity_memory()
    slot: int = entity_memory()

    registered: bool = entity_memory()

    def update_sequential(self):
        if self.registered:
            return
        self.registered = True
        if (
            JudgeTextMemory.latest_index[self.slot] == 0
            or self.start_time >= JudgeTextMemory.latest_start_time[self.slot]
        ):
            JudgeTextMemory.latest_index[self.slot] = self.index
            JudgeTextMemory.latest_start_time[self.slot] = self.start_time

    def update_parallel(self):
        if JudgeTextMemory.latest_index[self.slot] != self.index or time() >= get_judge_text_end_time(self.start_time):
            self.despawn = True
            return
        draw_judge_text(self.text, self.shine, self.text_quad, self.fast_late, self.fast_late_quad, self.start_time)
