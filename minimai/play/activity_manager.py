from __future__ import annotations

from sonolus.script.archetype import PlayArchetype, callback, entity_memory
from sonolus.script.effect import LoopedEffectHandle
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
from minimai.lib.touch_overlap import clear_touch_overlaps, draw_touch_overlaps


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
        clear_touch_overlaps()
        SfxMemory.touch_hold_riser_count = 0

    def update_parallel(self):
        self.record_riser()
        # After every judgment of the frame is reported.
        self.record_score()
        self.update_riser()
        draw_touch_overlaps()

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
