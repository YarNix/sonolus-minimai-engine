"""Achievement, DX score, combo and grade."""

from enum import IntEnum, auto
from math import floor
from typing import Protocol, ClassVar

from sonolus.script.globals import level_memory
from sonolus.script.runtime import level_score, level_life
from sonolus.script.archetype import LifeInfo

from minimai.lib.game import ArcadeJudgment

class BaseWeight:
    """Base weight of each note types; Break doesn't have weight, and use different base"""
    TAP = 1.0
    HOLD = 2.0
    SLIDE = 3.0

class JudgmentMultiplier:
    PERFECT = 1.0
    GREAT = 0.8
    GOOD = 0.5
    MISS = 0.0

class Grade(IntEnum):
    """The best result still reachable."""
    AP_PLUS = 0
    AP = auto()
    FC_PLUS = auto()
    FC = auto()
    NONE = auto()

class WeightedArchetype(Protocol):
    is_scored: ClassVar[bool]
    archetype_score_multiplier: ClassVar[float]
    archetype_life: ClassVar[LifeInfo]
    key: int | float

    @classmethod
    def score_weight(cls) -> float: ...


@level_memory
class ScoreMemory:
    total_base: float
    total_bonus: float
    total_dx: float
    base_earned: float
    base_lost: float
    bonus_earned: float
    bonus_lost: float
    dx_earned: float
    dx_lost: float
    combo: int
    grade: Grade


def add_note_to_total(weight: float, is_break: bool):
    """For a scored note (preprocess)."""
    if is_break:
        ScoreMemory.total_base += get_break_base()
        ScoreMemory.total_bonus += get_break_bonus()
    else:
        ScoreMemory.total_base += get_normal_base() * weight
    ScoreMemory.total_dx += get_dx()
    update_life()


def get_base_rate(judgment: ArcadeJudgment) -> float:
    """Part of a non-break note's base score."""
    result = 0.0
    if judgment <= ArcadeJudgment.LOW_PERFECT:
        result = 1.0
    elif judgment <= ArcadeJudgment.LOW_GREAT:
        result = 0.8
    elif judgment == ArcadeJudgment.GOOD:
        result = 0.5
    return result

def get_normal_base(judgment: ArcadeJudgment = ArcadeJudgment.CRITICAL_PERFECT) -> float:
    return 500 * get_base_rate(judgment)

def get_break_base(judgment: ArcadeJudgment = ArcadeJudgment.CRITICAL_PERFECT) -> float:
    result = 0.0
    if judgment <= ArcadeJudgment.LOW_PERFECT:
        result = 2500.0
    elif judgment == ArcadeJudgment.CRITICAL_GREAT:
        result = 2000.0
    elif judgment == ArcadeJudgment.HIGH_GREAT:
        result = 1500.0
    elif judgment == ArcadeJudgment.LOW_GREAT:
        result = 1250.0
    elif judgment == ArcadeJudgment.GOOD:
        result = 1000.0
    return result


def get_break_bonus(judgment: ArcadeJudgment = ArcadeJudgment.CRITICAL_PERFECT) -> float:
    result = 0.0
    if judgment == ArcadeJudgment.CRITICAL_PERFECT:
        result = 100.0
    elif judgment == ArcadeJudgment.HIGH_PERFECT:
        result = 75.0
    elif judgment == ArcadeJudgment.LOW_PERFECT:
        result = 50.0
    elif judgment <= ArcadeJudgment.LOW_GREAT:
        result = 40.0
    elif judgment == ArcadeJudgment.GOOD:
        result = 30.0
    return result


def get_dx(judgment: ArcadeJudgment = ArcadeJudgment.CRITICAL_PERFECT) -> float:
    result = 0.0
    if judgment == ArcadeJudgment.CRITICAL_PERFECT:
        result = 3.0
    elif judgment <= ArcadeJudgment.LOW_PERFECT:
        result = 2.0
    elif judgment <= ArcadeJudgment.LOW_GREAT:
        result = 1.0
    return result


def get_grade(judgment: ArcadeJudgment, is_break: bool) -> Grade:
    """The best grade a chart with this judgment in it can still get."""
    result = Grade.NONE
    if judgment == ArcadeJudgment.CRITICAL_PERFECT or (not is_break and judgment <= ArcadeJudgment.LOW_PERFECT):
        result = Grade.AP_PLUS
    elif judgment <= ArcadeJudgment.LOW_PERFECT:
        result = Grade.AP
    elif judgment <= ArcadeJudgment.LOW_GREAT:
        result = Grade.FC_PLUS
    elif judgment == ArcadeJudgment.GOOD:
        result = Grade.FC
    return result


