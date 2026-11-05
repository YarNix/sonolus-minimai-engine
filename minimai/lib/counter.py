from enum import IntEnum, auto
from math import floor

from sonolus.script.runtime import runtime_ui
from sonolus.script.sprite import Sprite

from minimai.lib.layer import LAYER_COUNTER, get_z
from minimai.lib.layout import COUNTER_GLYPH_WIDTHS, layout_counter_glyph
from minimai.lib.options import Options
from minimai.lib.scoring import Grade, ScoreMemory
from minimai.lib.skin import COUNTER_COLOURS, COUNTER_GLYPHS, ActiveSkin


class CenterDisplay(IntEnum):
    OFF = 0
    COMBO = auto()
    GRADE_COMBO = auto()


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

DIGIT_WIDTH = COUNTER_GLYPH_WIDTHS[0]


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


def draw_integer(value: int, colour: CounterColour):
    """A whole number in big digits, centered."""
    ui = runtime_ui().combo_config
    z = get_z(LAYER_COUNTER).tuple
    divisor = 1
    count = 1
    while divisor * 10 <= value:
        divisor *= 10
        count += 1
    left = -count * DIGIT_WIDTH / 2
    while divisor >= 1:
        digit = floor(value / divisor) % 10
        get_counter_sprite(colour, digit).draw(layout_counter_glyph(left, DIGIT_WIDTH, ui.scale), z, ui.alpha)
        left += DIGIT_WIDTH
        divisor /= 10


def draw_center_counter():
    display = Options.center_display
    if display == CenterDisplay.COMBO or display == CenterDisplay.GRADE_COMBO:
        if ScoreMemory.combo > 0:
            colour = CounterColour.PINK
            if display == CenterDisplay.GRADE_COMBO:
                colour = get_grade_colour(ScoreMemory.grade)
            draw_integer(ScoreMemory.combo, colour)
