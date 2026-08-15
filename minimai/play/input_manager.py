from math import floor

from sonolus.script.archetype import PlayArchetype, callback
from sonolus.script.globals import level_memory
from sonolus.script.array import Array, Dim
from sonolus.script.vec import Vec2
from sonolus.script.quad import Quad
from sonolus.script.iterator import maybe_next
from sonolus.script.containers import ArrayMap, ArraySet
from sonolus.script.runtime import Touch, time, touches
from sonolus.script.debug import debug_log, notify, assert_true

from minimai.lib import archetype_names
from minimai.lib.layout import get_button_iterator, get_button_range, Button, Sensor
from minimai.lib.hitbox import Hitboxes, in_bounds
from minimai.lib.options import Options
from minimai.lib.skin import ActiveSkin
from minimai.lib.layer import get_z, LAYER_DEBUG_LOW
from minimai.play.note import NoteMemory
from minimai.play.touch import TouchMemory

INPUT_SLOTS = 16

@level_memory
class InputState:
    button_consumed: ArrayMap[int, Button, Dim[16]]
    sensor_tap_consumed: ArrayMap[int, Sensor, Dim[16]]
    sensor_touch_consumed: ArrayMap[int, Sensor, Dim[40]]
    # disallowed_release_touches: ArrayMap[int, float, Dim[32]]

def button_consume(touch: Touch, button: Button):
    InputState.button_consumed[touch.id] = button

def sensor_tap_consume(touch: Touch, sensor: Sensor):
    InputState.sensor_tap_consumed[touch.id] = sensor

def sensor_touch_consume(touch: Touch, sensor: Sensor):
    InputState.sensor_touch_consumed[touch.id] = sensor
    
class InputManager(PlayArchetype):
    name = archetype_names.INPUT_MANAGER

    @callback(order=-1)
    def update_sequential(self):
        NoteMemory.active_tap_inputs.clear()
        TouchMemory.active_touch_inputs.clear()
        self.update_current_input()

    @callback(order=-1)
    def touch(self):
        self.preassign_inputs()

    def update_parallel(self):
        if not Options.show_input:
            return
        is_button_down = +Array[bool, Dim[8]]
        for btn in InputState.button_consumed.values():
            is_button_down[btn - 1] = True
        for idx, is_down in enumerate(is_button_down):
            if not is_down:
                continue
            for quad in Hitboxes.of_button_as_quads(idx + 1):
                ActiveSkin.white_square.draw(quad, get_z(LAYER_DEBUG_LOW, 0, idx).tuple, 0.8)
        is_sensor_down = +Array[bool, Dim[33]]
        for sns in InputState.sensor_tap_consumed.values():
            is_sensor_down[sns - 1] = True
        for sns in InputState.sensor_touch_consumed.values():
            is_sensor_down[sns - 1] = True
        for idx, is_down in enumerate(is_sensor_down):
            if not is_down:
                continue
            for quad in Hitboxes.of_sensor_as_quads(idx + 1):
                ActiveSkin.white_square.draw(quad, get_z(LAYER_DEBUG_LOW, 0, 8 + idx).tuple, 0.4)

    @staticmethod
    def update_current_input():
        # Handling old inputs
        old_button_inputs = +InputState.button_consumed
        InputState.button_consumed.clear()
        old_sensor_tap_inputs = +InputState.sensor_tap_consumed
        InputState.sensor_tap_consumed.clear()
        old_sensor_touch_inputs = +InputState.sensor_touch_consumed
        InputState.sensor_touch_consumed.clear()

        if len(touches()) == 0:
            return # Early out, no touches mean nothing is consumed

        for touch_id, old_button in old_button_inputs.items():
            maybe_touch = maybe_next(touch for touch in touches() if touch.id == touch_id)
            if maybe_touch.is_nothing:
                continue
            touch = maybe_touch.get()
            if Hitboxes.of_button_contains_point(old_button, touch.position):
                button_consume(touch, old_button)

        for touch_id, old_sensor in old_sensor_tap_inputs.items():
            maybe_touch = maybe_next(touch for touch in touches() if touch.id == touch_id)
            if maybe_touch.is_nothing:
                continue
            touch = maybe_touch.get()
            if Hitboxes.of_sensor_contains_point(old_sensor, touch.position):
                sensor_tap_consume(touch, old_sensor)

        for touch_id, old_sensor in old_sensor_touch_inputs.items():
            maybe_touch = maybe_next(touch for touch in touches() if touch.id == touch_id)
            if maybe_touch.is_nothing:
                continue
            touch = maybe_touch.get()
            if Hitboxes.of_sensor_contains_point(old_sensor, touch.position):
                sensor_touch_consume(touch, old_sensor)

    @staticmethod
    def preassign_inputs():
        # Assigning the touchs
        active_taps = NoteMemory.active_tap_inputs
        active_taps.sort(key=lambda ref: ref.get().target_time)
        active_touches = TouchMemory.active_touch_inputs
        active_touches.sort(key=lambda ref: ref.get().target_time)

        for touch in touches():
            # Check if touch is ready to be consumed
            if not in_bounds(touch.position):
                continue

            tap_captured = False
            for tap_note in active_taps:
                target_tap = tap_note.get()
                if target_tap.captured_touch_id != 0:
                    continue
                if touch.time not in target_tap.unadjusted_input_interval:
                    continue
                if (touch.id not in InputState.button_consumed
                    and Hitboxes.of_button_contains_point(target_tap.button, touch.position)):
                    button_consume(touch, target_tap.button)
                elif (touch.id not in InputState.sensor_tap_consumed
                    and Hitboxes.of_sensor_contains_point(target_tap.sensor, touch.position)):
                    sensor_tap_consume(touch, target_tap.sensor)
                else:
                    continue
                target_tap.captured_touch_id = touch.id
                tap_captured = True

            if not tap_captured:
                for i, b in get_button_iterator():
                    if Hitboxes.button[i].contains_point(touch.position):
                        button_consume(touch, b)
                        tap_captured = True
            if not tap_captured:
                for i in range(len(Hitboxes.group_a)):
                    if Hitboxes.group_a[i].contains_point(touch.position):
                        sensor_tap_consume(touch, Sensor.A1 + i)

            touch_captured = False
            for touch_note in active_touches:
                target_touch = touch_note.get()
                if target_touch.captured_touch_id != 0:
                    continue
                if touch.time not in target_touch.unadjusted_input_interval:
                    continue
                if (touch.id not in InputState.sensor_touch_consumed
                    and Hitboxes.of_sensor_contains_point(target_touch.sensor, touch.position)):
                    sensor_touch_consume(touch, target_touch.sensor)
                else:
                    continue
                target_touch.captured_touch_id = touch.id
                touch_captured = True

            if not touch_captured:
                for i in range(len(Hitboxes.group_a)):
                    if Hitboxes.group_a[i].contains_point(touch.position):
                        sensor_touch_consume(touch, Sensor.A1 + i)
                for i in range(len(Hitboxes.group_a)):
                    if Hitboxes.group_b[i].contains_point(touch.position):
                        sensor_touch_consume(touch, Sensor.B1 + i)
                if Hitboxes.group_c.contains_point(touch.position):
                    sensor_touch_consume(touch, Sensor.C)
                for i in range(len(Hitboxes.group_a)):
                    if Hitboxes.group_d[i].contains_point(touch.position):
                        sensor_touch_consume(touch, Sensor.D1 + i)
                for i in range(len(Hitboxes.group_e)):
                    if Hitboxes.group_e[i].contains_point(touch.position):
                        sensor_touch_consume(touch, Sensor.E1 + i)


