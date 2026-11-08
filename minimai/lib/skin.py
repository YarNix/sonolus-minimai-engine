from math import pi, sin

from sonolus.script.array_like import ArrayLike, check_positive_index
from sonolus.script.debug import static_error
from sonolus.script.globals import level_data
from sonolus.script.num import Num
from sonolus.script.quad import Quad
from sonolus.script.runtime import time
from sonolus.script.record import Record
from sonolus.script.sprite import RenderMode, Sprite, SpriteGroup, StandardSprite, ZIndex, pad_z_indexes, skin, sprite, sprite_group

SLIDE_OK_STATES = ("Curve R", "Straight R", "Wifi Up", "Curve L", "Straight L", "Wifi Down")
SLIDE_OK_GRADES = (
    "Critical Perfect", "Just Perfect",
    "Fast Perfect", "Late Perfect",
    "Fast Great", "Late Great",
    "Fast Good", "Late Good",
    "Too Late",
)
COUNTER_COLOURS = ("Yellow", "Pink", "Green", "Silver", "Blue", "Red", "Gold")
COUNTER_GLYPHS = ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "Dot", "Percent", "Plus", "Minus", "Star")

@skin
class BaseSkin:
    render_mode: RenderMode = RenderMode.LIGHTWEIGHT

    # Simple sprites for debug drawing purposes
    white_square: Sprite = sprite("White Square")
    white_outline: Sprite = sprite("White Outline")

    normal_line: Sprite = sprite("Mai Normal Line")
    break_line: Sprite = sprite("Mai Break Line")
    each_line: Sprite = sprite("Mai Each Line")
    star_line: Sprite = sprite("Mai Star Line")
    each_ring_line: SpriteGroup = sprite_group(f"Mai Each Ring Line {i}" for i in range(1, 5))

    normal_note: Sprite = sprite("Mai Normal Note")
    break_note: Sprite = sprite("Mai Break Note")
    break_note_light: Sprite = sprite("Mai Break Note Light")
    break_note_dark: Sprite = sprite("Mai Break Note Dark")
    each_note: Sprite = sprite("Mai Each Note")
    normal_note_ex_outline: Sprite = sprite("Mai Normal Note Ex Outline")
    break_note_ex_outline: Sprite = sprite("Mai Break Note Ex Outline")
    each_note_ex_outline: Sprite = sprite("Mai Each Note Ex Outline")

    normal_star: Sprite = sprite("Mai Normal Star")
    break_star: Sprite = sprite("Mai Break Star")
    break_star_light: Sprite = sprite("Mai Break Star Light")
    break_star_dark: Sprite = sprite("Mai Break Star Dark")
    each_star: Sprite = sprite("Mai Each Star")
    normal_star_ex_outline: Sprite = sprite("Mai Normal Star Ex Outline")
    break_star_ex_outline: Sprite = sprite("Mai Break Star Ex Outline")
    each_star_ex_outline: Sprite = sprite("Mai Each Star Ex Outline")

    double_star: Sprite = sprite("Mai Double Star")
    break_double_star: Sprite = sprite("Mai Break Double Star")
    break_double_star_light: Sprite = sprite("Mai Break Double Star Light")
    break_double_star_dark: Sprite = sprite("Mai Break Double Star Dark")
    each_double_star: Sprite = sprite("Mai Each Double Star")
    double_star_ex_outline: Sprite = sprite("Mai Double Star Ex Outline")
    break_double_star_ex_outline: Sprite = sprite("Mai Break Double Star Ex Outline")
    each_double_star_ex_outline: Sprite = sprite("Mai Each Double Star Ex Outline")

    normal_touch_point: Sprite = sprite("Mai Normal Touch Point")
    break_touch_point: Sprite = sprite("Mai Break Touch Point")
    each_touch_point: Sprite = sprite("Mai Each Touch Point")

    normal_touch_fan: Sprite = sprite("Mai Normal Touch Fan")
    break_touch_fan: Sprite = sprite("Mai Break Touch Fan")
    break_touch_fan_light: Sprite = sprite("Mai Break Touch Fan Light")
    break_touch_fan_dark: Sprite = sprite("Mai Break Touch Fan Dark")
    each_touch_fan: Sprite = sprite("Mai Each Touch Fan")

    normal_touch_overlap_border: SpriteGroup = sprite_group(f"Mai Normal Touch {i} Overlap Border" for i in range(2, 4))
    break_touch_overlap_border: SpriteGroup = sprite_group(f"Mai Break Touch {i} Overlap Border" for i in range(2, 4))
    each_touch_overlap_border: SpriteGroup = sprite_group(f"Mai Each Touch {i} Overlap Border" for i in range(2, 4))

    touch_just_border: Sprite = sprite("Mai Touch Just Border")
    touch_feedback_ring: Sprite = sprite("Mai Touch Feedback Ring")
    touch_feedback_petal: Sprite = sprite("Mai Touch Feedback Petal")

    slide_path: Sprite = sprite("Mai Slide Path")
    break_slide_path: Sprite = sprite("Mai Break Slide Path")
    break_slide_path_light: Sprite = sprite("Mai Break Slide Path Light")
    break_slide_path_dark: Sprite = sprite("Mai Break Slide Path Dark")
    each_slide_path: Sprite = sprite("Mai Each Slide Path")

    wifi_slide_paths: SpriteGroup = sprite_group(f"Mai Wifi Slide Path {i}" for i in range(1, 12))
    break_wifi_slide_paths: SpriteGroup = sprite_group(f"Mai Break Wifi Slide Path {i}" for i in range(1, 12))
    each_wifi_slide_paths: SpriteGroup = sprite_group(f"Mai Each Wifi Slide Path {i}" for i in range(1, 12))

    # hold_note: Sprite = sprite("Mai Hold Note")
    hold_note_head: Sprite = sprite("Mai Hold Note Head")
    hold_note_body: Sprite = sprite("Mai Hold Note Body")
    hold_note_tail: Sprite = sprite("Mai Hold Note Tail")
    # hold_note_off: Sprite = sprite("Mai Hold Note Off")
    hold_note_head_off: Sprite = sprite("Mai Hold Note Head Off")
    hold_note_body_off: Sprite = sprite("Mai Hold Note Body Off")
    hold_note_tail_off: Sprite = sprite("Mai Hold Note Tail Off")
    # hold_note_on: Sprite = sprite("Mai Hold Note On")
    hold_note_head_on_light: Sprite = sprite("Mai Hold Note Head On Light")
    hold_note_head_on_dark: Sprite = sprite("Mai Hold Note Head On Dark")
    hold_note_body_on_light: Sprite = sprite("Mai Hold Note Body On Light")
    hold_note_body_on_dark: Sprite = sprite("Mai Hold Note Body On Dark")
    hold_note_tail_on_light: Sprite = sprite("Mai Hold Note Tail On Light")
    hold_note_tail_on_dark: Sprite = sprite("Mai Hold Note Tail On Dark")
    # break_hold_note: Sprite = sprite("Mai Break Hold Note")
    break_hold_note_head_light: Sprite = sprite("Mai Break Hold Note Head Light")
    break_hold_note_head_dark: Sprite = sprite("Mai Break Hold Note Head Dark")
    break_hold_note_body_light: Sprite = sprite("Mai Break Hold Note Body Light")
    break_hold_note_body_dark: Sprite = sprite("Mai Break Hold Note Body Dark")
    break_hold_note_tail_light: Sprite = sprite("Mai Break Hold Note Tail Light")
    break_hold_note_tail_dark: Sprite = sprite("Mai Break Hold Note Tail Dark")
    # break_hold_note_on: Sprite = sprite("Mai Break Hold Note On")
    break_hold_note_head_on_light: Sprite = sprite("Mai Break Hold Note Head On Light")
    break_hold_note_head_on_dark: Sprite = sprite("Mai Break Hold Note Head On Dark")
    break_hold_note_body_on_light: Sprite = sprite("Mai Break Hold Note Body On Light")
    break_hold_note_body_on_dark: Sprite = sprite("Mai Break Hold Note Body On Dark")
    break_hold_note_tail_on_light: Sprite = sprite("Mai Break Hold Note Tail On Light")
    break_hold_note_tail_on_dark: Sprite = sprite("Mai Break Hold Note Tail On Dark")
    # each_hold_note: Sprite = sprite("Mai Each Hold Note")
    each_hold_note_head: Sprite = sprite("Mai Each Hold Note Head")
    each_hold_note_body: Sprite = sprite("Mai Each Hold Note Body")
    each_hold_note_tail: Sprite = sprite("Mai Each Hold Note Tail")
    # each_hold_note_on: Sprite = sprite("Mai Each Hold Note On")
    each_hold_note_head_on_light: Sprite = sprite("Mai Each Hold Note Head On Light")
    each_hold_note_head_on_dark: Sprite = sprite("Mai Each Hold Note Head On Dark")
    each_hold_note_body_on_light: Sprite = sprite("Mai Each Hold Note Body On Light")
    each_hold_note_body_on_dark: Sprite = sprite("Mai Each Hold Note Body On Dark")
    each_hold_note_tail_on_light: Sprite = sprite("Mai Each Hold Note Tail On Light")
    each_hold_note_tail_on_dark: Sprite = sprite("Mai Each Hold Note Tail On Dark")

    hold_note_head_ex_outline: Sprite = sprite("Mai Hold Note Head Ex Outline")
    hold_note_body_ex_outline: Sprite = sprite("Mai Hold Note Body Ex Outline")
    hold_note_tail_ex_outline: Sprite = sprite("Mai Hold Note Tail Ex Outline")
    break_hold_note_head_ex_outline: Sprite = sprite("Mai Break Hold Note Head Ex Outline")
    break_hold_note_body_ex_outline: Sprite = sprite("Mai Break Hold Note Body Ex Outline")
    break_hold_note_tail_ex_outline: Sprite = sprite("Mai Break Hold Note Tail Ex Outline")
    each_hold_note_head_ex_outline: Sprite = sprite("Mai Each Hold Note Head Ex Outline")
    each_hold_note_body_ex_outline: Sprite = sprite("Mai Each Hold Note Body Ex Outline")
    each_hold_note_tail_ex_outline: Sprite = sprite("Mai Each Hold Note Tail Ex Outline")

    hold_note_end_point: Sprite = sprite("Mai Hold Note End Point")
    break_hold_note_end_point: Sprite = sprite("Mai Break Hold Note End Point")
    each_hold_note_end_point: Sprite = sprite("Mai Each Hold Note End Point")

    normal_touch_hold_fan: SpriteGroup = sprite_group(f"Mai Normal Touch Hold Fan {i}" for i in range(1, 5))
    touch_hold_border_on: Sprite = sprite("Mai Touch Hold Border On")
    touch_hold_border_off: Sprite = sprite("Mai Touch Hold Border Off")
    # Cross-sections of the four border sides (clockwise from the top-right one)
    # used to draw the partly filled border.
    touch_hold_border_on_bars: SpriteGroup = sprite_group(f"Mai Touch Hold Border On Bar {i}" for i in range(1, 5))
    touch_hold_border_off_bars: SpriteGroup = sprite_group(f"Mai Touch Hold Border Off Bar {i}" for i in range(1, 5))

    ring: Sprite = sprite("Mai Ring")
    sensor_outline: Sprite = sprite("Mai Sensor Outline")

    judge_critical_perfect: Sprite = sprite("Mai Judge Critical Perfect")
    judge_perfect: Sprite = sprite("Mai Judge Perfect")
    judge_great: Sprite = sprite("Mai Judge Great")
    judge_good: Sprite = sprite("Mai Judge Good")
    judge_miss: Sprite = sprite("Mai Judge Miss")
    judge_critical_perfect_shine: Sprite = sprite("Mai Judge Critical Perfect Shine")
    judge_perfect_shine: Sprite = sprite("Mai Judge Perfect Shine")
    judge_fast: Sprite = sprite("Mai Judge Fast")
    judge_late: Sprite = sprite("Mai Judge Late")
    judge_perfect_fast: Sprite = sprite("Mai Judge Perfect Fast")
    judge_perfect_late: Sprite = sprite("Mai Judge Perfect Late")
    judge_great_fast: Sprite = sprite("Mai Judge Great Fast")
    judge_great_late: Sprite = sprite("Mai Judge Great Late")
    judge_good_fast: Sprite = sprite("Mai Judge Good Fast")
    judge_good_late: Sprite = sprite("Mai Judge Good Late")

    firework_rays: SpriteGroup = sprite_group(f"Mai Firework Ray {i}" for i in range(1, 13))
    firework_ball: Sprite = sprite("Mai Firework Ball")
    firework_ball_pale: Sprite = sprite("Mai Firework Ball Pale")
    firework_sparkle: Sprite = sprite("Mai Firework Sparkle")

    # By SLIDE_OK_STATES, then SLIDE_OK_GRADES.
    slide_oks: SpriteGroup = sprite_group(
        f"Mai Slide OK {state} {grade}" for state in SLIDE_OK_STATES for grade in SLIDE_OK_GRADES
    )

    # By COUNTER_COLOURS, then COUNTER_GLYPHS.
    counter_glyphs: SpriteGroup = sprite_group(
        f"Mai Counter {colour} {glyph}" for colour in COUNTER_COLOURS for glyph in COUNTER_GLYPHS
    )
    # The life counter's backdrop, by COUNTER_COLOURS.
    counter_lives: SpriteGroup = sprite_group(f"Mai Counter {colour} Life" for colour in COUNTER_COLOURS)

