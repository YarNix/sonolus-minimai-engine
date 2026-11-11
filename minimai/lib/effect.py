from enum import IntEnum, auto
from math import ceil

from sonolus.script.effect import Effect, LoopedEffectHandle, StandardEffect, effect, effects
from sonolus.script.globals import level_memory
from sonolus.script.runtime import is_watch

from minimai.lib.game import ArcadeJudgment
from minimai.lib.options import Options

EMPTY_EFFECT = Effect(-1)


@effects
class Effects:
    tap_perfect: StandardEffect.PERFECT
    tap_great: StandardEffect.GREAT
    tap_good: StandardEffect.GOOD
    tap_ex: StandardEffect.PERFECT_ALTERNATIVE
    break_hit_fallback: StandardEffect.GREAT_ALTERNATIVE
    touch_hit_fallback: StandardEffect.GOOD_ALTERNATIVE
    touch_hold_sustain_fallback: StandardEffect.HOLD

    break_hit: Effect = effect("Mai Break Hit")
    break_critical: Effect = effect("Mai Break Critical")
    # Mai Break Hit and Mai Break Critical mixed, so a live play doesn't cut one off with the other.
    break_critical_hit: Effect = effect("Mai Break Critical Hit")
    touch_hit: Effect = effect("Mai Touch Hit")
    firework: Effect = effect("Mai Firework")
    # Played as a loop only so it can be cut off on release.
    touch_hold_start: Effect = effect("Mai Touch Hold Start")
    touch_hold_sustain: Effect = effect("Mai Touch Hold Sustain")
    slide: Effect = effect("Mai Slide")
    break_slide: Effect = effect("Mai Break Slide")
    break_slide_end: Effect = effect("Mai Break Slide End")
    # Mai Break Slide End and Mai Break Critical mixed.
    break_slide_end_critical: Effect = effect("Mai Break Slide End Critical")
    guide: Effect = effect("Mai Guide")
    count_in: Effect = effect("Mai Count In")


# Same clip within this many seconds plays once (each pairs, touch groups).
SFX_DISTANCE = 0.02
# The same for scheduled sounds (watch, Auto SFX, the slide sound), other than the guide and count-in.
SCHEDULED_SFX_DISTANCE = 0.08
# A scheduled Mai Break Critical this soon after the last one is skipped.
BREAK_CRITICAL_DISTANCE = 0.3
# When Mai Touch Hold Start hands over to the sustain loop; the riser is cut at this point.
TOUCH_HOLD_CHARGE_DURATION = 10.0
# The guide plays a frame early.
GUIDE_OFFSET = -1 / 60
# Ticks before the first note, at most.
COUNT_IN_TICKS = 4
# Sounds scheduled earlier than this don't play, even though the level starts earlier.
COUNT_IN_EARLIEST_TIME = -1.0


class TapSoundJudgment(IntEnum):
    """Which judgments make a Tap/Hold sound."""
    GOOD_PERFECT = 0
    GOOD_CRITICAL_PERFECT = auto()
    CRITICAL_PERFECT_ONLY = auto()
    PERFECT_ONLY = auto()


def first_available_effect(*args: Effect) -> Effect:
    result = +EMPTY_EFFECT
    for e in args:
        if e.is_available:
            result @= e
            break
    return result


def is_hit(judgment: ArcadeJudgment) -> bool:
    return judgment != ArcadeJudgment.NONE and judgment != ArcadeJudgment.MISS


def emit_sfx(sfx: Effect, at: float, scheduled: bool, scheduled_distance: float = SCHEDULED_SFX_DISTANCE):
    """A hit sound: played now, or with auto SFX scheduled ``at`` (from preprocess).
    Each path only runs in its own mode, so the archetypes can call both. Watch only schedules."""
    if sfx.is_available:
        if scheduled:
            if Options.auto_sfx or is_watch():
                sfx.schedule(at, scheduled_distance)
        elif not Options.auto_sfx:
            sfx.play(SFX_DISTANCE)


