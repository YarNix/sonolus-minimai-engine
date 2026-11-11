from __future__ import annotations

from sonolus.script.archetype import EntityRef, WatchArchetype, callback, entity_data, imported

from minimai.lib import archetype_names
from minimai.lib.each_line import draw_each_line
from minimai.lib.game import Button
from minimai.lib.initialization import init_common
from minimai.watch.base import WatchButtonBase, get_challenge_end_time


class WatchEachLine(WatchArchetype):
    name = archetype_names.EACH_LINE

    left_ref: EntityRef[WatchButtonBase] = imported(name="left")
    right_ref: EntityRef[WatchButtonBase] = imported(name="right")

    start_button: Button = entity_data()
    # Buttons the arc spans clockwise (1..4); 0 = no line (same button).
    steps: int = entity_data()
    start_time: float = entity_data()
    target_time: float = entity_data()
    stops_at_ring: bool = entity_data()
    exit_time: float = entity_data()

    # After the notes' preprocess (their times and mirrored buttons).
    @callback(order=1)
    def preprocess(self):
        init_common()
        left = self.left_ref.get()
        right = self.right_ref.get()
        # The shorter way round: from left clockwise, or from right clockwise.
        steps = (right.button - left.button + 8) % 8
        self.start_button = left.button
        if steps > 4:
            steps = 8 - steps
            self.start_button = right.button
        self.steps = steps
        # The line follows a tap (or star) if there is one: those keep going when late.
        self.start_time = left.start_time
        self.target_time = left.target_time
        self.stops_at_ring = left.is_hold
        if left.is_hold and not right.is_hold:
            self.start_time = right.start_time
            self.target_time = right.target_time
            self.stops_at_ring = False
        # Gone with the first of its notes.
        self.exit_time = min(left.exit_time, right.exit_time)
        if steps == 0:
            self.exit_time = self.start_time

    def spawn_time(self) -> float:
        return self.start_time

    def despawn_time(self) -> float:
        return min(self.exit_time, get_challenge_end_time())

    def update_parallel(self):
        draw_each_line(self.start_button, self.steps, self.start_time, self.target_time, self.stops_at_ring)