class HoldActiveSpriteSet(Record):
    light: Sprite
    dark: Sprite

    def get_pulse(self) -> float:
        return abs(sin(time() * pi * 4))

    def draw(self, quad: Quad, z: ZIndex, a: float = 1):
        self.dark.draw(quad, z, a)
        z1, z2, z3, z4 = pad_z_indexes(z)
        self.light.draw(quad, (z1, z2, z3, z4 + 0.5), self.get_pulse() * a)


class BreakSpriteSet(Record):
    light: Sprite
    dark: Sprite

    def get_pulse(self) -> float:
        return max(sin(time() * pi * 4), 0)

    def draw(self, quad: Quad, z: ZIndex, a: float = 1):
        self.dark.draw(quad, z, a)
        z1, z2, z3, z4 = pad_z_indexes(z)
        self.light.draw(quad, (z1, z2, z3, z4 + 0.5), self.get_pulse() * a)


class BreakSpriteGroup(Record, ArrayLike[BreakSpriteSet]):
    """A pair of sprite groups (light / dark) of the same size, indexed like a SpriteGroup.

    Indexing returns the BreakSpriteSet of the two sprites at that index.
    """
    light: SpriteGroup
    dark: SpriteGroup

    def __len__(self) -> int:
        return len(self.light)

    def __getitem__(self, index: int) -> BreakSpriteSet:
        check_positive_index(index, len(self.light))
        return self.get_unchecked(index)

    def get_unchecked(self, index: Num) -> BreakSpriteSet:
        return BreakSpriteSet(
            light = self.light.get_unchecked(index),
            dark = self.dark.get_unchecked(index),
        )

    def __setitem__(self, index: int, value: BreakSpriteSet) -> None:
        static_error("BreakSpriteGroup is read-only")


