from enum import IntEnum, auto
from typing import assert_never

from sonolus.script.bucket import Bucket, Judgment, JudgmentWindow, bucket, bucket_sprite, buckets, _BucketSprite
from sonolus.script.interval import Interval, lerp
from sonolus.script.record import Record
from sonolus.script.sprite import Sprite
from sonolus.script.text import StandardText

from minimai.lib.hold import HoldKind
from minimai.lib.layout import SLIDE_PATH_BASE_SIZE, TOUCH_DISTANCE_START, TOUCH_DISTANCE_END, TOUCH_DOT_BASE_SIZE, TOUCH_FAN_BASE_SIZE
from minimai.lib.note import NoteKind
from minimai.lib.skin import BaseSkin
from minimai.lib.slide import SlideKind
from minimai.lib.touch import TouchKind

WINDOW_SCALE = 1000  # Note and touch windows are in ms

# Slide windows depend on the slide, so slide buckets use a normalized error:
# ±1 is the perfect window edge, ±2 the great edge, ±3 the good edge.
SLIDE_BUCKET_WINDOW = JudgmentWindow(
    perfect=Interval(-1, 1),
    great=Interval(-2, 2),
    good=Interval(-3, 3),
)

NOTE_BUCKET_SIZE = 2
NOTE_BUCKET_STEP = 2

# Touch icon with the fans at their spawn distance, scaled to about the note icon size.
TOUCH_BUCKET_SCALE = 1 / (TOUCH_DISTANCE_START + TOUCH_FAN_BASE_SIZE.y / 2)
TOUCH_BUCKET_STEP = 2.4

SLIDE_BUCKET_BAR_COUNT = 5
SLIDE_BUCKET_BAR_H = 2
SLIDE_BUCKET_BAR_W = SLIDE_BUCKET_BAR_H * SLIDE_PATH_BASE_SIZE.x / SLIDE_PATH_BASE_SIZE.y
SLIDE_BUCKET_BAR_STEP = 1
SLIDE_BUCKET_GROUP_GAP = 1


def get_note_bucket_sprite(kind: NoteKind) -> Sprite:
    if kind in (NoteKind.NORM_TAP, NoteKind.EX_TAP):
        return BaseSkin.normal_note
    if kind in (NoteKind.EACH_TAP, NoteKind.EX_EACH_TAP):
        return BaseSkin.each_note
    if kind in (NoteKind.BREAK_TAP, NoteKind.EX_BREAK_TAP):
        return BaseSkin.break_note
    if kind in (NoteKind.NORM_STAR, NoteKind.EX_STAR):
        return BaseSkin.normal_star
    if kind in (NoteKind.EACH_STAR, NoteKind.EX_EACH_STAR):
        return BaseSkin.each_star
    if kind in (NoteKind.BREAK_STAR, NoteKind.EX_BREAK_STAR):
        return BaseSkin.break_star
    if kind in (NoteKind.DOUBLE_STAR, NoteKind.EX_DOUBLE_STAR):
        return BaseSkin.double_star
    if kind in (NoteKind.EACH_DOUBLE_STAR, NoteKind.EX_EACH_DOUBLE_STAR):
        return BaseSkin.each_double_star
    if kind in (NoteKind.BREAK_DOUBLE_STAR, NoteKind.EX_BREAK_DOUBLE_STAR):
        return BaseSkin.break_double_star
    raise ValueError(f"No bucket sprite for {kind!r}")


def get_note_bucket_outline(kind: NoteKind) -> Sprite | None:
    outlines = {
        NoteKind.EX_TAP: BaseSkin.normal_note_ex_outline,
        NoteKind.EX_EACH_TAP: BaseSkin.each_note_ex_outline,
        NoteKind.EX_BREAK_TAP: BaseSkin.break_note_ex_outline,
        NoteKind.EX_STAR: BaseSkin.normal_star_ex_outline,
        NoteKind.EX_EACH_STAR: BaseSkin.each_star_ex_outline,
        NoteKind.EX_BREAK_STAR: BaseSkin.break_star_ex_outline,
        NoteKind.EX_DOUBLE_STAR: BaseSkin.double_star_ex_outline,
        NoteKind.EX_EACH_DOUBLE_STAR: BaseSkin.each_double_star_ex_outline,
        NoteKind.EX_BREAK_DOUBLE_STAR: BaseSkin.break_double_star_ex_outline,
    }
    return outlines.get(kind)