def report_score(weight: float, is_break: bool, judgment: ArcadeJudgment):
    """A scored note's final judgment (sequential callbacks only)."""
    if judgment == ArcadeJudgment.NONE:
        return
    if is_break:
        earned = get_break_base(judgment)
        ScoreMemory.base_earned += earned
        ScoreMemory.base_lost += get_break_base() - earned
        bonus = get_break_bonus(judgment)
        ScoreMemory.bonus_earned += bonus
        ScoreMemory.bonus_lost += get_break_bonus() - bonus
    else:
        earned = get_normal_base(judgment) * weight
        ScoreMemory.base_earned += earned
        ScoreMemory.base_lost += get_normal_base() * weight - earned
    ScoreMemory.dx_earned += get_dx(judgment)
    ScoreMemory.dx_lost += get_dx() - get_dx(judgment)
    if judgment == ArcadeJudgment.MISS:
        ScoreMemory.combo = 0
    else:
        ScoreMemory.combo += 1
    ScoreMemory.grade = max(ScoreMemory.grade, get_grade(judgment, is_break))


def get_base_total() -> float:
    return max(ScoreMemory.total_base, 1)


def get_bonus_total() -> float:
    """A chart with no break has no bonus: it tops out at 100%."""
    return max(ScoreMemory.total_bonus, 1)


def get_achievement() -> float:
    """In percent, rising from 0."""
    return ScoreMemory.base_earned / get_base_total() * 100 + ScoreMemory.bonus_earned / get_bonus_total()


def get_achievement_from_100() -> float:
    """In percent: 100 less the lost base score, plus the break bonus earned."""
    base = (ScoreMemory.total_base - ScoreMemory.base_lost) / get_base_total() * 100
    return base + ScoreMemory.bonus_earned / get_bonus_total()


def get_achievement_from_101() -> float:
    """In percent: 101 less everything lost."""
    base = (ScoreMemory.total_base - ScoreMemory.base_lost) / get_base_total() * 100
    return base + (ScoreMemory.total_bonus - ScoreMemory.bonus_lost) / get_bonus_total()


# A DX rank (✧1 to ✧5) is held while the DX score still reachable is above this part of the max.
DX_RANK_BORDERS = (0.85, 0.90, 0.93, 0.95, 0.97)


def get_dx_remaining() -> float:
    """The DX score still reachable."""
    return ScoreMemory.total_dx - ScoreMemory.dx_lost


def get_dx_rank() -> int:
    """0 below ✧1."""
    rank = 0
    ratio = get_dx_remaining() / max(ScoreMemory.total_dx, 1)
    for border in DX_RANK_BORDERS:
        if ratio > border:
            rank += 1
    return rank


def get_dx_rank_margin() -> int:
    """DX score above the current rank's border: how much can still be lost before dropping a rank."""
    lowest = 0.0
    ratio = get_dx_remaining() / max(ScoreMemory.total_dx, 1)
    for border in DX_RANK_BORDERS:
        if ratio > border:
            lowest = floor(ScoreMemory.total_dx * border) + 1
    return get_dx_remaining() - lowest


# Break use their how weight for scoring
MAX_BREAK_WEIGHT = get_break_base() / get_normal_base()

def init_score_multiplier():
    level_score().update(
        perfect_multiplier=JudgmentMultiplier.PERFECT,
        great_multiplier=JudgmentMultiplier.GREAT,
        good_multiplier=JudgmentMultiplier.GOOD,
    )

CLEAR_BORDER = 0.8
LIFE_PER_WEIGHT = 25


def get_life_loss(multiplier: float, weight: float) -> int:
    return round((JudgmentMultiplier.PERFECT - multiplier) * weight * LIFE_PER_WEIGHT)


def init_life_loss(archetype: type[WeightedArchetype], weight: float):
    archetype.archetype_life.update(
        perfect_increment=-get_life_loss(JudgmentMultiplier.PERFECT, weight),
        great_increment=-get_life_loss(JudgmentMultiplier.GREAT, weight),
        good_increment=-get_life_loss(JudgmentMultiplier.GOOD, weight),
        miss_increment=-get_life_loss(JudgmentMultiplier.MISS, weight),
    )


def update_life():
    """Update initial life when score total change."""
    # Every note's base score at a perfect is its score weight in normal bases.
    total_weight = ScoreMemory.total_base / get_normal_base()
    min_lost = LIFE_PER_WEIGHT // 10
    # Life 0 needs more lost than the margin: below the border, not on it.
    initial = round(total_weight * LIFE_PER_WEIGHT * (1 - CLEAR_BORDER)) + min_lost
    level_life().update(initial=initial, maximum=initial)
