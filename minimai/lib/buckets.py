from enum import Enum, auto
from typing import Iterable

from sonolus.script.bucket import Bucket, Judgment, JudgmentWindow, bucket, bucket_sprite, buckets, _BucketSprite
from sonolus.script.interval import Interval
from sonolus.script.record import Record
from sonolus.script.sprite import Sprite
from sonolus.script.text import StandardText
from sonolus.script.debug import static_assert

from minimai.lib.skin import BaseSkin

WINDOW_SCALE = 1000  # Windows are in ms

def create_bucket_sprites(*sprites: Iterable[Sprite], outlines: Iterable[Sprite | None] | None = None):
    out_sprites: list[_BucketSprite] = []
    static_assert(outlines is None or len(sprites) == len(outlines), "Can't have sprites size mismatch with outlines")

    sprite_len = len(sprites)
    x_offset = (sprite_len - 1) * 2 / 2
    for i, sprite in enumerate(sprites):
        if outlines is not None and outlines[i] is not None:
            out_sprites.append(bucket_sprite(
                sprite = outlines[i],
                x = 2 * i - x_offset,
                y = 0,
                w = 2,
                h = 2,
            ))

        out_sprites.append(bucket_sprite(
            sprite = sprite,
            x = 2 * i - x_offset,
            y = 0,
            w = 2,
            h = 2,
        ))

    return out_sprites

@buckets
class Buckets:
    standard_tap: Bucket = bucket(
        sprites=create_bucket_sprites(BaseSkin.normal_note, BaseSkin.each_note, BaseSkin.normal_star, BaseSkin.each_star),
        unit=StandardText.MILLISECOND_UNIT
    )
    ex_tap: Bucket = bucket(
        sprites=create_bucket_sprites(
            BaseSkin.normal_note, BaseSkin.each_note, BaseSkin.break_note,
            BaseSkin.normal_star, BaseSkin.each_star, BaseSkin.break_star,
            outlines=[
                BaseSkin.normal_note_ex_outline, BaseSkin.each_note_ex_outline, BaseSkin.break_note_ex_outline,
                BaseSkin.normal_star_ex_outline, BaseSkin.each_star_ex_outline, BaseSkin.break_star_ex_outline,
            ]
        ),
        unit=StandardText.MILLISECOND_UNIT
    )
    break_tap: Bucket = bucket(
        sprites=create_bucket_sprites(BaseSkin.break_note, BaseSkin.break_star),
        unit=StandardText.MILLISECOND_UNIT
    )

def init_buckets():
    Buckets.standard_tap.window = NOTE_WINDOW.bucket_window
    Buckets.ex_tap.window = NOTE_WINDOW.bucket_window
    Buckets.break_tap.window = NOTE_WINDOW.bucket_window

def round_interval(interval: Interval) -> Interval:
    return Interval(
        start=round(interval.start),
        end=round(interval.end),
    )

class ArcadeJudgment(Enum):
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

class SlideWindow(Record):
    perfect: Interval


def note_interval(frames: int):
    return Interval(-frames / 60, frames / 60)

def touch_interval(frames: int):
    return Interval(-9 / 60, frames / 60)

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
    critical_great = touch_interval(15),
    high_great = touch_interval(5),
    low_great = touch_interval(6),
    good = touch_interval(18),
)

# SLIDE_WINDOW = ArcadeWindow(
    
# )