def create_note_bucket_sprites(*kinds: NoteKind) -> list[_BucketSprite]:
    """One note per kind, left to right; EX kinds get their outline on top, as in game."""
    out_sprites: list[_BucketSprite] = []
    x_offset = (len(kinds) - 1) * NOTE_BUCKET_STEP / 2
    for i, kind in enumerate(kinds):
        x = NOTE_BUCKET_STEP * i - x_offset
        for sprite in (get_note_bucket_sprite(kind), get_note_bucket_outline(kind)):
            if sprite is not None:
                out_sprites.append(bucket_sprite(sprite=sprite, x=x, y=0, w=NOTE_BUCKET_SIZE, h=NOTE_BUCKET_SIZE))
    return out_sprites


def get_hold_bucket_sprites(kind: HoldKind) -> tuple[Sprite, Sprite, Sprite]:
    """(head, body, tail)"""
    match kind:
        case HoldKind.NORM_HOLD | HoldKind.EX_HOLD:
            return BaseSkin.hold_note_head, BaseSkin.hold_note_body, BaseSkin.hold_note_tail
        case HoldKind.EACH_HOLD | HoldKind.EX_EACH_HOLD:
            return BaseSkin.each_hold_note_head, BaseSkin.each_hold_note_body, BaseSkin.each_hold_note_tail
        case HoldKind.BREAK_HOLD | HoldKind.EX_BREAK_HOLD:
            return BaseSkin.break_hold_note_head_dark, BaseSkin.break_hold_note_body_dark, BaseSkin.break_hold_note_tail_dark
    raise ValueError(f"No bucket sprite for {kind!r}")


def get_hold_bucket_outlines(kind: HoldKind) -> tuple[Sprite, Sprite, Sprite] | None:
    """(head, body, tail) EX outline, or None for non-EX kinds."""
    match kind:
        case HoldKind.EX_HOLD:
            return BaseSkin.hold_note_head_ex_outline, BaseSkin.hold_note_body_ex_outline, BaseSkin.hold_note_tail_ex_outline
        case HoldKind.EX_EACH_HOLD:
            return BaseSkin.each_hold_note_head_ex_outline, BaseSkin.each_hold_note_body_ex_outline, BaseSkin.each_hold_note_tail_ex_outline
        case HoldKind.EX_BREAK_HOLD:
            return BaseSkin.break_hold_note_head_ex_outline, BaseSkin.break_hold_note_body_ex_outline, BaseSkin.break_hold_note_tail_ex_outline
    return None


def create_hold_bucket_sprites(*kinds: HoldKind) -> list[_BucketSprite]:
    """One short hold per kind, left to right; EX kinds get their outline on top, as in game."""
    out_sprites: list[_BucketSprite] = []
    x_offset = (len(kinds) - 1) * NOTE_BUCKET_STEP / 2
    w = NOTE_BUCKET_SIZE * 122 / 180
    cap = NOTE_BUCKET_SIZE * 60 / 180
    body = NOTE_BUCKET_SIZE * 60 / 180
    cap_y = (body + cap) / 2
    for i, kind in enumerate(kinds):
        x = NOTE_BUCKET_STEP * i - x_offset
        for pieces in (get_hold_bucket_sprites(kind), get_hold_bucket_outlines(kind)):
            if pieces is None:
                continue
            head, body_sprite, tail = pieces
            out_sprites.append(bucket_sprite(sprite=body_sprite, x=x, y=0, w=w, h=body))
            out_sprites.append(bucket_sprite(sprite=tail, x=x, y=-cap_y, w=w, h=cap))
            out_sprites.append(bucket_sprite(sprite=head, x=x, y=cap_y, w=w, h=cap))
    return out_sprites


