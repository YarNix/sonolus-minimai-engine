from math import cos, pi

from sonolus.script.interval import clamp, lerp, unlerp_clamped
from sonolus.script.runtime import time
from sonolus.script.vec import Vec2

from minimai.lib.game import Button, Sensor
from minimai.lib.hitbox import Hitboxes
from minimai.lib.layer import LAYER_TUTORIAL_HAND, LAYER_TUTORIAL_HIGHLIGHT, get_z
from minimai.lib.layout import (
    TUTORIAL_HAND_LIFT,
    TutorialHandLayout,
    get_button_angle_horizontal,
    layout_ring_pos,
    layout_tutorial_button_hand,
    layout_tutorial_hand,
    layout_tutorial_sensor_hand,
    wrap_pi,
)
from minimai.lib.skin import ActiveSkin
from minimai.tutorial.instructions import InstructionIcons

HIGHLIGHT_FADE = 0.2
HIGHLIGHT_PULSE_RATE = 2.0
HIGHLIGHT_ALPHA = (0.15, 0.4)

# The hand shows this long before it presses and after it lifts, fading at both ends,
# and presses down / lifts over HAND_PRESS.
HAND_LEAD = 0.5
HAND_STAY = 0.4
HAND_FADE = 0.15
HAND_PRESS = 0.15
HAND_ALPHA = 0.9


def draw_sensor_highlight(sensor: Sensor, start_time: float, end_time: float):
    """The sensor's hitbox, pulsing, from ``start_time`` (fading in) until ``end_time``."""
    now = time()
    if not start_time <= now < end_time:
        return
    pulse = (1 - cos(2 * pi * HIGHLIGHT_PULSE_RATE * (now - start_time))) / 2
    alpha = lerp(*HIGHLIGHT_ALPHA, pulse) * unlerp_clamped(start_time, start_time + HIGHLIGHT_FADE, now)
    z = get_z(LAYER_TUTORIAL_HIGHLIGHT).tuple
    for quad in Hitboxes.of_sensor_as_quads(sensor):
        ActiveSkin.white_square.draw(quad, z, alpha)


def draw_button_highlight(button: Button, start_time: float, end_time: float):
    """The button's A sensor, as ``draw_sensor_highlight``."""
    draw_sensor_highlight(Sensor.A1 + button - 1, start_time, end_time)


def get_hand_alpha(press_time: float, release_time: float) -> float:
    """0 outside the hand's showing time."""
    now = time()
    start = press_time - HAND_LEAD
    end = release_time + HAND_STAY
    if not start <= now < end:
        return 0.0
    return HAND_ALPHA * min(unlerp_clamped(start, start + HAND_FADE, now), unlerp_clamped(end, end - HAND_FADE, now))


def get_hand_lift(press_time: float, release_time: float) -> float:
    """0 while pressed, 1 when away."""
    now = time()
    return clamp(max(press_time - now, now - release_time, 0) / HAND_PRESS, 0, 1)


def paint_hand(layout: TutorialHandLayout, alpha: float):
    InstructionIcons.hand.paint(layout.position, layout.size, layout.rotation, LAYER_TUTORIAL_HAND, alpha)


def paint_button_hand(button: Button, press_time: float, release_time: float):
    """The hand pressing ``button`` from ``press_time`` to ``release_time`` (the same for a tap)."""
    alpha = get_hand_alpha(press_time, release_time)
    if alpha > 0:
        paint_hand(layout_tutorial_button_hand(button, get_hand_lift(press_time, release_time)), alpha)


def paint_sensor_hand(sensor: Sensor, press_time: float, release_time: float):
    """As ``paint_button_hand``, on a sensor."""
    alpha = get_hand_alpha(press_time, release_time)
    if alpha > 0:
        paint_hand(layout_tutorial_sensor_hand(sensor, get_hand_lift(press_time, release_time)), alpha)


def paint_star_hand(
    button: Button, hit_time: float, slide_time: float, end_time: float, travel_angle: float, star: Vec2
):
    """The hand tapping the star on ``button``, turning to ``travel_angle`` while it waits,
    then following it (fingertip on ``star``) until it arrives."""
    alpha = get_hand_alpha(hit_time, end_time)
    if alpha <= 0:
        return
    now = time()
    button_angle = get_button_angle_horizontal(button)
    pointing = travel_angle
    tip = +star
    if now < slide_time:
        turn = unlerp_clamped(hit_time, slide_time, now)
        pointing = button_angle + wrap_pi(travel_angle - button_angle) * turn
        lift = get_hand_lift(hit_time, slide_time)
        tip @= layout_ring_pos(button_angle, 1 - TUTORIAL_HAND_LIFT * lift)
    paint_hand(layout_tutorial_hand(tip, pointing), alpha)
