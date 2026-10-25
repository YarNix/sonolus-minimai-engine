from __future__ import annotations
from math import floor
from typing import cast

from sonolus.script.archetype import PlayArchetype, callback
from sonolus.script.array import Array, Dim
from sonolus.script.vec import Vec2
from sonolus.script.quad import Quad
from sonolus.script.iterator import maybe_next
from sonolus.script.maybe import Nothing
from sonolus.script.containers import ArraySet, Pair, VarArray
from sonolus.script.runtime import Touch, time, touches
from sonolus.script.debug import debug_log, notify, assert_true

from minimai.lib import archetype_names
from minimai.lib.game import Button, Sensor
from minimai.lib.hitbox import Hitboxes
from minimai.lib.input_state import InputState
from minimai.lib.layout import get_sensor_pos_from_center
from minimai.lib.options import Options
from minimai.lib.skin import ActiveSkin
from minimai.lib.layer import get_z, LAYER_DEBUG_LOW
from minimai.play.note import NoteMemory
from minimai.play.slide import SlideMemory
from minimai.play.touch import TouchMemory

INPUT_SLOTS = 16

def button_started(touch: Touch, button: Button):
    InputState.button_started[button - 1] = (InputState.button_down[button - 1] == 0)
    InputState.button_down[button - 1] = touch

def button_ended(button: Button):
    InputState.button_down[button - 1] = 0

def sensor_started(touch: Touch, sensor: Sensor):
    InputState.sensor_touch_started[sensor - 1] = True
    InputState.processing_sensor_touch.set_add(Pair(touch, sensor))

def sensor_ended(sensor: Sensor):
    InputState.sensor_touch_ended[sensor - 1] = True

def button_test_touches(button: Button) -> int:
    """Test all touches, return the id of the first one hit"""
    for touch in touches():
        if touch.ended and not touch.started:
            continue
        if Hitboxes.of_button_contains_point(button, touch.position):
            return touch.id
    return 0

def touch_test_sensors(touch: Touch) -> ArraySet[Sensor, Dim[8]]:
    """Collect at-most 8 nearest sensors hit by this touch"""

    sensors = VarArray[Pair[Sensor, float], Dim[33]].new()
    for sensor in range(Sensor.A1, Sensor.E8 + 1):
        if Hitboxes.of_sensor_contains_point(sensor, touch.position):
            dist = (get_sensor_pos_from_center(sensor) - touch.position).magnitude
            sensors.append(Pair(sensor, dist))
    sensors.sort(key=lambda p: p.second)

    ret = VarArray[Sensor, Dim[8]].new()
    for sensor_hit in sensors:
        if ret.is_full():
            break
        ret.append(sensor_hit.first)
    return ArraySet(ret)
    