def get_touch_bucket_sprites(kind: TouchKind) -> tuple[Sprite, Sprite]:
    """(point, fan)"""
    match kind:
        case TouchKind.NORM_TOUCH:
            return BaseSkin.normal_touch_point, BaseSkin.normal_touch_fan
        case TouchKind.EACH_TOUCH:
            return BaseSkin.each_touch_point, BaseSkin.each_touch_fan
        case TouchKind.BREAK_TOUCH:
            return BaseSkin.break_touch_point, BaseSkin.break_touch_fan
    raise ValueError(f"No bucket sprite for {kind!r}")


def create_touch_bucket_sprites(*kinds: TouchKind) -> list[_BucketSprite]:
    """One touch per kind, left to right: four fans pointing at the point, drawn in game order."""
    out_sprites: list[_BucketSprite] = []
    x_offset = (len(kinds) - 1) * TOUCH_BUCKET_STEP / 2
    dot_size = TOUCH_DOT_BASE_SIZE * TOUCH_BUCKET_SCALE
    fan_size = TOUCH_FAN_BASE_SIZE * TOUCH_BUCKET_SCALE
    fan_distance = lerp(TOUCH_DISTANCE_START, TOUCH_DISTANCE_END, 0.5) * TOUCH_BUCKET_SCALE
    for i, kind in enumerate(kinds):
        x = TOUCH_BUCKET_STEP * i - x_offset
        point, fan = get_touch_bucket_sprites(kind)
        # Left, right, top, bottom: (offset, rotation in degrees) of the bottom fan rotated about the point.
        for (dx, dy), rotation in (((-1, 0), -90), ((1, 0), 90), ((0, 1), 180), ((0, -1), 0)):
            out_sprites.append(bucket_sprite(
                sprite=fan,
                x=x + dx * fan_distance,
                y=dy * fan_distance,
                w=fan_size.x,
                h=fan_size.y,
                rotation=rotation,
            ))
        out_sprites.append(bucket_sprite(sprite=point, x=x, y=0, w=dot_size, h=dot_size))
    return out_sprites


def get_slide_bucket_sprite(kind: SlideKind) -> Sprite:
    match kind:
        case SlideKind.NORMAL_SLIDE | SlideKind.WIFI_SLIDE:
            return BaseSkin.slide_path
        case SlideKind.EACH_SLIDE | SlideKind.EACH_WIFI_SLIDE:
            return BaseSkin.each_slide_path
        case SlideKind.BREAK_SLIDE | SlideKind.BREAK_WIFI_SLIDE:
            return BaseSkin.break_slide_path
    raise ValueError(f"No bucket sprite for {kind!r}")


def create_slide_bucket_sprites(*kinds: SlideKind) -> list[_BucketSprite]:
    """Five slide bars pointing left per kind, groups left to right."""
    out_sprites: list[_BucketSprite] = []
    group_w = (SLIDE_BUCKET_BAR_COUNT - 1) * SLIDE_BUCKET_BAR_STEP + SLIDE_BUCKET_BAR_W
    group_step = group_w + SLIDE_BUCKET_GROUP_GAP
    x_offset = (len(kinds) - 1) * group_step / 2 + (SLIDE_BUCKET_BAR_COUNT - 1) * SLIDE_BUCKET_BAR_STEP / 2
    for i, kind in enumerate(kinds):
        sprite = get_slide_bucket_sprite(kind)
        # Rightmost first so the leading (left) bar is drawn on top, as in game.
        for j in reversed(range(SLIDE_BUCKET_BAR_COUNT)):
            out_sprites.append(bucket_sprite(
                sprite=sprite,
                x=group_step * i + SLIDE_BUCKET_BAR_STEP * j - x_offset,
                y=0,
                w=SLIDE_BUCKET_BAR_W,
                h=SLIDE_BUCKET_BAR_H,
            ))
    return out_sprites