class BodySpriteSet(Record):
    head: Sprite
    body: Sprite
    tail: Sprite


class ActiveBodySpriteSet(Record):
    head: HoldActiveSpriteSet
    body: HoldActiveSpriteSet
    tail: HoldActiveSpriteSet


class BreakBodySpriteSet(Record):
    """Head / body / tail pieces of a break body, each a light / dark pair."""
    head: BreakSpriteSet
    body: BreakSpriteSet
    tail: BreakSpriteSet


@level_data
class ActiveSkin:
    white_square: Sprite
    white_outline: Sprite

    normal_line: Sprite
    break_line: Sprite
    each_line: Sprite
    star_line: Sprite
    each_ring_line: SpriteGroup

    normal_note: Sprite
    break_note: BreakSpriteSet
    each_note: Sprite

    normal_note_ex_outline: Sprite
    break_note_ex_outline: Sprite
    each_note_ex_outline: Sprite

    normal_star: Sprite
    break_star: BreakSpriteSet
    each_star: Sprite

    double_star: Sprite
    break_double_star: BreakSpriteSet
    each_double_star: Sprite

    normal_star_ex_outline: Sprite
    break_star_ex_outline: Sprite
    each_star_ex_outline: Sprite

    double_star_ex_outline: Sprite
    break_double_star_ex_outline: Sprite
    each_double_star_ex_outline: Sprite

    normal_touch_point: Sprite
    break_touch_point: Sprite
    each_touch_point: Sprite

    normal_touch_fan: Sprite
    break_touch_fan: BreakSpriteSet
    each_touch_fan: Sprite

    normal_touch_overlap_border: SpriteGroup
    break_touch_overlap_border: SpriteGroup
    each_touch_overlap_border: SpriteGroup
    touch_just_border: Sprite
    touch_feedback_ring: Sprite
    touch_feedback_petal: Sprite

    slide_path: Sprite
    break_slide_path: BreakSpriteSet
    each_slide_path: Sprite

    wifi_slide_paths: SpriteGroup
    break_wifi_slide_paths: SpriteGroup
    each_wifi_slide_paths: SpriteGroup

    hold_note: BodySpriteSet
    hold_note_off: BodySpriteSet
    hold_note_on: ActiveBodySpriteSet
    break_hold_note: BreakBodySpriteSet
    break_hold_note_on: ActiveBodySpriteSet
    each_hold_note: BodySpriteSet
    each_hold_note_on: ActiveBodySpriteSet

    hold_note_ex_outline: BodySpriteSet
    break_hold_note_ex_outline: BodySpriteSet
    each_hold_note_ex_outline: BodySpriteSet

    hold_note_end_point: Sprite
    break_hold_note_end_point: Sprite
    each_hold_note_end_point: Sprite

    normal_touch_hold_fan: SpriteGroup
    touch_hold_border_on: Sprite
    touch_hold_border_off: Sprite
    touch_hold_border_on_bars: SpriteGroup
    touch_hold_border_off_bars: SpriteGroup

    ring: Sprite
    sensor_outline: Sprite

    judge_critical_perfect: Sprite
    judge_perfect: Sprite
    judge_great: Sprite
    judge_good: Sprite
    judge_miss: Sprite
    judge_critical_perfect_shine: Sprite
    judge_perfect_shine: Sprite
    judge_fast: Sprite
    judge_late: Sprite
    judge_perfect_fast: Sprite
    judge_perfect_late: Sprite
    judge_great_fast: Sprite
    judge_great_late: Sprite
    judge_good_fast: Sprite
    judge_good_late: Sprite

    firework_rays: SpriteGroup
    firework_ball: Sprite
    firework_ball_pale: Sprite
    firework_sparkle: Sprite

    slide_oks: SpriteGroup

    counter_glyphs: SpriteGroup
    counter_lives: SpriteGroup


