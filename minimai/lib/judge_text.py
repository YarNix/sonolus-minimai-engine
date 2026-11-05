from enum import IntEnum, auto
from math import floor

from sonolus.script.archetype import get_archetype_by_name
from sonolus.script.interval import remap_clamped
from sonolus.script.quad import Quad
from sonolus.script.runtime import time
from sonolus.script.sprite import Sprite
from sonolus.script.vec import Vec2

from minimai.lib import archetype_names
from minimai.lib.game import ArcadeJudgment, Button, Sensor
from minimai.lib.layer import LAYER_JUDGE_TEXT, get_z
from minimai.lib.layout import JudgeTextLayout
from minimai.lib.options import Options
from minimai.lib.skin import ActiveSkin

EMPTY_SPRITE = Sprite(-1)

# Seconds, before Effect Animation Speed.
JUDGE_TEXT_DURATION = 0.35
# The text pops from this scale to 1 at the start.
JUDGE_TEXT_POP_SCALE = 1.2
JUDGE_TEXT_POP_DURATION = 0.067
JUDGE_TEXT_FADE_START = 0.167
JUDGE_TEXT_FADE_END = 0.267
# A break's critical perfect shine is on every other 2-frame step until the fade ends.
JUDGE_TEXT_SHINE_RATE = 30

# One text at a time per place: the 8 buttons, then the 33 sensors for touches, then again for
# touch holds. A newer text there replaces the older.
BUTTON_SLOT_START = 0
TOUCH_SLOT_START = 8
TOUCH_HOLD_SLOT_START = 8 + 33
JUDGE_TEXT_SLOT_COUNT = 8 + 33 + 33


class JudgeTextFilter(IntEnum):
    """Which judgments show their text (the Judge Text option)."""
    ALL = 0
    BELOW_CRITICAL_PERFECT = auto()
    BELOW_PERFECT = auto()
    BELOW_GREAT = auto()
    MISS_ONLY = auto()
    OFF = auto()


def passes_filter(text_filter: int, judgment: ArcadeJudgment) -> bool:
    result = False
    if text_filter == JudgeTextFilter.ALL:
        result = True
    elif text_filter == JudgeTextFilter.BELOW_CRITICAL_PERFECT:
        result = judgment > ArcadeJudgment.CRITICAL_PERFECT
    elif text_filter == JudgeTextFilter.BELOW_PERFECT:
        result = judgment > ArcadeJudgment.LOW_PERFECT
    elif text_filter == JudgeTextFilter.BELOW_GREAT:
        result = judgment > ArcadeJudgment.LOW_GREAT
    elif text_filter == JudgeTextFilter.MISS_ONLY:
        result = judgment == ArcadeJudgment.MISS
    return result


class FastLateFilter(IntEnum):
    """Which judgments show fast/late (the Fast/Late option)."""
    BELOW_CRITICAL_PERFECT = 0
    BELOW_PERFECT = auto()
    BELOW_GREAT = auto()
    OFF = auto()


class FastLateStyle(IntEnum):
    """How fast/late shows (the Fast/Late Style option)."""
    # Fast/late beside the judge text (in its place when the skin has no judge text sprite).
    WITH_JUDGMENT = 0
    # The judge text's fast/late version instead of both, when the skin has it.
    FAST_LATE_JUDGMENT = auto()
    # Fast/late instead of the judge text.
    FAST_LATE_ONLY = auto()


def shows_fast_late(judgment: ArcadeJudgment, error: float) -> bool:
    result = False
    if ArcadeJudgment.CRITICAL_PERFECT < judgment < ArcadeJudgment.MISS and error != 0:
        text_filter = Options.fast_late
        if text_filter == FastLateFilter.BELOW_CRITICAL_PERFECT:
            result = True
        elif text_filter == FastLateFilter.BELOW_PERFECT:
            result = judgment > ArcadeJudgment.LOW_PERFECT
        elif text_filter == FastLateFilter.BELOW_GREAT:
            result = judgment > ArcadeJudgment.LOW_GREAT
    return result


def button_slot(button: Button) -> int:
    return BUTTON_SLOT_START + button - 1


def touch_slot(sensor: Sensor) -> int:
    return TOUCH_SLOT_START + sensor - 1


def touch_hold_slot(sensor: Sensor) -> int:
    return TOUCH_HOLD_SLOT_START + sensor - 1


def shows_critical_perfect_text() -> bool:
    """Critical perfects show their own text (else Perfect's)."""
    return Options.critical_perfect_text and ActiveSkin.judge_critical_perfect.is_available


def get_judge_text_sprite(judgment: ArcadeJudgment) -> Sprite:
    result = +ActiveSkin.judge_miss
    if judgment == ArcadeJudgment.CRITICAL_PERFECT:
        if shows_critical_perfect_text():
            result @= ActiveSkin.judge_critical_perfect
        else:
            result @= ActiveSkin.judge_perfect
    elif judgment <= ArcadeJudgment.LOW_PERFECT:
        result @= ActiveSkin.judge_perfect
    elif judgment <= ArcadeJudgment.LOW_GREAT:
        result @= ActiveSkin.judge_great
    elif judgment == ArcadeJudgment.GOOD:
        result @= ActiveSkin.judge_good
    return result