@buckets
class Buckets:
    standard_tap: Bucket = bucket(
        sprites=create_note_bucket_sprites(NoteKind.NORM_TAP, NoteKind.EACH_TAP, NoteKind.NORM_STAR, NoteKind.EACH_STAR),
        unit=StandardText.MILLISECOND_UNIT,
    )
    ex_tap: Bucket = bucket(
        sprites=create_note_bucket_sprites(
            NoteKind.EX_TAP, NoteKind.EX_EACH_TAP, NoteKind.EX_BREAK_TAP,
            NoteKind.EX_STAR, NoteKind.EX_EACH_STAR, NoteKind.EX_BREAK_STAR,
        ),
        unit=StandardText.MILLISECOND_UNIT,
    )
    break_tap: Bucket = bucket(
        sprites=create_note_bucket_sprites(NoteKind.BREAK_TAP, NoteKind.BREAK_STAR),
        unit=StandardText.MILLISECOND_UNIT,
    )
    standard_hold: Bucket = bucket(
        sprites=create_hold_bucket_sprites(HoldKind.NORM_HOLD, HoldKind.EACH_HOLD),
        unit=StandardText.MILLISECOND_UNIT,
    )
    ex_hold: Bucket = bucket(
        sprites=create_hold_bucket_sprites(HoldKind.EX_HOLD, HoldKind.EX_EACH_HOLD, HoldKind.EX_BREAK_HOLD),
        unit=StandardText.MILLISECOND_UNIT,
    )
    break_hold: Bucket = bucket(
        sprites=create_hold_bucket_sprites(HoldKind.BREAK_HOLD),
        unit=StandardText.MILLISECOND_UNIT,
    )
    standard_touch: Bucket = bucket(
        sprites=create_touch_bucket_sprites(TouchKind.NORM_TOUCH, TouchKind.EACH_TOUCH),
        unit=StandardText.MILLISECOND_UNIT,
    )
    break_touch: Bucket = bucket(
        sprites=create_touch_bucket_sprites(TouchKind.BREAK_TOUCH),
        unit=StandardText.MILLISECOND_UNIT,
    )
    standard_slide: Bucket = bucket(
        sprites=create_slide_bucket_sprites(SlideKind.NORMAL_SLIDE, SlideKind.EACH_SLIDE),
    )
    break_slide: Bucket = bucket(
        sprites=create_slide_bucket_sprites(SlideKind.BREAK_SLIDE),
    )


def init_buckets():
    Buckets.standard_tap.window = NOTE_WINDOW.bucket_window
    Buckets.ex_tap.window = NOTE_WINDOW.bucket_window
    Buckets.break_tap.window = NOTE_WINDOW.bucket_window
    Buckets.standard_hold.window = NOTE_WINDOW.bucket_window
    Buckets.ex_hold.window = NOTE_WINDOW.bucket_window
    Buckets.break_hold.window = NOTE_WINDOW.bucket_window
    Buckets.standard_touch.window = TOUCH_WINDOW.bucket_window
    Buckets.break_touch.window = TOUCH_WINDOW.bucket_window
    Buckets.standard_slide.window = SLIDE_BUCKET_WINDOW
    Buckets.break_slide.window = SLIDE_BUCKET_WINDOW


