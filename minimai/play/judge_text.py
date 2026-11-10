from sonolus.script.archetype import PlayArchetype, entity_memory
from sonolus.script.runtime import time

from minimai.lib import archetype_names
from minimai.lib.game import ArcadeJudgment
from minimai.lib.judge_text import (
    JudgeTextSprites,
    draw_judge_text,
    get_judge_text_end_time,
    get_judge_text_sprites,
    is_latest_judge_text,
    register_judge_text,
)
from minimai.lib.layout import JudgeTextLayout


class JudgeText(PlayArchetype):
    """A judge text and fast/late, spawned by a judged note (``spawn_judge_text``)."""
    name = archetype_names.JUDGE_TEXT

    judgment: ArcadeJudgment = entity_memory()
    is_break: bool = entity_memory()
    error: float = entity_memory()
    slot: int = entity_memory()
    layout: JudgeTextLayout = entity_memory()
    start_time: float = entity_memory()

    sprites: JudgeTextSprites = entity_memory()
    registered: bool = entity_memory()

    def initialize(self):
        self.sprites @= get_judge_text_sprites(self.judgment, self.is_break, self.error)

    def update_sequential(self):
        if self.registered or not self.sprites.is_visible():
            return
        self.registered = True
        register_judge_text(self.slot, self.index, self.start_time)

    def update_parallel(self):
        if not is_latest_judge_text(self.slot, self.index) or time() >= get_judge_text_end_time(self.start_time):
            self.despawn = True
            return
        draw_judge_text(self.sprites, self.layout, self.start_time)
