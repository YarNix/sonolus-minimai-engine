from sonolus.script.archetype import WatchArchetype, entity_memory

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


class WatchJudgeText(WatchArchetype):
    """A judge text and fast/late, spawned by a note's preprocess (``spawn_judge_text``)."""
    name = archetype_names.JUDGE_TEXT

    judgment: ArcadeJudgment = entity_memory()
    is_break: bool = entity_memory()
    error: float = entity_memory()
    slot: int = entity_memory()
    layout: JudgeTextLayout = entity_memory()
    start_time: float = entity_memory()

    sprites: JudgeTextSprites = entity_memory()

    def spawn_time(self) -> float:
        return self.start_time

    def despawn_time(self) -> float:
        return get_judge_text_end_time(self.start_time)

    def initialize(self):
        self.sprites @= get_judge_text_sprites(self.judgment, self.is_break, self.error)

    def update_sequential(self):
        if self.sprites.is_visible():
            register_judge_text(self.slot, self.index, self.start_time)

    def update_parallel(self):
        if is_latest_judge_text(self.slot, self.index):
            draw_judge_text(self.sprites, self.layout, self.start_time)