def get_note_bucket(kind: NoteKind) -> Bucket:
    result = Bucket(-1)
    match kind:
        case NoteKind.NORM_TAP | NoteKind.EACH_TAP \
            | NoteKind.NORM_STAR | NoteKind.EACH_STAR \
            | NoteKind.DOUBLE_STAR | NoteKind.EACH_DOUBLE_STAR:
            result @= Buckets.standard_tap
        case NoteKind.BREAK_TAP | NoteKind.BREAK_STAR | NoteKind.BREAK_DOUBLE_STAR:
            result @= Buckets.break_tap
        case NoteKind.EX_TAP | NoteKind.EX_EACH_TAP | NoteKind.EX_BREAK_TAP \
            | NoteKind.EX_STAR | NoteKind.EX_EACH_STAR | NoteKind.EX_BREAK_STAR \
            | NoteKind.EX_DOUBLE_STAR | NoteKind.EX_EACH_DOUBLE_STAR | NoteKind.EX_BREAK_DOUBLE_STAR:
            result @= Buckets.ex_tap
        case _:
            assert_never(kind)
    return result


def get_hold_bucket(kind: HoldKind) -> Bucket:
    result = Bucket(-1)
    match kind:
        case HoldKind.NORM_HOLD | HoldKind.EACH_HOLD:
            result @= Buckets.standard_hold
        case HoldKind.BREAK_HOLD:
            result @= Buckets.break_hold
        case HoldKind.EX_HOLD | HoldKind.EX_EACH_HOLD | HoldKind.EX_BREAK_HOLD:
            result @= Buckets.ex_hold
        case _:
            assert_never(kind)
    return result


def get_touch_bucket(kind: TouchKind) -> Bucket:
    result = Bucket(-1)
    match kind:
        case TouchKind.NORM_TOUCH | TouchKind.EACH_TOUCH:
            result @= Buckets.standard_touch
        case TouchKind.BREAK_TOUCH:
            result @= Buckets.break_touch
        case _:
            assert_never(kind)
    return result


def get_slide_bucket(kind: SlideKind) -> Bucket:
    result = Bucket(-1)
    match kind:
        case SlideKind.NORMAL_SLIDE | SlideKind.EACH_SLIDE | SlideKind.WIFI_SLIDE | SlideKind.EACH_WIFI_SLIDE:
            result @= Buckets.standard_slide
        case SlideKind.BREAK_SLIDE | SlideKind.BREAK_WIFI_SLIDE:
            result @= Buckets.break_slide
        case _:
            assert_never(kind)
    return result


def round_interval(interval: Interval) -> Interval:
    return Interval(
        start=round(interval.start),
        end=round(interval.end),
    )

class ArcadeJudgment(IntEnum):
    NONE = 0
    CRITICAL_PERFECT = auto()
    HIGH_PERFECT = auto()
    LOW_PERFECT = auto()
    CRITICAL_GREAT = auto()
    HIGH_GREAT = auto()
    LOW_GREAT = auto()
    GOOD = auto()
    MISS = auto()

def arcade_judgement_to_normal(judgment: ArcadeJudgment):
    if judgment <= ArcadeJudgment.LOW_PERFECT:
        return Judgment.PERFECT
    elif judgment <= ArcadeJudgment.LOW_GREAT:
        return Judgment.GREAT
    elif judgment == ArcadeJudgment.GOOD:
        return Judgment.GOOD
    return Judgment.MISS

class ArcadeWindow(Record):
    critical_perfect: Interval
    high_perfect: Interval
    low_perfect: Interval
    critical_great: Interval
    high_great: Interval
    low_great: Interval
    good: Interval

    @property
    def bucket_window(self):
        return JudgmentWindow(
            perfect=round_interval(self.low_perfect * WINDOW_SCALE),
            great=round_interval(self.low_great * WINDOW_SCALE),
            good=round_interval(self.good * WINDOW_SCALE),
        )

    def normalize_error(self, error: float) -> float:
        """Piecewise linear: perfect edge -> ±1, great edge -> ±2, good edge -> ±3."""
        if error >= 0:
            return normalize_window_side(error, self.low_perfect.end, self.low_great.end, self.good.end)
        return -normalize_window_side(-error, -self.low_perfect.start, -self.low_great.start, -self.good.start)

    def judge(self, actual: float, target: float) -> ArcadeJudgment:
        diff = actual - target
        if diff in self.critical_perfect:
            return ArcadeJudgment.CRITICAL_PERFECT
        elif diff in self.high_perfect:
            return ArcadeJudgment.HIGH_PERFECT
        elif diff in self.low_perfect:
            return ArcadeJudgment.LOW_PERFECT
        elif diff in self.critical_great:
            return ArcadeJudgment.CRITICAL_GREAT
        elif diff in self.high_great:
            return ArcadeJudgment.HIGH_GREAT
        elif diff in self.low_great:
            return ArcadeJudgment.LOW_GREAT
        elif diff in self.good:
            return ArcadeJudgment.GOOD
        else:
            return ArcadeJudgment.MISS

