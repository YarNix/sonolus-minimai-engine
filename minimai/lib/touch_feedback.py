from enum import IntEnum, auto
from math import e, pi
from random import random

from sonolus.script.array import Array, Dim
from sonolus.script.globals import level_memory
from sonolus.script.interval import remap_clamped
from sonolus.script.runtime import time

from minimai.lib.game import Button, Sensor, SensorGroup, sensor_to_group
from minimai.lib.input_state import InputState
from minimai.lib.hitbox import Hitboxes
from minimai.lib.layer import LAYER_DEBUG_LOW, LAYER_TOUCH_FEEDBACK, get_z
from minimai.lib.layout import (
    TOUCH_FEEDBACK_CENTER_RADIUS,
    TOUCH_FEEDBACK_RADIUS,
    layout_touch_feedback_center,
    layout_touch_feedback_petal,
    layout_touch_feedback_ring,
)
from minimai.lib.options import Options
from minimai.lib.skin import ActiveSkin

# A press within this long of a hit note there shows no feedback.
TOUCH_FEEDBACK_COOLDOWN = 0.4167
# Seconds, before Effect Animation Speed
TOUCH_FEEDBACK_DURATION = 0.36
# The main ring grows to its radius with this time constant while drifting on outward (radii per
# second), and fades with the other time constant until it's cut off.
RING_GROW = 0.018
RING_DRIFT = 0.8
RING_FADE_IN = 0.012
RING_FADE = 0.05
RING_CUT = (0.1, 0.15)
CENTER_GROW = 0.04
CENTER_FADE_IN = 0.025
CENTER_FADE_OUT = (0.03, 0.115)
PETALS = 10
# Petals ease out to their end distance and shrink away over their whole life.
PETAL_EASE = 2.2


class TouchFeedbackLevel(IntEnum):
    """Where presses show feedback (the Touch Feedback option)."""
    ALL = 0
    OUTER_ONLY = auto()
    """the buttons and A sensors"""
    INNER_ONLY = auto()
    """B, C and E"""
    OFF = auto()


SlotTimes = Array[float, Dim[33]]
SlotFlags = Array[bool, Dim[33]]


@level_memory
class TouchFeedbackMemory:
    # By sensor - 1; a button uses its A sensor's slot.
    start_time: SlotTimes
    started: SlotFlags
    last_hit_time: SlotTimes
    has_hit: SlotFlags
    # The petals' turn, different for every feedback.
    rotation: SlotTimes


def has_feedback(sensor: Sensor) -> bool:
    group = sensor_to_group(sensor)
    level = Options.touch_feedback
    result = False
    if group == SensorGroup.A:
        result = level == TouchFeedbackLevel.ALL or level == TouchFeedbackLevel.OUTER_ONLY
    elif group != SensorGroup.D:
        result = level == TouchFeedbackLevel.ALL or level == TouchFeedbackLevel.INNER_ONLY
    return result


def start_feedback(sensor: Sensor):
    slot = sensor - 1
    if not has_feedback(sensor):
        return
    last_feedback_time = time() - TouchFeedbackMemory.last_hit_time[slot]
    if TouchFeedbackMemory.has_hit[slot] and last_feedback_time < TOUCH_FEEDBACK_COOLDOWN:
        return
    TouchFeedbackMemory.start_time[slot] = time()
    TouchFeedbackMemory.started[slot] = True
    TouchFeedbackMemory.rotation[slot] = random() * 2 * pi / PETALS


def update_touch_feedback():
    """Starts feedback for this frame's presses that no note took."""
    for i in range(8):
        if InputState.button_started[i]:
            start_feedback(Sensor.A1 + i)
    for pressed in InputState.processing_sensor_touch:
        start_feedback(pressed.second)


def mark_touch_feedback_hit(sensor: Sensor):
    """A note took a press there: its feedback stops, and the next presses for a while show none."""
    TouchFeedbackMemory.last_hit_time[sensor - 1] = time()
    TouchFeedbackMemory.has_hit[sensor - 1] = True


def mark_button_feedback_hit(button: Button):
    mark_touch_feedback_hit(Sensor.A1 + button - 1)


def draw_touch_feedbacks():
    for slot in range(33):
        start = TouchFeedbackMemory.start_time[slot]
        if not TouchFeedbackMemory.started[slot]:
            pass
        elif TouchFeedbackMemory.has_hit[slot] and TouchFeedbackMemory.last_hit_time[slot] >= start:
            pass
        else:
            age = (time() - start) * Options.effect_animation_speed
            if age < TOUCH_FEEDBACK_DURATION:
                _touch_feedback_draw(slot, age)

def _touch_feedback_draw(slot: int, age: float):
    center = layout_touch_feedback_center(slot + 1)
    z = get_z(LAYER_TOUCH_FEEDBACK, 0, slot).tuple
    if age < RING_CUT[1]:
        radius = TOUCH_FEEDBACK_RADIUS * (1 - e ** (-age / RING_GROW) + RING_DRIFT * age)
        alpha = (
            remap_clamped(0, RING_FADE_IN, 0, 1, age)
            * e ** (-max(age - RING_FADE_IN, 0) / RING_FADE)
            * remap_clamped(*RING_CUT, 1, 0, age)
        )
        ActiveSkin.touch_feedback_ring.draw(layout_touch_feedback_ring(center, radius), z, alpha)
        radius = TOUCH_FEEDBACK_CENTER_RADIUS * (1 - e ** (-age / CENTER_GROW))
        alpha = remap_clamped(0, CENTER_FADE_IN, 0, 1, age) * remap_clamped(*CENTER_FADE_OUT, 1, 0, age)
        if alpha > 0:
            ActiveSkin.touch_feedback_ring.draw(layout_touch_feedback_ring(center, radius), z, alpha)
    life = age / TOUCH_FEEDBACK_DURATION
    progress = 1 - (1 - life) ** PETAL_EASE
    rotation = TouchFeedbackMemory.rotation[slot]
    for i in range(PETALS):
        angle = rotation + i * 2 * pi / PETALS
        ActiveSkin.touch_feedback_petal.draw(layout_touch_feedback_petal(center, angle, progress, 1 - life), z)

def draw_input_feedbacks():
    if not Options.show_input:
        return

    for idx, is_down in enumerate(InputState.button_down):
        if not is_down:
            continue
        for quad in Hitboxes.of_button_as_quads(idx + 1):
            ActiveSkin.white_square.draw(quad, get_z(LAYER_DEBUG_LOW, 0, idx).tuple, 0.6)

    for idx, is_down in enumerate(InputState.sensor_touch_down):
        if not is_down:
            continue
        for quad in Hitboxes.of_sensor_as_quads(idx + 1):
            ActiveSkin.white_square.draw(quad, get_z(LAYER_DEBUG_LOW, 0, 8 + idx).tuple, 0.4)