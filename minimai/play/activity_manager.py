from __future__ import annotations

from sonolus.script.archetype import PlayArchetype, callback, entity_memory
from sonolus.script.array import Array, Dim
from sonolus.script.containers import VarArray
from sonolus.script.effect import LoopedEffectHandle
from sonolus.script.globals import level_memory
from sonolus.script.record import Record
from sonolus.script.runtime import offset_adjusted_time, time

from minimai.lib import archetype_names
from minimai.lib.effect import (
    TOUCH_HOLD_CHARGE_DURATION,
    Effects,
    SfxMemory,
    first_available_effect,
    stop_looped_sfx,
)
from minimai.lib.options import Options
from minimai.lib.scoring import ScoreSnapshot, get_score_snapshot
from minimai.lib.streams import STREAM_START_TIME, Streams
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


class ActivityManager(PlayArchetype):
    """Per-frame state shared between entities: touch overlaps, the touch hold riser and the score
    stream."""
    name = archetype_names.ACTIVITY_MANAGER

    # One riser however many touch holds want it.
    riser_active: bool = entity_memory()
    riser_start_time: float = entity_memory()
    charge_handle: LoopedEffectHandle = entity_memory()
    sustain_handle: LoopedEffectHandle = entity_memory()

    recorded_riser: bool = entity_memory()
    recorded_score: ScoreSnapshot = entity_memory()

    def initialize(self):
        Streams.touch_hold_riser[STREAM_START_TIME] = False
        self.recorded_score @= get_score_snapshot()
        Streams.score[STREAM_START_TIME] = self.recorded_score

    # Before the touches and touch holds register.
    @callback(order=-1)
    def update_sequential(self):
        for entries in OverlapMemory.sensors:
            entries.clear()
        SfxMemory.touch_hold_riser_count = 0

    def update_parallel(self):
        self.record_riser()
        # After every judgment of the frame is reported.
        self.record_score()
        self.update_riser()
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

    def terminate(self):
        stop_looped_sfx(self.charge_handle)
        stop_looped_sfx(self.sustain_handle)

    def update_riser(self):
        """The charge loops (so it can be cut off) until it reaches its end, then the sustain loops."""
        if not Options.touch_sound:
            return
        if SfxMemory.touch_hold_riser_count == 0:
            stop_looped_sfx(self.charge_handle)
            stop_looped_sfx(self.sustain_handle)
            self.riser_active = False
        elif not self.riser_active:
            self.riser_active = True
            self.riser_start_time = time()
            if Effects.touch_hold_start.is_available:
                self.charge_handle @= Effects.touch_hold_start.loop()
            else:
                self.start_sustain()
        elif self.charge_handle.id != 0 and time() - self.riser_start_time >= TOUCH_HOLD_CHARGE_DURATION:
            stop_looped_sfx(self.charge_handle)
            self.start_sustain()

    def record_riser(self):
        wanted = SfxMemory.touch_hold_riser_count > 0
        if wanted != self.recorded_riser:
            Streams.touch_hold_riser[offset_adjusted_time()] = wanted
            self.recorded_riser = wanted

    def record_score(self):
        score = get_score_snapshot()
        if score != self.recorded_score:
            Streams.score[offset_adjusted_time()] = score
            self.recorded_score @= score

    def start_sustain(self):
        sustain = first_available_effect(Effects.touch_hold_sustain, Effects.touch_hold_sustain_fallback)
        if sustain.is_available:
            self.sustain_handle @= sustain.loop()


def register_touch_overlap(sensor: int, start_time: float, index: int, kind: TouchKind):
    """A touch is visible on ``sensor`` this frame."""
    entries = OverlapMemory.sensors[sensor - 1]
    if not entries.is_full():
        entries.append(OverlapEntry(start_time=start_time, index=index, kind=kind))