def get_plain_tap_sfx(judgment: ArcadeJudgment) -> Effect:
    """The Tap/Hold grade sound, gated by the Tap/Hold Sound Judgment option."""
    gate = Options.tap_sound_judgment
    allowed = False
    if not is_hit(judgment) or not Options.tap_sound:
        allowed = False
    elif gate == TapSoundJudgment.GOOD_PERFECT:
        allowed = judgment != ArcadeJudgment.CRITICAL_PERFECT
    elif gate == TapSoundJudgment.GOOD_CRITICAL_PERFECT:
        allowed = True
    elif gate == TapSoundJudgment.CRITICAL_PERFECT_ONLY:
        allowed = judgment == ArcadeJudgment.CRITICAL_PERFECT
    else:
        allowed = judgment <= ArcadeJudgment.LOW_PERFECT
    result = +EMPTY_EFFECT
    if not allowed:
        pass
    elif judgment <= ArcadeJudgment.LOW_PERFECT:
        result @= Effects.tap_perfect
    elif judgment <= ArcadeJudgment.LOW_GREAT:
        result @= Effects.tap_great
    else:
        result @= Effects.tap_good
    return result


def uses_break_critical_mix(mix: Effect, scheduled: bool) -> bool:
    """The mixed clip when the pack has it, except when scheduled: a scheduled clip can't cut the one
    before, so Mai Break Critical is scheduled on its own (when the pack has it) and doesn't pile up."""
    return mix.is_available and not (scheduled and Effects.break_critical.is_available)


def emit_break_hit_sfx(judgment: ArcadeJudgment, at: float, scheduled: bool):
    if not is_hit(judgment) or not Options.break_sound:
        return
    if judgment == ArcadeJudgment.CRITICAL_PERFECT and uses_break_critical_mix(Effects.break_critical_hit, scheduled):
        emit_sfx(Effects.break_critical_hit, at, scheduled)
        return
    emit_sfx(first_available_effect(Effects.break_hit, Effects.break_hit_fallback), at, scheduled)
    if judgment == ArcadeJudgment.CRITICAL_PERFECT:
        emit_sfx(Effects.break_critical, at, scheduled, BREAK_CRITICAL_DISTANCE)


def emit_ex_sfx(judgment: ArcadeJudgment, at: float, scheduled: bool):
    if is_hit(judgment) and Options.ex_sound:
        emit_sfx(Effects.tap_ex, at, scheduled)


def emit_tap_sfx(is_break: bool, is_ex: bool, judgment: ArcadeJudgment, at: float, scheduled: bool):
    """Tap, star or hold head hit: break, then EX, then the grade sound."""
    if is_break:
        emit_break_hit_sfx(judgment, at, scheduled)
    elif is_ex:
        emit_ex_sfx(judgment, at, scheduled)
    else:
        emit_sfx(get_plain_tap_sfx(judgment), at, scheduled)


def emit_hold_end_sfx(judgment: ArcadeJudgment, at: float, scheduled: bool):
    """Hold and touch hold end: the grade sound of the final judgment, never break or EX."""
    emit_sfx(get_plain_tap_sfx(judgment), at, scheduled)


def emit_touch_sfx(is_break: bool, judgment: ArcadeJudgment, at: float, scheduled: bool):
    if is_break:
        emit_break_hit_sfx(judgment, at, scheduled)
    elif is_hit(judgment) and Options.touch_sound:
        emit_sfx(first_available_effect(Effects.touch_hit, Effects.touch_hit_fallback), at, scheduled)


def emit_firework_sfx(firework: bool, judgment: ArcadeJudgment, at: float, scheduled: bool):
    if firework and is_hit(judgment) and Options.misc_sound:
        emit_sfx(Effects.firework, at, scheduled)


