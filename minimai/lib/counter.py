from enum import IntEnum, auto
from math import floor

from sonolus.script.runtime import runtime_ui
from sonolus.script.sprite import Sprite

from minimai.lib.layer import LAYER_COUNTER, get_z
from minimai.lib.layout import (
    COUNTER_GLYPH_WIDTHS,
    COUNTER_PERCENT_SIZE,
    COUNTER_SMALL_SIZE,
    COUNTER_SMALL_TRACKING,
    layout_counter_glyph,
)
from minimai.lib.options import Options
from minimai.lib.scoring import (
    Grade,
    ScoreMemory,
    get_achievement,
    get_achievement_from_100,
    get_achievement_from_101,
)
from minimai.lib.skin import COUNTER_COLOURS, COUNTER_GLYPHS, ActiveSkin


class CenterDisplay(IntEnum):
    OFF = 0
    COMBO = auto()
    GRADE_COMBO = auto()
    ACHIEVEMENT = auto()
    ACHIEVEMENT_FROM_100 = auto()
    ACHIEVEMENT_FROM_101 = auto()


class CounterColour(IntEnum):
    YELLOW = 0
    PINK = auto()
    GREEN = auto()
    SILVER = auto()
    BLUE = auto()
    RED = auto()
    GOLD = auto()


class CounterGlyph(IntEnum):
    ZERO = 0
    ONE = 1
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    DOT = auto()
    PERCENT = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()


assert len(CounterColour) == len(COUNTER_COLOURS)
assert len(CounterGlyph) == len(COUNTER_GLYPHS)

DIGIT_WIDTH = COUNTER_GLYPH_WIDTHS[CounterGlyph.ZERO]
DOT_WIDTH = COUNTER_GLYPH_WIDTHS[CounterGlyph.DOT]
PERCENT_WIDTH = COUNTER_GLYPH_WIDTHS[CounterGlyph.PERCENT]

ACHIEVEMENT_DECIMALS = 4
ACHIEVEMENT_STEPS = 10**ACHIEVEMENT_DECIMALS
# Added before flooring, so a division landing just under a step (99.99999999) still shows 100.
ACHIEVEMENT_EPSILON = 1e-3


def get_counter_sprite(colour: CounterColour, glyph: int) -> Sprite:
    return ActiveSkin.counter_glyphs[colour * len(COUNTER_GLYPHS) + glyph]


def get_grade_colour(grade: Grade) -> CounterColour:
    result = CounterColour.SILVER
    if grade == Grade.AP_PLUS:
        result = CounterColour.GOLD
    elif grade == Grade.AP:
        result = CounterColour.YELLOW
    elif grade == Grade.FC_PLUS:
        result = CounterColour.PINK
    elif grade == Grade.FC:
        result = CounterColour.GREEN
    return result


def get_achievement_colour(achievement: float) -> CounterColour:
    result = CounterColour.BLUE
    if achievement >= 100:
        result = CounterColour.GOLD
    elif achievement >= 97:
        result = CounterColour.YELLOW
    elif achievement >= 80:
        result = CounterColour.RED
    return result


def get_digit_count(value: int) -> int:
    count = 1
    divisor = 10
    while divisor <= value:
        divisor *= 10
        count += 1
    return count


def draw_glyph(colour: CounterColour, glyph: int, left: float, width: float, size: float) -> float:
    """Draws a glyph at ``size`` of the big digits, on their baseline. Returns its right edge."""
    ui = runtime_ui().combo_config
    layout = layout_counter_glyph(left, width, ui.scale, size)
    get_counter_sprite(colour, glyph).draw(layout, get_z(LAYER_COUNTER).tuple, ui.alpha)
    return left + width * size


def draw_digits(value: int, count: int, colour: CounterColour, left: float, size: float, tracking: float) -> float:
    """``value`` as ``count`` digits, with leading zeros. Returns the right edge."""
    divisor = 1
    for _ in range(count - 1):
        divisor *= 10
    while divisor >= 1:
        left = draw_glyph(colour, floor(value / divisor) % 10, left, DIGIT_WIDTH, size) + tracking
        divisor /= 10
    return left


def draw_integer(value: int, colour: CounterColour):
    """A whole number in big digits, centered."""
    count = get_digit_count(value)
    draw_digits(value, count, colour, -count * DIGIT_WIDTH / 2, 1, 0)


def draw_achievement(achievement: float):
    """As "101.0000%": the whole part big, the decimals and % small, centered."""
    units = floor(achievement * ACHIEVEMENT_STEPS + ACHIEVEMENT_EPSILON)
    whole = floor(units / ACHIEVEMENT_STEPS)
    count = get_digit_count(whole)
    colour = get_achievement_colour(units / ACHIEVEMENT_STEPS)
    small_run = (
        (DOT_WIDTH + ACHIEVEMENT_DECIMALS * DIGIT_WIDTH) * COUNTER_SMALL_SIZE
        + PERCENT_WIDTH * COUNTER_PERCENT_SIZE
        + (ACHIEVEMENT_DECIMALS + 1) * COUNTER_SMALL_TRACKING
    )
    left = -(count * DIGIT_WIDTH + small_run) / 2
    left = draw_digits(whole, count, colour, left, 1, 0)
    left = draw_glyph(colour, CounterGlyph.DOT, left, DOT_WIDTH, COUNTER_SMALL_SIZE) + COUNTER_SMALL_TRACKING
    left = draw_digits(
        units - whole * ACHIEVEMENT_STEPS, ACHIEVEMENT_DECIMALS, colour, left, COUNTER_SMALL_SIZE, COUNTER_SMALL_TRACKING
    )
    draw_glyph(colour, CounterGlyph.PERCENT, left, PERCENT_WIDTH, COUNTER_PERCENT_SIZE)


def draw_center_counter():
    display = Options.center_display
    if display == CenterDisplay.COMBO or display == CenterDisplay.GRADE_COMBO:
        if ScoreMemory.combo > 0:
            colour = CounterColour.PINK
            if display == CenterDisplay.GRADE_COMBO:
                colour = get_grade_colour(ScoreMemory.grade)
            draw_integer(ScoreMemory.combo, colour)
    elif display == CenterDisplay.ACHIEVEMENT:
        draw_achievement(get_achievement())
    elif display == CenterDisplay.ACHIEVEMENT_FROM_100:
        draw_achievement(get_achievement_from_100())
    elif display == CenterDisplay.ACHIEVEMENT_FROM_101:
        draw_achievement(get_achievement_from_101())
