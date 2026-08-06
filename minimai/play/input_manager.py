from sonolus.script.archetype import PlayArchetype, callback
from sonolus.script.globals import level_memory
from sonolus.script.array import Array, Dim
from sonolus.script.iterator import maybe_next
from sonolus.script.containers import ArrayMap, ArraySet
from sonolus.script.runtime import Touch, time, touches
from sonolus.script.debug import debug_log, notify, assert_true

from minimai.lib import archetype_names
from minimai.lib.layout import Hitboxes, get_button_iterator, is_in_input_region
from minimai.lib.options import Options
from minimai.play.note import NoteMemory

INPUT_SLOTS = 16

@level_memory
class InputState:
    consumed_touches: ArrayMap[int, int, Dim[32]]
    # disallowed_release_touches: ArrayMap[int, float, Dim[32]]

def consume_touch(touch: Touch, button: int):
    assert_true(0 < button and button < 9, "Bad button argument!")
    InputState.consumed_touches[touch.id] = button
    
class InputManager(PlayArchetype):
    name = archetype_names.INPUT_MANAGER

    @callback(order=-1)
    def update_sequential(self):
        NoteMemory.active_tap_inputs.clear()

    @callback(order=-1)
    def touch(self):
        self.update_current_input()
        self.preassign_inputs()

    @staticmethod
    def update_current_input():
        # Handling old inputs
        old_touches = +InputState.consumed_touches
        InputState.consumed_touches.clear()
        for touch_id, consumed_button in old_touches.items():
            maybe_touch = maybe_next(touch for touch in touches() if touch.id == touch_id)
            if maybe_touch.is_nothing:
                continue
            touch = maybe_touch.get()
            if Hitboxes.button[consumed_button - 1].contains_point(touch.position):
                consume_touch(touch, consumed_button)

    @staticmethod
    def preassign_inputs():
        # Assigning the touchs
        active_taps = NoteMemory.active_tap_inputs
        active_taps.sort(key=lambda ref: ref.get().target_time)

        for touch in touches():
            # Check if touch is ready to be consumed
            if touch.id in InputState.consumed_touches:
                continue
            if not is_in_input_region(touch.position):
                continue

            touch_consumed = False
            for taps in active_taps:
                target_tap = taps.get()
                if target_tap.captured_touch_id != 0:
                    continue
                if not target_tap.hitbox.contains_point(touch.position):
                    continue
                if touch.time not in target_tap.unadjusted_input_interval:
                    continue
                consume_touch(touch, target_tap.button)
                target_tap.captured_touch_id = touch.id
                target_tap.touch_captured_time = touch.time
                touch_consumed = True
                break

            if not touch_consumed:
                for i, b in get_button_iterator():
                    if Hitboxes.button[i].contains_point(touch.position):
                        consume_touch(touch, b)

