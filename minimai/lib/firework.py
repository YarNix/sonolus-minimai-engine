from math import floor, pi, sin

from sonolus.script.archetype import get_archetype_by_name
from sonolus.script.interval import lerp, remap_clamped
from sonolus.script.runtime import time
from sonolus.script.vec import Vec2

from minimai.lib import archetype_names
from minimai.lib.game import ArcadeJudgment
from minimai.lib.layer import LAYER_FIREWORK, get_z
from minimai.lib.layout import (
    FIREWORK_BALL_SIZE,
    FIREWORK_INNER_SPARKLE_DISTANCE,
    FIREWORK_OUTER_SPARKLE_MAX_DISTANCE,
    FIREWORK_OUTER_SPARKLE_MIN_DISTANCE,
    FIREWORK_PALE_BALL_SIZE,
    layout_firework_ball,
    layout_firework_ray,
    layout_firework_sparkle,
)
from minimai.lib.options import Options
from minimai.lib.skin import ActiveSkin

FIREWORK_DURATION = 1.0
# Ray sprites in the skin, evenly spaced around the hue circle.
FIREWORK_HUES = 12
FIREWORK_RAYS = 24
# Hue sprites per second each ray moves through.
FIREWORK_HUE_SPEED = 3.0
# Degrees per second, clockwise, from when the rays come in.
FIREWORK_TURN_SPEED = 66.0
FIREWORK_TURN_START = 0.133
FIREWORK_RAY_IN = (0.117, 0.167)
FIREWORK_RAY_GROW = (0.117, 0.183)
FIREWORK_RAY_OUT = (0.82, 1.0)
# At the end the rays draw away from the center (the reference cuts them off at the screen's
# circle as they move out): their inner end goes out to this part of their length.
FIREWORK_RAY_RECEDE = (0.7, 1.0)
FIREWORK_RAY_RECEDE_LENGTH = 0.8
# The rays are a little see-through.
FIREWORK_RAY_ALPHA = 0.8
# The ray starts at this part of its length.
FIREWORK_RAY_START_LENGTH = 0.7
FIREWORK_BALL_IN = 0.03
FIREWORK_BALL_OUT = (0.1, 0.18)
FIREWORK_PALE_BALL_IN = (0.1, 0.18)
FIREWORK_PALE_BALL_OUT = (0.45, 0.6)
FIREWORK_PALE_BALL_ALPHA = 0.7
# Sparkles: count, when the first and last appear, and how long each lasts.
FIREWORK_INNER_SPARKLES = 10
FIREWORK_INNER_SPARKLE_START = (0.0, 0.05)
FIREWORK_OUTER_SPARKLES = 20
FIREWORK_OUTER_SPARKLE_START = (0.08, 0.3)
FIREWORK_SPARKLE_LIFE = 0.4
# A sparkle pops in over this part of its life and shrinks away over the last part.
FIREWORK_SPARKLE_POP = 0.2
FIREWORK_SPARKLE_SHRINK = 0.3
# Twinkles per second, and how much the size swings.
FIREWORK_TWINKLE_RATE = 10.0
FIREWORK_TWINKLE = 0.3

Z_RAY = 0
Z_BALL = 1
Z_PALE_BALL = 2
Z_SPARKLE = 3


def spawn_firework(firework: bool, judgment: ArcadeJudgment, center: Vec2):
    """For a hit note with the firework flag (play only)."""
    if not firework or not Options.note_effect:
        return
    if judgment == ArcadeJudgment.NONE or judgment == ArcadeJudgment.MISS:
        return
    get_archetype_by_name(archetype_names.FIREWORK).spawn(center=center, start_time=time())


def get_firework_end_time(start_time: float) -> float:
    return start_time + FIREWORK_DURATION / Options.effect_animation_speed


def noise(seed: float, i: int, k: int) -> float:
    """A fixed pseudo-random number in [0, 1) for part ``i``, value ``k`` of a firework, so the
    firework keeps its layout from frame to frame without storing it."""
    x = sin(seed * 12.9898 + i * 78.233 + k * 37.719) * 43758.5453
    return x - floor(x)


def draw_firework(center: Vec2, start_time: float, seed: float):
    age = (time() - start_time) * Options.effect_animation_speed
    draw_rays(center, start_time, seed, age)
    draw_balls(center, start_time, age)
    draw_sparkles(center, start_time, seed, age)


