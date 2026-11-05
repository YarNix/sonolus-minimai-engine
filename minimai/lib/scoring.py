"""Achievement, DX score, combo and grade."""

from enum import IntEnum, auto

from sonolus.script.globals import level_memory

from minimai.lib.game import ArcadeJudgment

class BaseWeight:
    """Base weight of each note types; Break doesn't have weight, and use different base"""
    TAP = 1.0
    HOLD = 2.0
    SLIDE = 3.0

class Grade(IntEnum):
    """The best result still reachable."""
    AP_PLUS = 0
    AP = auto()
    FC_PLUS = auto()
    FC = auto()
    NONE = auto()


@level_memory
class ScoreMemory:
    total_base: float
    total_bonus: float
    total_dx: float
    base_earned: float
    base_lost: float
    bonus_earned: float
    bonus_lost: float
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
