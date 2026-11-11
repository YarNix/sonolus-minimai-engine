from sonolus.script.archetype import EntityRef, WatchArchetype, entity_memory
from sonolus.script.containers import sort_linked_entities
from sonolus.script.runtime import is_replay, time

from minimai.lib import archetype_names
from minimai.lib.counter import draw_center_counter
from minimai.lib.options import Options
from minimai.lib.scoring import Grade, ScoreSnapshot, get_dx, set_score_snapshot
from minimai.lib.streams import STREAM_START_TIME, Streams
from minimai.watch.base import ScoreTimeline, WatchScoredBase


class WatchCenterCounter(WatchArchetype):
    """Shows the score as play did: from the replay's score stream, or without a replay from the
    score timeline (every note a critical perfect)."""
    name = archetype_names.CENTER_COUNTER

    # The last note judged by now on the score timeline (0: none yet).
    cursor: EntityRef[WatchScoredBase] = entity_memory()

    def spawn_time(self) -> float:
        return -1e8

    def despawn_time(self) -> float:
        return 1e8

    def update_sequential(self):
        if is_replay():
            set_score_snapshot(Streams.score.get_previous_inclusive(time()))
        else:
            self.move_cursor()
            set_score_snapshot(self.get_timeline_snapshot())

    def update_parallel(self):
        draw_center_counter()

    def move_cursor(self):
        """A step or two a frame; a seek walks from where it was."""
        while self.cursor.index > 0 and self.cursor.get().score_time > time():
            self.cursor.index = self.cursor.get().score_prev.index
        next_index = ScoreTimeline.head.index
        if self.cursor.index > 0:
            next_index = self.cursor.get().score_next.index
        while next_index > 0 and WatchScoredBase.at(next_index).score_time <= time():
            self.cursor.index = next_index
            next_index = WatchScoredBase.at(next_index).score_next.index

    def get_timeline_snapshot(self) -> ScoreSnapshot:
        count = 0
        base = 0.0
        bonus = 0.0
        if self.cursor.index > 0:
            note = self.cursor.get()
            count = note.score_count
            base = note.score_base
            bonus = note.score_bonus
        life = 0
        if Options.life_challenge > 0:
            life = max(Options.life_challenge - Options.critical_perfect_loss * count, 0)
        return ScoreSnapshot(
            base_earned=base,
            base_lost=0,
            bonus_earned=bonus,
            bonus_lost=0,
            dx_earned=get_dx() * count,
            dx_lost=0,
            combo=count,
            grade=Grade.AP_PLUS,
            life=life,
        )


def build_score_timeline():
    """Preprocess, after every note's: sorts the score timeline and sums it up, and finds when a
    replay's Life Challenge ended."""
    ScoreTimeline.challenge_end_time = 1e8
    if is_replay():
        if Options.life_challenge > 0 and Options.end_at_zero_life:
            for at, snapshot in Streams.score.iter_items_from(STREAM_START_TIME):
                if snapshot.life <= 0:
                    ScoreTimeline.challenge_end_time = at
                    break
        return
    if ScoreTimeline.head.index == 0:
        return
    ScoreTimeline.head.index = sort_linked_entities(
        ScoreTimeline.head,
        get_value=lambda note: note.score_time,
        get_next_ref=lambda note: note.score_next,
        get_prev_ref=lambda note: note.score_prev,
    ).index
    count = 0
    base = 0.0
    bonus = 0.0
    index = ScoreTimeline.head.index
    while index > 0:
        note = WatchScoredBase.at(index)
        count += note.score_count
        base += note.score_base
        bonus += note.score_bonus
        note.score_count = count
        note.score_base = base
        note.score_bonus = bonus
        index = note.score_next.index
