from __future__ import annotations

from sonolus.script.archetype import PlayArchetype, callback, entity_memory
from sonolus.script.array import Array, Dim
from sonolus.script.iterator import maybe_next
from sonolus.script.containers import ArraySet, Pair, VarArray
from sonolus.script.runtime import Touch, offset_adjusted_time, touches

from minimai.lib import archetype_names
from minimai.lib.game import Button, Sensor, apply_button_mirror_option, apply_sensor_mirror_option
from minimai.lib.hitbox import Hitboxes
from minimai.lib.input_state import InputState
from minimai.lib.layout import get_sensor_pos_from_center, layout_px_size, to_view
from minimai.lib.options import Options
from minimai.lib.streams import STREAM_START_TIME, InputSnapshot, Streams
from minimai.lib.touch_feedback import (
    draw_input_feedbacks,
    draw_touch_feedbacks,
    mark_button_feedback_hit,
    mark_touch_feedback_hit,
    update_touch_feedback,
)
from minimai.play.base_input import BaseInputMemory
from minimai.play.slide import SlideMemory

INPUT_SLOTS = 16
# Ring units per frame.
TOUCH_MIN_MOTION = 0.005

def button_started(touch: Touch, button: Button):
    InputState.button_started[button - 1] = (InputState.button_down[button - 1] == 0)
    InputState.button_down[button - 1] = touch

def button_ended(button: Button):
    InputState.button_down[button - 1] = 0

def sensor_started(touch: Touch, sensor: Sensor):
    InputState.sensor_touch_started[sensor - 1] = True
    InputState.processing_sensor_touch.set_add(Pair(touch, sensor))

def note_sensor_started(touch: Touch, sensor: Sensor):
    InputState.sensor_note_started[sensor - 1] = True
    InputState.processing_sensor_note.set_add(Pair(touch, sensor))

def sensor_ended(sensor: Sensor):
    InputState.sensor_touch_ended[sensor - 1] = True

def note_sensor_ended(sensor: Sensor):
    InputState.sensor_note_ended[sensor - 1] = True

def button_test_touches(button: Button) -> int:
    """Test all touches, return the id of the first one hit"""
    for touch in touches():
        if touch.ended and not touch.started:
            continue
        if Hitboxes.of_button_contains_point(button, to_view(touch.position)):
            return touch.id
    return 0

def touch_test_sensors(touch: Touch):
    """Sensors hit by this touch with the touch radius, and with the note radius"""
    def nearest_sensors(hits: VarArray[Pair[Sensor, float], Dim[33]]) -> ArraySet[Sensor, Dim[8]]:
        """The at-most 8 sensors hit nearest to their center"""
        hits.sort(key=lambda p: p.second)
        ret = VarArray[Sensor, Dim[8]].new()
        for hit in hits:
            if ret.is_full():
                break
            ret.append(hit.first)
        return ArraySet(ret)

    touch_hits = VarArray[Pair[Sensor, float], Dim[33]].new()
    note_hits = VarArray[Pair[Sensor, float], Dim[33]].new()
    position = to_view(touch.position)
    for sensor in range(Sensor.A1, Sensor.E8 + 1):
        result = Hitboxes.of_sensor_test_point(sensor, position)
        if not result.touch and not result.note:
            continue
        center_dist = (get_sensor_pos_from_center(sensor) - position).magnitude
        if result.touch:
            touch_hits.append(Pair(sensor, center_dist))
        if result.note:
            note_hits.append(Pair(sensor, center_dist))
    return nearest_sensors(touch_hits), nearest_sensors(note_hits)

