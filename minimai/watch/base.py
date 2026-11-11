from __future__ import annotations

from sonolus.script.archetype import EntityRef, WatchArchetype, entity_data, imported
from sonolus.script.globals import level_memory

from minimai.lib.game import Button
from minimai.lib.scoring import get_break_base, get_break_bonus, get_normal_base


class WatchScoredBase(WatchArchetype):
    """Notes that can be scored. Without a replay, the scored ones are linked in judgment order, each
    with the totals once it is judged, for the center counter."""
    score_next: EntityRef[WatchScoredBase] = entity_data()
    score_prev: EntityRef[WatchScoredBase] = entity_data()
    score_time: float = entity_data()
    # This note's score until ``build_score_timeline``, then the totals up to it.
    score_count: int = entity_data()
    score_base: float = entity_data()
    score_bonus: float = entity_data()

    def add_to_score_timeline(self, at: float, weight: float, is_break: bool):
        """Preprocess, without a replay: a critical perfect ``at``."""
        self.score_time = at
        self.score_count = 1
        if is_break:
            self.score_base = get_break_base()
            self.score_bonus = get_break_bonus()
        else:
            self.score_base = get_normal_base() * weight
            self.score_bonus = 0
        self.score_next.index = ScoreTimeline.head.index
        ScoreTimeline.head.index = self.index


@level_memory
class ScoreTimeline:
    # Without a replay: the first scored note to be judged (``build_score_timeline``).
    head: EntityRef[WatchScoredBase]
    # When End at 0 Life drops the notes left (1e8: never).
    challenge_end_time: float


def get_challenge_end_time() -> float:
    return ScoreTimeline.challenge_end_time


class WatchButtonBase(WatchScoredBase):
    """Taps, stars and holds: what an each line needs from its notes."""
    button: Button = imported(default=1)
    firework: bool = imported(default=False)

    target_time: float = entity_data()
    # When the note appears (each lines appear with it).
    start_time: float = entity_data()
    # Holds stop at the ring; taps and stars keep going when late.
    is_hold: bool = entity_data()
    # When the note despawns.
    exit_time: float = entity_data()