def init_skin():
    ActiveSkin.white_square = BaseSkin.white_square
    ActiveSkin.white_outline = BaseSkin.white_outline

    ActiveSkin.normal_line = BaseSkin.normal_line
    ActiveSkin.break_line = BaseSkin.break_line
    ActiveSkin.each_line = BaseSkin.each_line
    ActiveSkin.star_line = BaseSkin.star_line
    ActiveSkin.each_ring_line = BaseSkin.each_ring_line

    ActiveSkin.normal_note = BaseSkin.normal_note
    ActiveSkin.break_note = BreakSpriteSet(
        light = BaseSkin.break_note_light,
        dark = BaseSkin.break_note_dark,
    )
    ActiveSkin.each_note = BaseSkin.each_note

    ActiveSkin.normal_star = BaseSkin.normal_star
    ActiveSkin.break_star = BreakSpriteSet(
        light = BaseSkin.break_star_light,
        dark = BaseSkin.break_star_dark,
    )
    ActiveSkin.each_star = BaseSkin.each_star
    ActiveSkin.double_star = BaseSkin.double_star
    ActiveSkin.break_double_star = BreakSpriteSet(
        light = BaseSkin.break_double_star_light,
        dark = BaseSkin.break_double_star_dark,
    )
    ActiveSkin.each_double_star = BaseSkin.each_double_star

    ActiveSkin.normal_note_ex_outline = BaseSkin.normal_note_ex_outline
    ActiveSkin.break_note_ex_outline = BaseSkin.break_note_ex_outline
    ActiveSkin.each_note_ex_outline = BaseSkin.each_note_ex_outline
    ActiveSkin.normal_star_ex_outline = BaseSkin.normal_star_ex_outline
    ActiveSkin.break_star_ex_outline = BaseSkin.break_star_ex_outline
    ActiveSkin.each_star_ex_outline = BaseSkin.each_star_ex_outline
    ActiveSkin.double_star_ex_outline = BaseSkin.double_star_ex_outline
    ActiveSkin.break_double_star_ex_outline = BaseSkin.break_double_star_ex_outline
    ActiveSkin.each_double_star_ex_outline = BaseSkin.each_double_star_ex_outline

    ActiveSkin.normal_touch_point = BaseSkin.normal_touch_point
    ActiveSkin.break_touch_point = BaseSkin.break_touch_point
    ActiveSkin.each_touch_point = BaseSkin.each_touch_point

    ActiveSkin.normal_touch_fan = BaseSkin.normal_touch_fan
    ActiveSkin.break_touch_fan = BreakSpriteSet(
        light = BaseSkin.break_touch_fan_light,
        dark = BaseSkin.break_touch_fan_dark,
    )
    ActiveSkin.each_touch_fan = BaseSkin.each_touch_fan

    ActiveSkin.normal_touch_overlap_border = BaseSkin.normal_touch_overlap_border
    ActiveSkin.break_touch_overlap_border = BaseSkin.break_touch_overlap_border
    ActiveSkin.each_touch_overlap_border = BaseSkin.each_touch_overlap_border
    ActiveSkin.touch_just_border = BaseSkin.touch_just_border
    ActiveSkin.touch_feedback_ring = BaseSkin.touch_feedback_ring
    ActiveSkin.touch_feedback_petal = BaseSkin.touch_feedback_petal

    ActiveSkin.slide_path = BaseSkin.slide_path
    ActiveSkin.break_slide_path = BreakSpriteSet(
        light = BaseSkin.break_slide_path_light,
        dark = BaseSkin.break_slide_path_dark,
    )
    ActiveSkin.each_slide_path = BaseSkin.each_slide_path

    ActiveSkin.wifi_slide_paths = BaseSkin.wifi_slide_paths
    ActiveSkin.break_wifi_slide_paths = BaseSkin.break_wifi_slide_paths
    ActiveSkin.each_wifi_slide_paths = BaseSkin.each_wifi_slide_paths

    ActiveSkin.hold_note = BodySpriteSet(
        head = BaseSkin.hold_note_head,
        body = BaseSkin.hold_note_body,
        tail = BaseSkin.hold_note_tail,
    )
    ActiveSkin.hold_note_off = BodySpriteSet(
        head = BaseSkin.hold_note_head_off,
        body = BaseSkin.hold_note_body_off,
        tail = BaseSkin.hold_note_tail_off,
    )
    ActiveSkin.hold_note_on = ActiveBodySpriteSet(
        head = HoldActiveSpriteSet(
            light = BaseSkin.hold_note_head_on_light,
            dark = BaseSkin.hold_note_head_on_dark,
        ),
        body = HoldActiveSpriteSet(
            light = BaseSkin.hold_note_body_on_light,
            dark = BaseSkin.hold_note_body_on_dark,
        ),
        tail = HoldActiveSpriteSet(
            light = BaseSkin.hold_note_tail_on_light,
            dark = BaseSkin.hold_note_tail_on_dark,
        ),
    )
    ActiveSkin.break_hold_note = BreakBodySpriteSet(
        head = BreakSpriteSet(
            light = BaseSkin.break_hold_note_head_light,
            dark = BaseSkin.break_hold_note_head_dark,
        ),
        body = BreakSpriteSet(
            light = BaseSkin.break_hold_note_body_light,
            dark = BaseSkin.break_hold_note_body_dark,
        ),
        tail = BreakSpriteSet(
            light = BaseSkin.break_hold_note_tail_light,
            dark = BaseSkin.break_hold_note_tail_dark,
        ),
    )
    ActiveSkin.break_hold_note_on = ActiveBodySpriteSet(
        head = HoldActiveSpriteSet(
            light = BaseSkin.break_hold_note_head_on_light,
            dark = BaseSkin.break_hold_note_head_on_dark,
        ),
        body = HoldActiveSpriteSet(
            light = BaseSkin.break_hold_note_body_on_light,
            dark = BaseSkin.break_hold_note_body_on_dark,
        ),
        tail = HoldActiveSpriteSet(
            light = BaseSkin.break_hold_note_tail_on_light,
            dark = BaseSkin.break_hold_note_tail_on_dark,
        ),
    )
    ActiveSkin.each_hold_note = BodySpriteSet(
        head = BaseSkin.each_hold_note_head,
        body = BaseSkin.each_hold_note_body,
        tail = BaseSkin.each_hold_note_tail,
    )
    ActiveSkin.each_hold_note_on = ActiveBodySpriteSet(
        head = HoldActiveSpriteSet(
            light = BaseSkin.each_hold_note_head_on_light,
            dark = BaseSkin.each_hold_note_head_on_dark,
        ),
        body = HoldActiveSpriteSet(
            light = BaseSkin.each_hold_note_body_on_light,
            dark = BaseSkin.each_hold_note_body_on_dark,
        ),
        tail = HoldActiveSpriteSet(
            light = BaseSkin.each_hold_note_tail_on_light,
            dark = BaseSkin.each_hold_note_tail_on_dark,
        ),
    )

    ActiveSkin.hold_note_ex_outline = BodySpriteSet(
        head = BaseSkin.hold_note_head_ex_outline,
        body = BaseSkin.hold_note_body_ex_outline,
        tail = BaseSkin.hold_note_tail_ex_outline,
    )
    ActiveSkin.break_hold_note_ex_outline = BodySpriteSet(
        head = BaseSkin.break_hold_note_head_ex_outline,
        body = BaseSkin.break_hold_note_body_ex_outline,
        tail = BaseSkin.break_hold_note_tail_ex_outline,
    )
    ActiveSkin.each_hold_note_ex_outline = BodySpriteSet(
        head = BaseSkin.each_hold_note_head_ex_outline,
        body = BaseSkin.each_hold_note_body_ex_outline,
        tail = BaseSkin.each_hold_note_tail_ex_outline,
    )

    ActiveSkin.hold_note_end_point = BaseSkin.hold_note_end_point
    ActiveSkin.break_hold_note_end_point = BaseSkin.break_hold_note_end_point
    ActiveSkin.each_hold_note_end_point = BaseSkin.each_hold_note_end_point

    ActiveSkin.normal_touch_hold_fan = BaseSkin.normal_touch_hold_fan
    ActiveSkin.touch_hold_border_on = BaseSkin.touch_hold_border_on
    ActiveSkin.touch_hold_border_off = BaseSkin.touch_hold_border_off
    ActiveSkin.touch_hold_border_on_bars = BaseSkin.touch_hold_border_on_bars
    ActiveSkin.touch_hold_border_off_bars = BaseSkin.touch_hold_border_off_bars

    ActiveSkin.ring = BaseSkin.ring
    ActiveSkin.sensor_outline = BaseSkin.sensor_outline

    ActiveSkin.judge_critical_perfect = BaseSkin.judge_critical_perfect
    ActiveSkin.judge_perfect = BaseSkin.judge_perfect
    ActiveSkin.judge_great = BaseSkin.judge_great
    ActiveSkin.judge_good = BaseSkin.judge_good
    ActiveSkin.judge_miss = BaseSkin.judge_miss
    ActiveSkin.judge_critical_perfect_shine = BaseSkin.judge_critical_perfect_shine
    ActiveSkin.judge_perfect_shine = BaseSkin.judge_perfect_shine
    ActiveSkin.judge_fast = BaseSkin.judge_fast
    ActiveSkin.judge_late = BaseSkin.judge_late
    ActiveSkin.judge_perfect_fast = BaseSkin.judge_perfect_fast
    ActiveSkin.judge_perfect_late = BaseSkin.judge_perfect_late
    ActiveSkin.judge_great_fast = BaseSkin.judge_great_fast
    ActiveSkin.judge_great_late = BaseSkin.judge_great_late
    ActiveSkin.judge_good_fast = BaseSkin.judge_good_fast
    ActiveSkin.judge_good_late = BaseSkin.judge_good_late

    ActiveSkin.firework_rays = BaseSkin.firework_rays
    ActiveSkin.firework_ball = BaseSkin.firework_ball
    ActiveSkin.firework_ball_pale = BaseSkin.firework_ball_pale
    ActiveSkin.firework_sparkle = BaseSkin.firework_sparkle

    ActiveSkin.slide_oks = BaseSkin.slide_oks

    ActiveSkin.counter_glyphs = BaseSkin.counter_glyphs
    ActiveSkin.counter_lives = BaseSkin.counter_lives
