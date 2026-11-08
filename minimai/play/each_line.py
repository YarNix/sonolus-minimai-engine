from __future__ import annotations

from sonolus.script.archetype import EntityRef, PlayArchetype, callback, entity_data, imported
from sonolus.script.runtime import time

from minimai.lib import archetype_names
from minimai.lib.each_line import draw_each_line
from minimai.lib.game import Button
from minimai.lib.scoring import is_challenge_over
from minimai.play.base_input import ButtonBaseInput


class EachLine(PlayArchetype):
    """The arc between two taps / holds / star heads hit together (computed by the level builder:
    neighbours in chart order among the notes of one time)."""

    name = archetype_names.EACH_LINE

    left_ref: EntityRef[ButtonBaseInput] = imported(name="left")
    right_ref: EntityRef[ButtonBaseInput] = imported(name="right")

    start_button: Button = entity_data()
    # Buttons the arc spans clockwise (1..4); 0 = no line (same button).
    steps: int = entity_data()
    start_time: float = entity_data()
    target_time: float = entity_data()
    stops_at_ring: bool = entity_data()

    # After the notes' preprocess (their start / target times).
    @callback(order=1)
    def preprocess(self):
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

    def spawn_order(self) -> float:
        return self.start_time

    def should_spawn(self) -> bool:
        return time() >= self.start_time or is_challenge_over()

    # def initialize(self):
    #     if is_challenge_over():
    #         return

    def update_parallel(self):
        # Gone with the first of its notes.
        if (
            is_challenge_over()
            or self.steps == 0
            or self.left_ref.get().is_despawned
            or self.right_ref.get().is_despawned
        ):
            self.despawn = True
            return
        draw_each_line(self.start_button, self.steps, self.start_time, self.target_time, self.stops_at_ring)
