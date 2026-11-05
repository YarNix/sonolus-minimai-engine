from enum import IntEnum, auto

from sonolus.script.archetype import get_archetype_by_name
from sonolus.script.interval import remap_clamped
from sonolus.script.quad import Quad
from sonolus.script.runtime import time
from sonolus.script.sprite import Sprite

from minimai.lib import archetype_names
from minimai.lib.game import ArcadeJudgment
from minimai.lib.judge_text import passes_filter
from minimai.lib.layer import LAYER_SLIDE_OK, ZIndexes
from minimai.lib.layout import SlideOkLayout
from minimai.lib.options import Options
from minimai.lib.skin import ActiveSkin

# Seconds, before Effect Animation Speed.
SLIDE_OK_FADE_IN = 0.033
SLIDE_OK_FADE_OUT = (0.283, 0.417)


class SlideOkGrade(IntEnum):
    CRITICAL_PERFECT = 0
    JUST_PERFECT = auto()
    FAST_PERFECT = auto()
    LATE_PERFECT = auto()
    FAST_GREAT = auto()
    LATE_GREAT = auto()
    FAST_GOOD = auto()
    LATE_GOOD = auto()
    TOO_LATE = auto()


SLIDE_OK_GRADES = len(SlideOkGrade)


def get_slide_ok_sprite(layout: SlideOkLayout, judgment: ArcadeJudgment, error: float) -> Sprite:
    """A critical perfect shows Perfect unless Show Critical Perfect Text is on.
    A fast/late perfect (Strict Slide Judgment only) shows Perfect when the skin doesn't have it."""
    state = layout.shape
    if not layout.is_right:
        state += 3
    is_fast = error < 0
    grade = SlideOkGrade.TOO_LATE
    if judgment == ArcadeJudgment.CRITICAL_PERFECT:
        grade = SlideOkGrade.JUST_PERFECT
        if Options.critical_perfect_text:
            grade = SlideOkGrade.CRITICAL_PERFECT
    elif judgment <= ArcadeJudgment.LOW_PERFECT:
        grade = SlideOkGrade.LATE_PERFECT
        if is_fast:
            grade = SlideOkGrade.FAST_PERFECT
    elif judgment <= ArcadeJudgment.LOW_GREAT:
        grade = SlideOkGrade.LATE_GREAT
        if is_fast:
            grade = SlideOkGrade.FAST_GREAT
    elif judgment == ArcadeJudgment.GOOD:
        grade = SlideOkGrade.LATE_GOOD
        if is_fast:
            grade = SlideOkGrade.FAST_GOOD
    result = +ActiveSkin.slide_oks[state * SLIDE_OK_GRADES + grade]
    if grade <= SlideOkGrade.LATE_PERFECT and not result.is_available:
        result @= ActiveSkin.slide_oks[state * SLIDE_OK_GRADES + SlideOkGrade.JUST_PERFECT]
    return result


def get_slide_ok_sort_group(judgment: ArcadeJudgment) -> int:
    """Worse judgments on top; every critical perfect is below, whatever text it shows."""
    result = 4
    if judgment == ArcadeJudgment.CRITICAL_PERFECT:
        result = 0
    elif judgment <= ArcadeJudgment.LOW_PERFECT:
        result = 1
    elif judgment <= ArcadeJudgment.LOW_GREAT:
        result = 2
    elif judgment == ArcadeJudgment.GOOD:
        result = 3
    return result


def spawn_slide_ok(judgment: ArcadeJudgment, error: float, layout: SlideOkLayout, chart_time: float, index: int):
    """For a judged final slide (play only).
    ``error`` is as for the judge text;
    ``chart_time`` and ``index`` order slide OKs of the same sort group (Slide OK Order)."""
    if Options.sonolus_judgment or judgment == ArcadeJudgment.NONE or not passes_filter(Options.judge_text, judgment):
        return
    sprite = get_slide_ok_sprite(layout, judgment, error)
    if not sprite.is_available:
        return
    order = chart_time
    tie = index
    if Options.slide_ok_order == 0:
        order = -chart_time
        tie = -index
    get_archetype_by_name(archetype_names.SLIDE_OK).spawn(
        sprite=sprite,
        quad=layout.quad,
        start_time=time(),
        z=ZIndexes(z1=LAYER_SLIDE_OK, z2=get_slide_ok_sort_group(judgment), z3=order, z4=tie),
    )


def get_slide_ok_end_time(start_time: float) -> float:
    return start_time + SLIDE_OK_FADE_OUT[1] / Options.effect_animation_speed


def draw_slide_ok(sprite: Sprite, quad: Quad, start_time: float, z: ZIndexes):
    elapsed = (time() - start_time) * Options.effect_animation_speed
    alpha = remap_clamped(0, SLIDE_OK_FADE_IN, 0, 1, elapsed) * remap_clamped(*SLIDE_OK_FADE_OUT, 1, 0, elapsed)
    if alpha > 0:
        sprite.draw(quad, z.tuple, alpha)
