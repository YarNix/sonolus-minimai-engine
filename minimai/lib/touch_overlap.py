from __future__ import annotations

from sonolus.script.array import Array, Dim
from sonolus.script.containers import VarArray
from sonolus.script.globals import level_memory
from sonolus.script.record import Record

from minimai.lib.touch import TouchKind, draw_touch_overlap


class OverlapEntry(Record):
    """A touch visible on a sensor this frame."""
    start_time: float
    # Breaks ties between touches that appear together.
    index: int
    kind: TouchKind

    def is_before(self, other: OverlapEntry) -> bool:
        return self.start_time < other.start_time or (
            self.start_time == other.start_time and self.index < other.index
        )


# Per sensor; only the 2nd and 3rd touch to appear are drawn.
OverlapEntries = VarArray[OverlapEntry, Dim[8]]


@level_memory
class OverlapMemory:
    sensors: Array[OverlapEntries, Dim[33]]


def clear_touch_overlaps():
    """Every frame, before the touches register (sequential callbacks only)."""
    for entries in OverlapMemory.sensors:
        entries.clear()


def register_touch_overlap(sensor: int, start_time: float, index: int, kind: TouchKind):
    """A touch is visible on ``sensor`` this frame (sequential callbacks only)."""
    entries = OverlapMemory.sensors[sensor - 1]
    if not entries.is_full():
        entries.append(OverlapEntry(start_time=start_time, index=index, kind=kind))


def draw_touch_overlaps():
    """After the touches register (parallel callbacks)."""
    for i, entries in enumerate(OverlapMemory.sensors):
        if len(entries) < 2:
            continue
        for entry in entries:
            rank = 1
            # Can't sort entries in update_parallel
            # Loop is cheapest
            for other in entries:
                if other.is_before(entry):
                    rank += 1
            if rank == 2 or rank == 3:
                draw_touch_overlap(entry.kind, i + 1, rank)
