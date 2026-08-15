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
    break_tap: Bucket =  bucket(
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

class ArcadeWindow(Record):
    critical_perfect: Interval
    perfect: Interval
    great: Interval
    good: Interval

    @property
    def bucket_window(self):
        return JudgmentWindow(
            perfect=round_interval(self.perfect * WINDOW_SCALE),
            great=round_interval(self.great * WINDOW_SCALE),
            good=round_interval(self.good * WINDOW_SCALE),
        )

    def judge(self, actual: float, target: float) -> Judgment:
        diff = actual - target
        if diff in self.perfect:
            return Judgment.PERFECT
        elif diff in self.great:
            return Judgment.GREAT
        elif diff in self.good:
            return Judgment.GOOD
        else:
            return Judgment.MISS

NOTE_WINDOW = ArcadeWindow(
    critical_perfect=Interval(-1 / 60, 1 / 60),
    perfect=Interval(-3 / 60, 3 / 60),
    great=Interval(-6 / 60, 6 / 60),
    good=Interval(-9 / 60, 9 / 60),
)

TOUCH_WINDOW = ArcadeWindow(
    critical_perfect=Interval(-9 / 60, 9 / 60),
    perfect=Interval(-9 / 60, 12 / 60),
    great=Interval(-9 / 60, 15 / 60),
    good=Interval(-9 / 60, 18 / 60),
)