def schedule_slide_sfx(is_break: bool, start_time: float):
    """When the star starts travelling, live or auto, so tapping the star doesn't play it with the
    star's own hit and guide sounds. Slides starting together play one."""
    if not Options.slide_sound:
        return
    sfx = +EMPTY_EFFECT
    if is_break:
        sfx @= Effects.break_slide
    else:
        sfx @= Effects.slide
    if sfx.is_available:
        sfx.schedule(start_time, SCHEDULED_SFX_DISTANCE)


def emit_break_slide_end_sfx(judgment: ArcadeJudgment, at: float, scheduled: bool):
    """Only a critical perfect break slide."""
    if judgment != ArcadeJudgment.CRITICAL_PERFECT:
        return
    if uses_break_critical_mix(Effects.break_slide_end_critical, scheduled):
        if Options.slide_sound:
            emit_sfx(Effects.break_slide_end_critical, at, scheduled)
        return
    if Options.slide_sound:
        emit_sfx(Effects.break_slide_end, at, scheduled)
    if Options.break_sound:
        emit_sfx(Effects.break_critical, at, scheduled, BREAK_CRITICAL_DISTANCE)


def schedule_guide_sfx(at: float):
    if Options.guide_sound and Effects.guide.is_available:
        Effects.guide.schedule(at + GUIDE_OFFSET, SFX_DISTANCE)


@level_memory
class SfxMemory:
    # Touch holds that want the riser this frame.
    touch_hold_riser_count: int
    # The earliest note, for the count-in. Written in preprocess.
    first_note_time: float


def init_sfx_memory():
    SfxMemory.first_note_time = 1e9


def report_note_time(target_time: float):
    """Preprocess only: a note at ``target_time``, for the count-in."""
    SfxMemory.first_note_time = min(SfxMemory.first_note_time, target_time)


def register_touch_hold_riser():
    """A touch hold wants the riser this frame (sequential callbacks only)."""
    SfxMemory.touch_hold_riser_count += 1


def schedule_count_in(bpm: float, first_note_time: float):
    """Schedule `COUNT_IN_TICKS` ticks one beat apart, within [`COUNT_IN_EARLIEST_TIME`, first_note_time].
    
    Count in usually ends at beat 0 (time 0).
    If the first tick would be too early, the ticks move later;
    If the later ticks would be after the first note, they are removed."""
    if not Options.guide_sound or not Effects.count_in.is_available:
        return
    # Also false for NaN.
    if not 0 < bpm < 1e6:
        return
    interval = 60 / bpm
    ticks = COUNT_IN_TICKS
    while ticks > 0:
        minimum_beat = COUNT_IN_EARLIEST_TIME / interval
        beats = ticks - 1  # First beat already included
        # rounding slack keeps a tick that lands right on the bound
        last_beat = max(0, ceil(minimum_beat + beats + 1 - 1e-6))
        if (last_beat * interval) <= first_note_time:
            for tick in range(ticks, 0, -1):
                Effects.count_in.schedule((last_beat - tick) * interval, SFX_DISTANCE)
            return
        ticks -= 1


def schedule_touch_hold_riser(start: float, end: float):
    """The riser from ``start`` to ``end``, scheduled (preprocess): the charge loops until it reaches
    its end, then the sustain loops."""
    if not Options.touch_sound or end <= start:
        return
    sustain_start = start
    if Effects.touch_hold_start.is_available:
        sustain_start = start + TOUCH_HOLD_CHARGE_DURATION
        Effects.touch_hold_start.schedule_loop(start).stop(min(end, sustain_start))
    if sustain_start < end:
        sustain = first_available_effect(Effects.touch_hold_sustain, Effects.touch_hold_sustain_fallback)
        if sustain.is_available:
            sustain.schedule_loop(sustain_start).stop(end)


def stop_looped_sfx(handle: LoopedEffectHandle):
    if handle.id != 0:
        handle.stop()
        handle.id = 0