class InputManager(PlayArchetype):
    name = archetype_names.INPUT_MANAGER

    @callback(order=-1)
    def update_sequential(self):
        NoteMemory.active_tap_inputs.clear()
        TouchMemory.active_touch_inputs.clear()
        SlideMemory.active_slide_inputs.clear()
        self.update_current_input()

    @callback(order=-1)
    def touch(self):
        self.preassign_inputs()
        self.process_inputs()

    def update_parallel(self):
        if not Options.show_input:
            return
        
        for idx, is_down in enumerate(InputState.button_down):
            if not is_down:
                continue
            for quad in Hitboxes.of_button_as_quads(idx + 1):
                ActiveSkin.white_square.draw(quad, get_z(LAYER_DEBUG_LOW, 0, idx).tuple, 0.6)

        is_sensor_down = +Array[bool, Dim[33]]
        for sensors in InputState.sensor_touch_active.values():
            for sns in sensors:
                is_sensor_down[sns - 1] = True
        for idx, is_down in enumerate(is_sensor_down):
            if not is_down:
                continue
            for quad in Hitboxes.of_sensor_as_quads(idx + 1):
                ActiveSkin.white_square.draw(quad, get_z(LAYER_DEBUG_LOW, 0, 8 + idx).tuple, 0.4)

    @staticmethod
    def update_current_input():
        # Handling old inputs
        old_state = +InputState.sensor_touch_active
        cleared = +Array[bool, Dim[33]]
        InputState.button_started = +Array[bool, Dim[8]]
        InputState.sensor_touch_started @= cleared
        InputState.sensor_touch_down @= cleared
        InputState.sensor_touch_ended @= cleared
        InputState.sensor_touch_active.clear()
        InputState.processing_sensor_touch.clear()

        for idx, touch_id in enumerate(InputState.button_down):
            button = idx + 1
            if not touch_id:
                new_touch_id = button_test_touches(button)
                if new_touch_id:
                    button_started(new_touch_id, button)
                continue

            maybe_touch = maybe_next(touch for touch in touches() if touch.id == touch_id)
            if (maybe_touch.is_some
                and not maybe_touch.get().ended
                and Hitboxes.of_button_contains_point(button, maybe_touch.get().position)):
                continue

            # Try assigning a new touch for the button 
            new_touch_id = button_test_touches(button)
            if new_touch_id:
                button_started(new_touch_id, button)
            else:
                button_ended(button)

        for touch_id, old_sensors in old_state.items():
            maybe_touch = maybe_next(touch for touch in touches() if touch.id == touch_id)
            if maybe_touch.is_some:
                continue
            # Touch no longer existed, reports every sensor as released
            for sensor in old_sensors:
                sensor_ended(sensor)

        for touch in touches():
            current_sensors = touch_test_sensors(touch)
            if touch.id in old_state:
                previous_sensors = old_state[touch.id]

                for sensor in current_sensors:
                    if sensor not in previous_sensors:
                        sensor_started(touch.id, sensor)

                for sensor in previous_sensors:
                    if sensor not in current_sensors:
                        sensor_ended(sensor)
            else:
                for sensor in current_sensors:
                    sensor_started(touch.id, sensor)

            if touch.ended:
                for sensor in current_sensors:
                    sensor_ended(sensor)
                continue # Touch ended don't add it to the active touches

            InputState.sensor_touch_active[touch.id] = current_sensors

        for down_sensors in InputState.sensor_touch_active.values():
            for sensor in down_sensors:
                InputState.sensor_touch_down[sensor - 1] = True

    @staticmethod
    def preassign_inputs():
        # Assigning the touchs
        active_taps = NoteMemory.active_tap_inputs
        active_taps.sort(key=lambda ref: ref.get().target_time)
        active_touches = TouchMemory.active_touch_inputs
        active_touches.sort(key=lambda ref: ref.get().target_time)

        for tap_note in active_taps:
            target_tap = tap_note.get()
            if target_tap.captured_touch_id != 0:
                continue
            # Test button first
            if InputState.button_started[target_tap.button - 1]:
                touch_id = InputState.button_down[target_tap.button - 1]
                touch = next(touch for touch in touches() if touch.id == touch_id)
                if touch.time in target_tap.unadjusted_input_interval:
                    # Test success
                    InputState.button_started[target_tap.button - 1] = False
                    target_tap.captured_touch_id = touch_id
                    continue
            # Test touch next
            for idx, processing in enumerate(InputState.processing_sensor_touch):
                if processing.second != target_tap.sensor:
                    continue
                touch_id = processing.first
                touch = next(touch for touch in touches() if touch.id == touch_id)
                if touch.time in target_tap.unadjusted_input_interval:
                    # Test success
                    target_tap.captured_touch_id = touch_id
                    InputState.processing_sensor_touch.pop(idx)
                    break
            
        for touch_note in active_touches:
            target_touch = touch_note.get()
            if target_touch.captured_touch_id != 0:
                continue
            for idx, processing in enumerate(InputState.processing_sensor_touch):
                if processing.second != target_touch.sensor:
                    continue
                touch_id = processing.first
                touch = next(touch for touch in touches() if touch.id == touch_id)
                if touch.time in target_touch.unadjusted_input_interval:
                    # Test success
                    target_touch.captured_touch_id = touch_id
                    InputState.processing_sensor_touch.pop(idx)
                    break

    @staticmethod
    def process_inputs():

        ## Process slide input
        # Advance every registered slide's judge queue, parents before children.
        active_slides = SlideMemory.active_slide_inputs
        active_slides.sort(key=lambda slide_ref: slide_ref.get(check=False).chain_depth)
        for slide_ref in active_slides:
            slide = slide_ref.get(check=False)
            prev_index = slide.prev_slide_ref.index
            if not slide.is_checkable:
                if prev_index <= 0:
                    # Head is gated by time
                    slide.is_checkable = True
                else:
                    # While later parts gated until the parent has at most 1 area left.
                    slide.is_checkable = slide.parent_total_remaining <= 1

            if not slide.is_checkable:
                continue
            # Advancing the queue
            advanced = slide.check_judge_queues()

            if advanced and prev_index > 0:
                slide.parent_force_finish()