def hold_end_judge(head: ArcadeJudgment, percent: float) -> ArcadeJudgment:
    """Final hold grade from the head grade and the share of the body that was held (0..1).

    | Body       | P1   | P2 / P3 | G1-G3 / Good | Miss |
    |------------|------|---------|--------------|------|
    | 100%       | P1   | kept    | G1           | Good |
    | [67, 100)  | P2   | kept    | G1           | Good |
    | [33, 67)   | G2   | G1      | G1           | Good |
    | [5, 33)    | Good | Good    | Good         | Good |
    | [0, 5)     | Good | Good    | Good         | Miss |
    """
    HOLD_BAND_FULL = 1.0
    HOLD_BAND_HIGH = 0.67
    HOLD_BAND_MID = 0.33
    HOLD_BAND_LOW = 0.05
    result = ArcadeJudgment.GOOD
    is_perfect = (
        head == ArcadeJudgment.CRITICAL_PERFECT
        or head == ArcadeJudgment.HIGH_PERFECT
        or head == ArcadeJudgment.LOW_PERFECT
    )
    if head == ArcadeJudgment.MISS:
        if percent < HOLD_BAND_LOW:
            result = ArcadeJudgment.MISS
    elif percent >= HOLD_BAND_FULL:
        result = head if is_perfect else ArcadeJudgment.CRITICAL_GREAT
    elif percent >= HOLD_BAND_HIGH:
        if head == ArcadeJudgment.CRITICAL_PERFECT:
            result = ArcadeJudgment.HIGH_PERFECT
        elif is_perfect:
            result = head
        else:
            result = ArcadeJudgment.CRITICAL_GREAT
    elif percent >= HOLD_BAND_MID:
        if head == ArcadeJudgment.CRITICAL_PERFECT:
            result = ArcadeJudgment.HIGH_GREAT
        else:
            result = ArcadeJudgment.CRITICAL_GREAT
    return result


def normalize_window_side(error: float, perfect: float, great: float, good: float) -> float:
    """``error`` and the edges are distances from the target; a narrower outer edge collapses its band."""
    great = max(great, perfect)
    good = max(good, great)
    result = 3.0
    if error <= perfect:
        result = error / perfect if perfect > 0 else 0.0
    elif error <= great:
        result = 1 + (error - perfect) / (great - perfect)
    elif error <= good:
        result = 2 + (error - great) / (good - great)
    return result


def note_interval(frames: int):
    return Interval(-frames / 60, frames / 60)

def touch_interval(frames: float):
    return Interval(-9 / 60, frames / 60)

def hold_interval(start: float, end: float):
    return Interval(start + 6 / 60, end - 12 / 60)

NOTE_WINDOW = ArcadeWindow(
    critical_perfect = note_interval(1),
    high_perfect = note_interval(2),
    low_perfect = note_interval(3),
    critical_great = note_interval(4),
    high_great = note_interval(5),
    low_great = note_interval(6),
    good = note_interval(9),
)

TOUCH_WINDOW = ArcadeWindow(
    critical_perfect = touch_interval(9),
    high_perfect = touch_interval(10.5),
    low_perfect = touch_interval(12),
    critical_great = touch_interval(13),
    high_great = touch_interval(14),
    low_great = touch_interval(15),
    good = touch_interval(18),
)