def draw_rays(center: Vec2, start_time: float, seed: float, age: float):
    alpha = (
        FIREWORK_RAY_ALPHA
        * remap_clamped(*FIREWORK_RAY_IN, 0, 1, age)
        * remap_clamped(*FIREWORK_RAY_OUT, 1, 0, age)
    )
    if alpha <= 0:
        return
    length = remap_clamped(*FIREWORK_RAY_GROW, FIREWORK_RAY_START_LENGTH, 1, age)
    start = remap_clamped(*FIREWORK_RAY_RECEDE, 0, FIREWORK_RAY_RECEDE_LENGTH, age)
    turn = -FIREWORK_TURN_SPEED * max(age - FIREWORK_TURN_START, 0) * pi / 180
    base = noise(seed, 0, 0) * 2 * pi + turn
    for i in range(FIREWORK_RAYS):
        layout = layout_firework_ray(center, base + i * 2 * pi / FIREWORK_RAYS, start, length)
        hue = noise(seed, i + 1, 1) * FIREWORK_HUES + FIREWORK_HUE_SPEED * age
        lower = floor(hue)
        blend = hue - lower
        first = lower % FIREWORK_HUES
        second = (lower + 1) % FIREWORK_HUES
        ActiveSkin.firework_rays[first].draw(
            layout, get_z(LAYER_FIREWORK, start_time, Z_RAY, 2 * i, invert_time=True).tuple, alpha
        )
        ActiveSkin.firework_rays[second].draw(
            layout, get_z(LAYER_FIREWORK, start_time, Z_RAY, 2 * i + 1, invert_time=True).tuple, alpha * blend
        )


def draw_balls(center: Vec2, start_time: float, age: float):
    alpha = remap_clamped(*FIREWORK_BALL_OUT, 1, 0, age)
    if alpha > 0:
        scale = remap_clamped(0, FIREWORK_BALL_IN, 0.85, 1, age)
        ActiveSkin.firework_ball.draw(
            layout_firework_ball(center, FIREWORK_BALL_SIZE, scale),
            get_z(LAYER_FIREWORK, start_time, Z_BALL, invert_time=True).tuple,
            alpha,
        )
    pale = remap_clamped(*FIREWORK_PALE_BALL_IN, 0, 1, age) * remap_clamped(*FIREWORK_PALE_BALL_OUT, 1, 0, age)
    if pale > 0:
        scale = remap_clamped(FIREWORK_PALE_BALL_IN[0], FIREWORK_PALE_BALL_OUT[1], 1, 1.1, age)
        ActiveSkin.firework_ball_pale.draw(
            layout_firework_ball(center, FIREWORK_PALE_BALL_SIZE, scale),
            get_z(LAYER_FIREWORK, start_time, Z_PALE_BALL, invert_time=True).tuple,
            pale * FIREWORK_PALE_BALL_ALPHA,
        )


def draw_sparkles(center: Vec2, start_time: float, seed: float, age: float):
    for i in range(FIREWORK_INNER_SPARKLES + FIREWORK_OUTER_SPARKLES):
        inner = i < FIREWORK_INNER_SPARKLES
        first = FIREWORK_OUTER_SPARKLE_START[0]
        last = FIREWORK_OUTER_SPARKLE_START[1]
        if inner:
            first = FIREWORK_INNER_SPARKLE_START[0]
            last = FIREWORK_INNER_SPARKLE_START[1]
        start = lerp(first, last, noise(seed, i, 2))
        life = (age - start) / FIREWORK_SPARKLE_LIFE
        if 0 < life < 1:
            # Inner sparkles spread evenly round the ball (with a little jitter); outer ones anywhere.
            distance = FIREWORK_INNER_SPARKLE_DISTANCE
            angle = (i + noise(seed, i, 3) * 0.6) * 2 * pi / FIREWORK_INNER_SPARKLES
            if not inner:
                distance = lerp(
                    FIREWORK_OUTER_SPARKLE_MIN_DISTANCE, FIREWORK_OUTER_SPARKLE_MAX_DISTANCE, noise(seed, i, 4)
                )
                angle = noise(seed, i, 3) * 2 * pi
            twinkle = 1 + FIREWORK_TWINKLE * sin(2 * pi * (FIREWORK_TWINKLE_RATE * age + noise(seed, i, 5)))
            size = min(life / FIREWORK_SPARKLE_POP, (1 - life) / FIREWORK_SPARKLE_SHRINK, 1)
            scale = size * twinkle * lerp(0.7, 1.2, noise(seed, i, 6))
            ActiveSkin.firework_sparkle.draw(
                layout_firework_sparkle(center, angle, distance, scale),
                get_z(LAYER_FIREWORK, start_time, Z_SPARKLE, i, invert_time=True).tuple,
            )