class InputManager(PlayArchetype):
    name = archetype_names.INPUT_MANAGER

    recorded_input: InputSnapshot = entity_memory()

    def initialize(self):
        if Options.record_input:
            Streams.input[STREAM_START_TIME] = self.recorded_input

    @callback(order=-1)
    def update_sequential(self):
        BaseInputMemory.active_tap_inputs.clear()
        BaseInputMemory.active_touch_inputs.clear()
        SlideMemory.active_slide_inputs.clear()
        self.update_current_input()
        if Options.record_input:
            self.record_input()

    @callback(order=-1)
    def touch(self):
        self.preassign_inputs()
        update_touch_feedback()
        self.process_inputs()

    def update_parallel(self):
        draw_touch_feedbacks()
        draw_input_feedbacks()

    def record_input(self):
        snapshot = +InputSnapshot
        for i, touch_id in enumerate(InputState.button_down):
            if touch_id != 0:
                snapshot.add_button(apply_button_mirror_option(i + 1))
        for i in range(33):
            if InputState.sensor_touch_down[i]:
                snapshot.touch.add(apply_sensor_mirror_option(i + 1))
            if InputState.sensor_note_down[i]:
                snapshot.note.add(apply_sensor_mirror_option(i + 1))
        if snapshot != self.recorded_input:
            Streams.input[offset_adjusted_time()] = snapshot
            self.recorded_input @= snapshot

    @staticmethod
    def update_current_input():
        # Handling old inputs
        old_state = +InputState.sensor_touch_active
        old_note_state = +InputState.sensor_note_active
        cleared = +Array[bool, Dim[33]]
        InputState.button_started = +Array[bool, Dim[8]]
        InputState.sensor_touch_started @= cleared
        InputState.sensor_touch_down @= cleared
        InputState.sensor_touch_ended @= cleared
        InputState.sensor_touch_active.clear()
        InputState.sensor_note_started @= cleared
        InputState.sensor_note_down @= cleared
        InputState.sensor_note_ended @= cleared
        InputState.sensor_note_active.clear()
        InputState.processing_sensor_touch.clear()
        InputState.processing_sensor_note.clear()

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
                and Hitboxes.of_button_contains_point(button, to_view(maybe_touch.get().position))):
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

        for touch_id, old_sensors in old_note_state.items():
            maybe_touch = maybe_next(touch for touch in touches() if touch.id == touch_id)
            if maybe_touch.is_some:
                continue
            for sensor in old_sensors:
                note_sensor_ended(sensor)

        for touch in touches():
            touch_sensors, note_sensors = touch_test_sensors(touch)
            if touch.id in old_state:
                previous_sensors = old_state[touch.id]

                for sensor in touch_sensors:
                    if sensor not in previous_sensors:
                        sensor_started(touch.id, sensor)

                for sensor in previous_sensors:
                    if sensor not in touch_sensors:
                        sensor_ended(sensor)
            else:
                for sensor in touch_sensors:
                    sensor_started(touch.id, sensor)

            if touch.id in old_note_state:
                previous_sensors = old_note_state[touch.id]

                for sensor in note_sensors:
                    if sensor not in previous_sensors:
                        note_sensor_started(touch.id, sensor)

                for sensor in previous_sensors:
                    if sensor not in note_sensors:
                        note_sensor_ended(sensor)
            else:
                for sensor in note_sensors:
                    note_sensor_started(touch.id, sensor)

            if touch.ended:
                for sensor in touch_sensors:
                    sensor_ended(sensor)
                for sensor in note_sensors:
                    note_sensor_ended(sensor)
                continue # Touch ended don't add it to the active touches

            InputState.sensor_touch_active[touch.id] = touch_sensors
            InputState.sensor_note_active[touch.id] = note_sensors

        for down_sensors in InputState.sensor_touch_active.values():
            for sensor in down_sensors:
                InputState.sensor_touch_down[sensor - 1] = True
        for down_sensors in InputState.sensor_note_active.values():
            for sensor in down_sensors:
                InputState.sensor_note_down[sensor - 1] = True

    @staticmethod
    def preassign_inputs():
        # Assigning the touchs
        active_taps = BaseInputMemory.active_tap_inputs
        active_taps.sort(key=lambda ref: ref.get().target_time)
        active_touches = BaseInputMemory.active_touch_inputs
        active_touches.sort(key=lambda ref: ref.get().target_time)

        # The touch that took a tap through each button this frame.
        button_tap_touch = +Array[int, Dim[8]]
        # The touch that took a tap through each sensor this frame.
        sensor_tap_touch = +Array[int, Dim[33]]
        for tap_note in active_taps:
            target_tap = tap_note.get()
            if target_tap.captured_touch_id != 0:
                continue
            button = target_tap.button
            # Test button first
            if InputState.button_started[button - 1]:
                touch_id = InputState.button_down[button - 1]
                touch = next(touch for touch in touches() if touch.id == touch_id)
                if touch.time in target_tap.unadjusted_input_interval:
                    # Test success
                    InputState.button_started[button - 1] = False
                    target_tap.captured_touch_id = touch_id
                    button_tap_touch[button - 1] = touch_id
                    mark_button_feedback_hit(button)
                    continue
            # Test touch next
            for idx, processing in enumerate(InputState.processing_sensor_note):
                if processing.second != target_tap.sensor:
                    continue
                touch_id = processing.first
                # For taps, a touch on both the button and its A sensor is one touch.
                if touch_id == button_tap_touch[button - 1]:
                    continue
                touch = next(touch for touch in touches() if touch.id == touch_id)
                if touch.time in target_tap.unadjusted_input_interval:
                    # Test success
                    target_tap.captured_touch_id = touch_id
                    sensor_tap_touch[target_tap.sensor - 1] = touch_id
                    if InputState.button_down[button - 1] == touch_id:
                        InputState.button_started[button - 1] = False
                    mark_touch_feedback_hit(processing.second)
                    InputState.processing_sensor_note.pop(idx)
                    break

        # Sensors that took a note by a moving touch this frame.
        moved_sensors = +Array[bool, Dim[33]]
        min_motion = layout_px_size(TOUCH_MIN_MOTION)
        for touch_note in active_touches:
            target_touch = touch_note.get()
            if target_touch.captured_touch_id != 0:
                continue
            for idx, processing in enumerate(InputState.processing_sensor_touch):
                if processing.second != target_touch.sensor:
                    continue
                touch_id = processing.first
                # A press that took a tap on this sensor can't also take a touch note there.
                if touch_id == sensor_tap_touch[target_touch.sensor - 1]:
                    continue
                touch = next(touch for touch in touches() if touch.id == touch_id)
                if touch.time in target_touch.unadjusted_input_interval:
                    # Test success
                    target_touch.captured_touch_id = touch_id
                    mark_touch_feedback_hit(processing.second)
                    InputState.processing_sensor_touch.pop(idx)
                    break
            if target_touch.captured_touch_id != 0 or moved_sensors[target_touch.sensor - 1]:
                continue
            # Test touches moving inside the sensor next
            for touch in touches():
                if touch.delta.magnitude < min_motion:
                    continue
                if touch.id == sensor_tap_touch[target_touch.sensor - 1]:
                    continue
                if touch.time not in target_touch.unadjusted_input_interval:
                    continue
                if not Hitboxes.of_sensor_test_point(target_touch.sensor, to_view(touch.position)).inside:
                    continue
                target_touch.captured_touch_id = touch.id
                moved_sensors[target_touch.sensor - 1] = True
                mark_touch_feedback_hit(target_touch.sensor)
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