def get_judge_text_with_fast_late(judgment: ArcadeJudgment, is_fast: bool) -> Sprite:
    """The judge text's fast/late version (perfect, great or good; may be missing from the skin)."""
    result = +EMPTY_SPRITE
    if judgment == ArcadeJudgment.CRITICAL_PERFECT:
        pass
    elif judgment <= ArcadeJudgment.LOW_PERFECT:
        if is_fast:
            result @= ActiveSkin.judge_perfect_fast
        else:
            result @= ActiveSkin.judge_perfect_late
    elif judgment <= ArcadeJudgment.LOW_GREAT:
        if is_fast:
            result @= ActiveSkin.judge_great_fast
        else:
            result @= ActiveSkin.judge_great_late
    elif judgment == ArcadeJudgment.GOOD:
        if is_fast:
            result @= ActiveSkin.judge_good_fast
        else:
            result @= ActiveSkin.judge_good_late
    return result


def get_judge_text_shine(is_break: bool, judgment: ArcadeJudgment) -> Sprite:
    """Only a break's critical perfect shines. Without the sprite the text doesn't blink."""
    result = +EMPTY_SPRITE
    if is_break and judgment == ArcadeJudgment.CRITICAL_PERFECT:
        if shows_critical_perfect_text():
            result @= ActiveSkin.judge_critical_perfect_shine
        else:
            result @= ActiveSkin.judge_perfect_shine
    return result


def spawn_judge_text(judgment: ArcadeJudgment, is_break: bool, error: float, slot: int, layout: JudgeTextLayout):
    """The judge text and fast/late of a judged note (play only).
    ``error`` is the hit time minus the target time; a hit off by nothing has no fast/late."""
    if Options.sonolus_judgment or Options.judge_text_distance <= 0 or judgment == ArcadeJudgment.NONE:
        return
    # The Judge Text filter hides fast/late too, whatever the style.
    if not passes_filter(Options.judge_text, judgment):
        return
    style = Options.fast_late_style
    text = +get_judge_text_sprite(judgment)
    shine = +get_judge_text_shine(is_break, judgment)
    fast_late = +EMPTY_SPRITE
    if shows_fast_late(judgment, error):
        if error < 0:
            fast_late @= ActiveSkin.judge_fast
        else:
            fast_late @= ActiveSkin.judge_late
    if style == FastLateStyle.FAST_LATE_JUDGMENT and text.is_available and fast_late.is_available:
        # Without the fast/late version in the skin, both show as With Judgment.
        combined = get_judge_text_with_fast_late(judgment, error < 0)
        if combined.is_available:
            text @= combined
            fast_late @= EMPTY_SPRITE
    if style == FastLateStyle.FAST_LATE_ONLY and fast_late.is_available:
        text @= EMPTY_SPRITE
        shine @= EMPTY_SPRITE
    if not text.is_available and not fast_late.is_available:
        return
    fast_late_quad = +layout.fast_late_alone
    if text.is_available:
        fast_late_quad @= layout.fast_late
    get_archetype_by_name(archetype_names.JUDGE_TEXT).spawn(
        text=text,
        shine=shine,
        text_quad=layout.text,
        fast_late=fast_late,
        fast_late_quad=fast_late_quad,
        start_time=time(),
        slot=slot,
    )


def get_judge_text_end_time(start_time: float) -> float:
    return start_time + JUDGE_TEXT_DURATION / Options.effect_animation_speed


def draw_judge_text(text: Sprite, shine: Sprite, text_quad: Quad, fast_late: Sprite, fast_late_quad: Quad, start_time: float):
    elapsed = (time() - start_time) * Options.effect_animation_speed
    scale = remap_clamped(0, JUDGE_TEXT_POP_DURATION, JUDGE_TEXT_POP_SCALE, 1, elapsed)
    alpha = remap_clamped(JUDGE_TEXT_FADE_START, JUDGE_TEXT_FADE_END, 1, 0, elapsed)
    if alpha <= 0:
        return
    factor = Vec2(scale, scale)
    # Newer texts on top.
    if text.is_available:
        layout = text_quad.scale_centered(factor)
        text.draw(layout, get_z(LAYER_JUDGE_TEXT, start_time, 0, invert_time=True).tuple, alpha)
        if shine.is_available and floor(elapsed * JUDGE_TEXT_SHINE_RATE) % 2 == 1:
            shine.draw(layout, get_z(LAYER_JUDGE_TEXT, start_time, 1, invert_time=True).tuple, alpha)
    if fast_late.is_available:
        fast_late.draw(
            fast_late_quad.scale_centered(factor),
            get_z(LAYER_JUDGE_TEXT, start_time, 2, invert_time=True).tuple,
            alpha,
        )
