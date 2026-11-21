from collections.abc import Iterable
from enum import IntEnum, auto
from math import pi
from typing import Any, Protocol, TypeAlias, assert_never, cast

from sonolus.script.archetype import EntityRef, get_archetype_by_name
from sonolus.script.array import Array, Dim
from sonolus.script.containers import VarArray
from sonolus.script.debug import assert_true
from sonolus.script.record import Record
from sonolus.script.vec import Vec2
from sonolus.script.quad import Quad
from sonolus.script.runtime import time
from sonolus.script.interval import clamp, lerp, remap, unlerp, unlerp_clamped
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names
from minimai.lib.layer import ZIndexes, get_z, LAYER_SLIDE_NOTE, LAYER_SLIDE_PATH
from minimai.lib.layout import (
    SLIDE_TRACK_POINTS,
    Layout,
    build_slide_star_points,
    from_skin_px,
    layout_slide_head,
    layout_slide_path,
    layout_wifi_slide_path,
)
from minimai.lib.options import Options
from minimai.lib.skin import ActiveSkin
from minimai.lib.note import NoteKind, _note_draw
from minimai.lib.input_state import InputState
from minimai.lib.game import (
    Button,
    Sensor,
    button_mirror,
    button_shift,
    sensor_mirror,
    sensor_shift,
)
from minimai.lib.scoring import MAX_BREAK_WEIGHT, WeightedArchetype, init_life_loss


class SlideKind(IntEnum):
    NORMAL_SLIDE = auto()
    EACH_SLIDE = auto()
    BREAK_SLIDE = auto()

    WIFI_SLIDE = auto()
    EACH_WIFI_SLIDE = auto()
    BREAK_WIFI_SLIDE = auto()

def is_wifi_slide(kind: SlideKind):
    return kind in (SlideKind.WIFI_SLIDE, SlideKind.EACH_WIFI_SLIDE, SlideKind.BREAK_WIFI_SLIDE)

def is_break_slide(kind: SlideKind):
    return kind in (SlideKind.BREAK_SLIDE, SlideKind.BREAK_WIFI_SLIDE)

class SlideTrackKind(IntEnum):
    NONE = 0
    # Edge (> < ^)
    CIRCLE_1 = auto()
    CIRCLE_2 = auto()
    CIRCLE_3 = auto()
    CIRCLE_4 = auto()
    CIRCLE_5 = auto()
    CIRCLE_6 = auto()
    CIRCLE_7 = auto()
    CIRCLE_8 = auto()
    # Straight (-)
    LINE_3 = auto()
    LINE_4 = auto()
    LINE_5 = auto()
    # Center (v)
    CENTER_1 = auto()
    CENTER_2 = auto()
    CENTER_3 = auto()
    CENTER_4 = auto()
    # Inner loop (p q)
    LOOP_IN_1 = auto()
    LOOP_IN_2 = auto()
    LOOP_IN_3 = auto()
    LOOP_IN_4 = auto()
    LOOP_IN_5 = auto()
    LOOP_IN_6 = auto()
    LOOP_IN_7 = auto()
    LOOP_IN_8 = auto()
    # Outer loop (pp qq)
    LOOP_OUT_1 = auto()
    LOOP_OUT_2 = auto()
    LOOP_OUT_3 = auto()
    LOOP_OUT_4 = auto()
    LOOP_OUT_5 = auto()
    LOOP_OUT_6 = auto()
    LOOP_OUT_7 = auto()
    LOOP_OUT_8 = auto()
    # Reflect (V L)
    REFLECT_2 = auto()
    REFLECT_3 = auto()
    REFLECT_4 = auto()
    REFLECT_5 = auto()
    # Zigzag (s z)
    ZIG_ZAG = auto()
    # Wifi (w)
    FAN = auto()
    # [Internal use only]
    FAN_L = auto()
    FAN_C = auto()
    FAN_R = auto()

# Wi-Fi branches
class SlideBranch(IntEnum):
    BRANCH_C = 0
    BRANCH_L = 1
    BRANCH_R = 2

SLIDE_PATH_ALL_HIDDEN = 1000
class SlideArea(Record):
    sensors: VarArray[Sensor, Dim[2]]
    path_on_active: int
    path_on_finish: int
    can_skip: bool

class SlideChainInfo(Record):
    """How a slide sits in a connection chain; drives area ``is_last``/``can_skip`` overrides."""
    is_part: bool       # has a previous or a next slide
    is_head: bool       # has no previous slide
    is_final: bool      # has no next slide (scored)
    total_areas: int    # judge areas of the whole chain (shared areas counted once)

SlideAreaInfo: TypeAlias = (
    tuple[Sensor | tuple[Sensor, Sensor], int, int]
    | tuple[Sensor | tuple[Sensor, Sensor], int, int, bool]
)

def build_slide_areas(*area_infos: SlideAreaInfo) -> VarArray[SlideArea, Dim[12]]:
    """Build canonical judgment-area templates.

    The integer boundaries are kept verbatim: they index the corresponding
    prefab's track points and are later used for segment-by-segment hiding.
    """
    areas = VarArray[SlideArea, Dim[12]].new()
    for info in area_infos:
        match info:
            case sensor_areas, point_on_start, point_on_end:
                can_skip = True
            case sensor_areas, point_on_start, point_on_end, can_skip:
                pass
            case _:
                raise TypeError(f"Invalid slide area definition: {info}")

        sensors = VarArray[Sensor, Dim[2]].new()
        if type(sensor_areas) is Sensor or isinstance(sensor_areas, int):
            sensors.append(sensor_areas)
        else:
            sensors.extend(Array(*sensor_areas))

        areas.append(
            SlideArea(
                sensors=sensors,
                path_on_active=point_on_start,
                path_on_finish=point_on_end,
                can_skip=can_skip,
            )
        )
    return areas

# The array index base on SlideTrackKind
SLIDE_AREAS = Array(
    build_slide_areas((Sensor.N0, 0, 1)),
    # Circle (> - mirror <)
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.A2, 7, 11), (Sensor.A3, 14, 19), (Sensor.A4, 23, 27), (Sensor.A5, 31, 35), (Sensor.A6, 39, 43), (Sensor.A7, 46, 51), (Sensor.A8, 54, 59), (Sensor.A1, 61, 63)),
    build_slide_areas((Sensor.A1, 0, 3, False), (Sensor.A2, 5, 7)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.A2, 7, 11, False), (Sensor.A3, 13, 15)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.A2, 7, 11), (Sensor.A3, 14, 19), (Sensor.A4, 21, 23)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.A2, 7, 11), (Sensor.A3, 14, 19), (Sensor.A4, 23, 27), (Sensor.A5, 29, 31)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.A2, 7, 11), (Sensor.A3, 14, 19), (Sensor.A4, 23, 27), (Sensor.A5, 31, 35), (Sensor.A6, 37, 39)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.A2, 7, 11), (Sensor.A3, 14, 19), (Sensor.A4, 23, 27), (Sensor.A5, 31, 35), (Sensor.A6, 39, 43), (Sensor.A7, 45, 47)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.A2, 7, 11), (Sensor.A3, 14, 19), (Sensor.A4, 23, 27), (Sensor.A5, 31, 35), (Sensor.A6, 39, 43), (Sensor.A7, 46, 51), (Sensor.A8, 53, 55)),
    # Straight (-)
    build_slide_areas((Sensor.A1, 0, 3), ((Sensor.A2, Sensor.B2), 6, 9, False), (Sensor.A3, 10, 13)),
    build_slide_areas((Sensor.A1, 0, 4), (Sensor.B2, 6, 9), (Sensor.B3, 11, 14), (Sensor.A4, 15, 18)),
    build_slide_areas((Sensor.A1, 0, 4), (Sensor.B1, 5, 7), (Sensor.C, 10, 12), (Sensor.B5, 13, 16), (Sensor.A5, 17, 19)),
    # Center (v)
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.B1, 4, 7), (Sensor.C, 8, 13), (Sensor.B1, 14, 16), (Sensor.A1, 17, 19)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.B1, 4, 7), (Sensor.C, 8, 13), (Sensor.B2, 14, 16), (Sensor.A2, 17, 19)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.B1, 4, 7), (Sensor.C, 8, 13), (Sensor.B3, 14, 16), (Sensor.A3, 17, 19)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.B1, 4, 7), (Sensor.C, 8, 13), (Sensor.B4, 14, 16), (Sensor.A4, 17, 19)),
    # Inner loop (p - mirror q)
    build_slide_areas((Sensor.A1, 0, 4), (Sensor.B8, 5, 8), (Sensor.B7, 9, 11), (Sensor.B6, 12, 14), (Sensor.B5, 15, 17), (Sensor.B4, 19, 21), (Sensor.B3, 22, 24), (Sensor.B2, 25, 29), (Sensor.A1, 30, 33)),
    build_slide_areas((Sensor.A1, 0, 4), (Sensor.B8, 5, 8), (Sensor.B7, 9, 11), (Sensor.B6, 12, 14), (Sensor.B5, 16, 18), (Sensor.B4, 19, 21), (Sensor.B3, 22, 26), (Sensor.A2, 27, 30)),
    build_slide_areas((Sensor.A1, 0, 4), (Sensor.B8, 5, 8), (Sensor.B7, 9, 11), (Sensor.B6, 12, 14), (Sensor.B5, 16, 18), (Sensor.B4, 20, 23), (Sensor.A3, 25, 27)),
    build_slide_areas((Sensor.A1, 0, 4), (Sensor.B8, 5, 8), (Sensor.B7, 9, 11), (Sensor.B6, 12, 14), (Sensor.B5, 16, 20), (Sensor.A4, 22, 24)),
    build_slide_areas((Sensor.A1, 0, 4), (Sensor.B8, 5, 8), (Sensor.B7, 9, 12), (Sensor.B6, 14, 17), (Sensor.A5, 19, 21)),
    build_slide_areas((Sensor.A1, 0, 4), (Sensor.B8, 5, 8), (Sensor.B7, 9, 11), (Sensor.B6, 13, 15), (Sensor.B5, 16, 18), (Sensor.B4, 19, 21), (Sensor.B3, 22, 24), (Sensor.B2, 25, 27), (Sensor.B1, 28, 30), (Sensor.B8, 31, 33), (Sensor.B7, 35, 38), (Sensor.A6, 40, 42)),
    build_slide_areas((Sensor.A1, 0, 4), (Sensor.B8, 7, 9), (Sensor.B7, 10, 12), (Sensor.B6, 13, 15), (Sensor.B5, 16, 18), (Sensor.B4, 20, 22), (Sensor.B3, 23, 25), (Sensor.B2, 26, 28), (Sensor.B1, 30, 32), (Sensor.B8, 33, 36), (Sensor.A7, 37, 40)),
    build_slide_areas((Sensor.A1, 0, 4), (Sensor.B8, 5, 8), (Sensor.B7, 9, 11), (Sensor.B6, 12, 14), (Sensor.B5, 15, 17), (Sensor.B4, 19, 21), (Sensor.B3, 22, 24), (Sensor.B2, 25, 27), (Sensor.B1, 28, 32), (Sensor.A8, 33, 36)),
    # Outer loop (pp - mirror qq)
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.B1, 5, 7), (Sensor.C, 10, 13), (Sensor.B4, 15, 17), (Sensor.A3, 21, 26), (Sensor.A2, 29, 32), (Sensor.A1, 33, 35)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.B1, 5, 7), (Sensor.C, 9, 13), (Sensor.B4, 14, 17), (Sensor.A3, 20, 25), (Sensor.A2, 26, 28)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.B1, 4, 7), (Sensor.C, 9, 13), (Sensor.B4, 14, 17), (Sensor.A3, 19, 22)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.B1, 5, 7), (Sensor.C, 9, 13), (Sensor.B4, 14, 17), (Sensor.A3, 20, 25), (Sensor.A2, 28, 33), (Sensor.B1, 34, 37), (Sensor.C, 39, 43), (Sensor.B4, 44, 46), (Sensor.A4, 47, 49)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.B1, 5, 7), (Sensor.C, 9, 13), (Sensor.B4, 14, 17), (Sensor.A3, 20, 25), (Sensor.A2, 28, 33), (Sensor.B1, 34, 37), (Sensor.C, 39, 43), (Sensor.B5, 44, 46), (Sensor.A5, 47, 49)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.B1, 5, 7), (Sensor.C, 9, 13), (Sensor.B4, 14, 17), (Sensor.A3, 20, 25), (Sensor.A2, 28, 33), (Sensor.B1, 34, 37), ((Sensor.C, Sensor.B8), 38, 40), ((Sensor.B7, Sensor.B6), 42, 44), (Sensor.A6, 46, 48)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.B1, 5, 7), (Sensor.C, 9, 13), (Sensor.B4, 14, 17), (Sensor.A3, 20, 25), (Sensor.A2, 28, 33), (Sensor.B1, 34, 37), (Sensor.B8, 38, 42), (Sensor.A7, 43, 46)),
    build_slide_areas((Sensor.A1, 0, 3), (Sensor.B1, 5, 7), (Sensor.C, 9, 13), (Sensor.B4, 14, 17), (Sensor.A3, 20, 25), (Sensor.A2, 28, 33), ((Sensor.B1, Sensor.A1), 35, 37), (Sensor.A8, 38, 41)),
    # Reflect (V)
    build_slide_areas((Sensor.A1, 0, 3), ((Sensor.B8, Sensor.A8), 6, 10, False), (Sensor.A7, 12, 19), (Sensor.B8, 21, 24), (Sensor.B1, 25, 28), (Sensor.A2, 29, 32)),
    build_slide_areas((Sensor.A1, 0, 3), ((Sensor.B8, Sensor.A8), 6, 10, False), (Sensor.A7, 12, 18), (Sensor.B7, 20, 22), (Sensor.C, 25, 27), (Sensor.B3, 28, 31), (Sensor.A3, 32, 34)),
    build_slide_areas((Sensor.A1, 0, 3), ((Sensor.B8, Sensor.A8), 6, 10, False), (Sensor.A7, 12, 19), (Sensor.B6, 21, 24), (Sensor.B5, 25, 28), (Sensor.A4, 29, 32)),
    build_slide_areas((Sensor.A1, 0, 3), ((Sensor.B8, Sensor.A8), 6, 10, False), (Sensor.A7, 12, 18), ((Sensor.B6, Sensor.A6), 21, 24, False), (Sensor.A5, 27, 28)),
    # Zig-zag (s)
    build_slide_areas((Sensor.A1, 0, 4), (Sensor.B8, 7, 9), (Sensor.B7, 10, 12), (Sensor.C, 14, 17), (Sensor.B3, 19, 21), (Sensor.B4, 22, 25), (Sensor.A5, 27, 30)),
    # Wifi (w)
    build_slide_areas((Sensor.N0, 0, 1)),
    build_slide_areas((Sensor.A1, 0, 0), (Sensor.B8, 2, 2), (Sensor.B7, 4, 4), ((Sensor.A6, Sensor.D6), 7, 7)),
    build_slide_areas((Sensor.A1, 0, 0), (Sensor.B1, 2, 2), (Sensor.C, 4, 4), ((Sensor.A5, Sensor.B5), 7, 7)),
    build_slide_areas((Sensor.A1, 0, 0), (Sensor.B2, 2, 2), (Sensor.B3, 4, 4), ((Sensor.A4, Sensor.D5), 7, 7)),
)

def get_slide_area_count(track: SlideTrackKind) -> int:
    return len(SLIDE_AREAS[track])

def get_slide_area_sensor(
    track: SlideTrackKind,
    area_index: int,
    sensor_index: int,
    button: Button,
    is_mirrored: bool,
) -> Sensor:
    source = SLIDE_AREAS[track][area_index].sensors[sensor_index]
    sensor = sensor_mirror(source, Sensor.A1) if is_mirrored else source
    return sensor_shift(sensor, button - 1)

def get_slide_area_path_on_active(track: SlideTrackKind, judged_area_count: int):
    return SLIDE_AREAS[track][judged_area_count].path_on_active

def get_slide_area_path_on_finish(track: SlideTrackKind, judged_area_count: int):
    return SLIDE_AREAS[track][judged_area_count].path_on_finish

def get_slide_area_can_skip(track: SlideTrackKind, area_index: int, chain: SlideChainInfo) -> bool:
    """Chain overrides of the area skip flags (slide skipping enabled)."""
    can_skip = SLIDE_AREAS[track][area_index].can_skip
    if chain.is_part:
        if chain.total_areas >= 4:
            can_skip = True
        elif chain.is_head and area_index < 2:
            can_skip = area_index == 0
        elif chain.is_final and area_index < 2:
            can_skip = area_index == 1
    return can_skip

class SlideQueueState(Record):
    """Represent a compact judge-queue state.

    The queue's areas are never stored: they are rebuilt from ``SLIDE_AREAS``.
    The latched state of the queue's areas are packed into a flag value
    """
    judged_area_count: int
    flags: int # Note: memories are f32 no matter how we typed it
    """
    Stores the touch state of the two judgment areas the slide is currently checking in bit
    | Bit | Area | Sensor | State     |
    |-----|------|--------|-----------|
    | 1   | 0    | 0      | activated |
    | 2   | 0    | 0      | released  |
    | 3   | 0    | 1      | activated |
    | 4   | 0    | 1      | released  |
    | 5   | 1    | 0      | activated |
    | 6   | 1    | 0      | released  |
    | 7   | 1    | 1      | activated |
    | 8   | 1    | 1      | released  |
    """

    @staticmethod
    def _flag_bit(area_offset: int, sensor_offset: int, activated: bool):
        bit = 1 if activated else 2
        if area_offset == 1:
            bit *= 16
        if sensor_offset == 1:
            bit *= 4
        return bit

    def _test_flag(self, bit: int):
        return (self.flags // bit) % 2 == 1

    def _set_flag(self, bit: int, value: bool) -> int:
        current = self._test_flag(bit)
        if value and not current:
            self.flags = self.flags + bit
        elif not value and current:
            self.flags = self.flags - bit
        return self.flags

    def _check_slide_area(
        self,
        area_offset: int,
        track: SlideTrackKind,
        button: Button,
        is_mirrored: bool,
        is_last: bool,
    ) -> tuple[bool, bool]:
        """Update the latches of window area ``area_offset``; return ``(active, finished)``."""
        area_index = self.judged_area_count + area_offset
        sensor_count = len(SLIDE_AREAS[track][area_index].sensors)
        active = False
        finished = False
        for sensor_offset in range(sensor_count):
            sensor = get_slide_area_sensor(track, area_index, sensor_offset, button, is_mirrored)
            activated_bit = self._flag_bit(area_offset, sensor_offset, True)
            released_bit = self._flag_bit(area_offset, sensor_offset, False)
            was_activated = (
                self._test_flag(activated_bit)
                or InputState.sensor_note_started[sensor - 1]
                or InputState.sensor_note_down[sensor - 1]
            )
            was_released = was_activated and InputState.sensor_note_ended[sensor - 1]
            self._set_flag(activated_bit, was_activated)
            self._set_flag(released_bit, was_released)
            active = active or was_activated
            if is_last:
                finished = finished or was_activated
            else:
                finished = finished or (was_activated and was_released)
        return active, finished

    def advance_queue(self, steps: int):
        self.judged_area_count += steps
        if steps == 1:
            self.flags = self.flags // 16
        else:
            self.flags = 0

    def check_queue(
        self,
        track: SlideTrackKind,
        button: Button,
        is_mirrored: bool,
        is_final_queue: bool,
        chain: SlideChainInfo,
    ) -> bool:
        """Advance the queue from this frame's input. Returns whether any area is triggered
        (active or finished)."""
        triggered = False
        area_count = get_slide_area_count(track)
        while self.judged_area_count < area_count:
            index = self.judged_area_count
            advance = 0
            active, finished = self._check_slide_area(
                0, track, button, is_mirrored, is_final_queue and index == area_count - 1
            )
            triggered = triggered or active
            if finished:
                advance = 1
            if index + 1 < area_count and (get_slide_area_can_skip(track, index, chain) or active):
                next_active, next_finished = self._check_slide_area(
                    1, track, button, is_mirrored, is_final_queue and index + 1 == area_count - 1
                )
                triggered = triggered or next_active
                if next_finished:
                    advance = 2
                elif next_active:
                    advance = 1
            if advance == 0:
                break
            self.advance_queue(advance)
        return triggered

    def get_remaining_area(self, track: SlideTrackKind) -> int:
        return max(get_slide_area_count(track) - self.judged_area_count, 0)

    def force_finish(self, track: SlideTrackKind):
        """Empty the queue (and hide the whole path)."""
        self.judged_area_count = get_slide_area_count(track)
        self.flags = 0

    def get_path_hidden_count(self, track: SlideTrackKind) -> int:
        """Number of leading path points to hide, derived from the queue state."""
        area_count = get_slide_area_count(track)
        index = self.judged_area_count
        hidden = 0
        if index >= area_count:
            hidden = SLIDE_PATH_ALL_HIDDEN
        else:
            if index > 0:
                hidden = get_slide_area_path_on_finish(track, index - 1)
            FIRST_WAS_ACTIVATED_BIT = self._flag_bit(0, 0, activated=True)
            SECOND_WAS_ACTIVATED_BIT = self._flag_bit(0, 1, activated=True)
            if self._test_flag(FIRST_WAS_ACTIVATED_BIT) or self._test_flag(SECOND_WAS_ACTIVATED_BIT):
                hidden = max(hidden, get_slide_area_path_on_active(track, index))
        return hidden


SLIDE_JUDGMENT_CONST = Array(
    0.0,
    # Circle
    0.058, 0.465, 0.233, 0.155, 0.116, 0.093, 0.078, 0.066,
    # Line
    0.182, 0.19, 0.152,
    # Center
    0.185, 0.154, 0.158, 0.158,
    # Loop in
    0.095, 0.112, 0.125, 0.139, 0.16, 0.08, 0.084, 0.0895,
    # Loop out
    0.065, 0.086, 0.157, 0.065, 0.065, 0.067, 0.079, 0.0626,
    # Refelect
    0.1, 0.104, 0.098, 0.105,
    # Zigzag
    0.13,
    # Fan
    0.16287, 0.0, 0.0, 0.0,
)

def get_slide_end_button(track: SlideTrackKind, start_button: Button, is_mirrored: bool) -> Button:
    end_button = 1
    match track:
        case SlideTrackKind.CIRCLE_1 | SlideTrackKind.CENTER_1 | SlideTrackKind.LOOP_IN_1 | SlideTrackKind.LOOP_OUT_1:
            end_button = 1
        case (SlideTrackKind.CIRCLE_2 | SlideTrackKind.CENTER_2
            | SlideTrackKind.LOOP_IN_2 | SlideTrackKind.LOOP_OUT_2 | SlideTrackKind.REFLECT_2):
            end_button = 2
        case (SlideTrackKind.CIRCLE_3 | SlideTrackKind.LINE_3 | SlideTrackKind.CENTER_3
            | SlideTrackKind.LOOP_IN_3 | SlideTrackKind.LOOP_OUT_3 | SlideTrackKind.REFLECT_3):
            end_button = 3
        case (SlideTrackKind.CIRCLE_4 | SlideTrackKind.LINE_4 | SlideTrackKind.CENTER_4
            | SlideTrackKind.LOOP_IN_4 | SlideTrackKind.LOOP_OUT_4 | SlideTrackKind.REFLECT_4):
            end_button = 4
        case (SlideTrackKind.CIRCLE_5 | SlideTrackKind.LINE_5
            | SlideTrackKind.LOOP_IN_5 | SlideTrackKind.LOOP_OUT_5 | SlideTrackKind.REFLECT_5
            | SlideTrackKind.ZIG_ZAG | SlideTrackKind.FAN):
            end_button = 5
        case SlideTrackKind.CIRCLE_6 | SlideTrackKind.LOOP_IN_6 | SlideTrackKind.LOOP_OUT_6:
            end_button = 6
        case SlideTrackKind.CIRCLE_7 | SlideTrackKind.LOOP_IN_7 | SlideTrackKind.LOOP_OUT_7:
            end_button = 7
        case SlideTrackKind.CIRCLE_8 | SlideTrackKind.LOOP_IN_8 | SlideTrackKind.LOOP_OUT_8:
            end_button = 8
        case SlideTrackKind.FAN_L:
            end_button = 6
        case SlideTrackKind.FAN_C:
            end_button = 5
        case SlideTrackKind.FAN_R:
            end_button = 4
        case _:
            assert_never(track)
            end_button = 5
    if is_mirrored:
        end_button = button_mirror(end_button, Sensor.A1)
    end_button = button_shift(end_button, start_button - 1)
    return end_button

def get_star_note_kind(kind: SlideKind) -> NoteKind:
    match kind:
        case SlideKind.NORMAL_SLIDE | SlideKind.WIFI_SLIDE:
            return NoteKind.NORM_STAR
        case SlideKind.EACH_SLIDE | SlideKind.EACH_WIFI_SLIDE:
            return NoteKind.EACH_STAR
        case SlideKind.BREAK_SLIDE | SlideKind.BREAK_WIFI_SLIDE:
            return NoteKind.BREAK_STAR
        case _:
            assert_never(kind)
            return NoteKind.NORM_STAR

def get_slide_kind_variant(kind: SlideKind, wifi: bool) -> SlideKind:
    """Same colour (normal / each / break) as ``kind``, as a Wi-Fi or a single-track kind."""
    result = SlideKind.NORMAL_SLIDE
    match kind:
        case SlideKind.NORMAL_SLIDE | SlideKind.WIFI_SLIDE:
            result = SlideKind.WIFI_SLIDE if wifi else SlideKind.NORMAL_SLIDE
        case SlideKind.EACH_SLIDE | SlideKind.EACH_WIFI_SLIDE:
            result = SlideKind.EACH_WIFI_SLIDE if wifi else SlideKind.EACH_SLIDE
        case SlideKind.BREAK_SLIDE | SlideKind.BREAK_WIFI_SLIDE:
            result = SlideKind.BREAK_WIFI_SLIDE if wifi else SlideKind.BREAK_SLIDE
        case _:
            assert_never(kind)
    return result


def get_wifi_star_angle(star_track: SlideTrackKind, button: Button, is_mirrored: bool) -> float:
    """Fixed Wi-Fi star angle: ``-22.5 * (8 + i + 2 * (button - 1))`` degrees,
    i = 0 right star, 1 centre star, 2 left star (by on-screen side)."""
    side = 1
    if star_track == SlideTrackKind.FAN_R:
        side = 2 if is_mirrored else 0
    elif star_track == SlideTrackKind.FAN_L:
        side = 0 if is_mirrored else 2
    return -pi / 8 * (8 + side + 2 * (button - 1))


def get_fade_in_end_time(target_time: float) -> float:
    """When a slide's path is fully shown; its input window opens then too."""
    return target_time - 3 / 60


SLIDE_FADE_IN_MAX_ALPHA = 0.5

def get_slide_path_alpha(start_time: float, target_time: float, current_time: float) -> float:
    if current_time < start_time:
        return 0.0
    end_time = get_fade_in_end_time(target_time)
    if current_time > end_time:
        return 1.0
    fade_in_duration = clamp(end_time - start_time, 0, 0.2)
    fade_in_cutoff = start_time + fade_in_duration
    if current_time > fade_in_cutoff:
        return SLIDE_FADE_IN_MAX_ALPHA
    alpha = remap(start_time, fade_in_cutoff, 0, SLIDE_FADE_IN_MAX_ALPHA, current_time)
    return alpha


def draw_slide(
    kind: SlideKind,
    track: SlideTrackKind,
    button: Button,
    is_mirrored: bool,
    path_hidden_count: int,
    start_time: float,
    target_time: float,
    slide_time: float,
    end_time: float,
    is_chain_head: bool,
    is_chain_final: bool,
    chain_depth: int,
):
    """``chain_depth``: the segments before this one in its chain."""
    current_time = time()
    track_points = SLIDE_TRACK_POINTS[track]
    point_count = len(track_points)
    if point_count <= 0:
        return

    is_wifi = is_wifi_slide(kind)
    start_index = min(path_hidden_count, point_count)
    path_alpha = get_slide_path_alpha(start_time, target_time, current_time)
    for index in range(start_index, point_count):
        layer = get_z(LAYER_SLIDE_PATH, target_time, -chain_depth, point_count - index)
        if is_wifi:
            layout = layout_wifi_slide_path(index, track_points, button, is_mirrored)
            _wifi_slide_path_draw(kind, index, layout, layer, path_alpha)
        else:
            layout = layout_slide_path(index, track_points, button, is_mirrored)
            _slide_path_draw(kind, layout, layer, path_alpha)

    # Star visibility:
    # - chain head: fades/scales in from the star-note time to the slide start
    # - chain middle: hidden until their own slide start, then show and travel until end time, then hide on arrival
    # - chain final: don't hide on arrival, wait at the last point until despawn
    if not is_chain_head and current_time < slide_time:
        return
    if not is_chain_final and current_time >= end_time:
        return
    star_alpha = 1.0
    if is_chain_head and slide_time > target_time:
        star_alpha = unlerp_clamped(target_time, slide_time, current_time)
    star_scale = star_alpha + 0.5

    star_kind = get_star_note_kind(kind)
    progress = unlerp(slide_time, end_time, current_time)
    if is_wifi:
        for draw_order, star_track in enumerate(
            (SlideTrackKind.FAN_R, SlideTrackKind.FAN_L, SlideTrackKind.FAN_C)
        ):
            star_points = SLIDE_TRACK_POINTS[star_track]
            star_layout = layout_slide_head(progress, star_points, button, is_mirrored, rotate_head=False)
            star_layout = star_layout.scale_centered(Vec2.one() * star_scale)
            star_layout = star_layout.rotate_centered(get_wifi_star_angle(star_track, button, is_mirrored))
            _note_draw(star_kind, star_layout, get_z(LAYER_SLIDE_NOTE, target_time, draw_order), star_alpha)
    else:
        star_points = build_slide_star_points(track_points, get_slide_end_button(track, 1, False))
        star_layout = layout_slide_head(progress, star_points, button, is_mirrored)
        star_layout = star_layout.scale_centered(Vec2.one() * star_scale)
        _note_draw(star_kind, star_layout, get_z(LAYER_SLIDE_NOTE, target_time), star_alpha)

def _slide_path_draw(kind: SlideKind, layout: Quad, layer: ZIndexes, alpha: float = 1):
    match kind:
        case SlideKind.NORMAL_SLIDE:
            ActiveSkin.slide_path.draw(layout, layer.tuple, alpha)
        case SlideKind.EACH_SLIDE:
            ActiveSkin.each_slide_path.draw(layout, layer.tuple, alpha)
        case SlideKind.BREAK_SLIDE:
            ActiveSkin.break_slide_path.draw(layout, layer.tuple, alpha)
        case _:
            assert_never(kind)

def _wifi_slide_path_draw(
    kind: SlideKind,
    index: int,
    layout: Quad,
    layer: ZIndexes,
    alpha: float = 1,
):
    match kind:
        case SlideKind.WIFI_SLIDE:
            ActiveSkin.wifi_slide_paths[index].draw(layout, layer.tuple, alpha)
        case SlideKind.EACH_WIFI_SLIDE:
            ActiveSkin.each_wifi_slide_paths[index].draw(layout, layer.tuple, alpha)
        case SlideKind.BREAK_WIFI_SLIDE:
            ActiveSkin.break_wifi_slide_paths[index].draw(layout, layer.tuple, alpha)
        case _:
            assert_never(kind)

def get_slide_appear_duration(speed: float):
    assert_true(speed != 0, "Speed 0 is not supported!")
    fade_speed = max(abs(Layout.note_speed * speed), 0.01)
    fade_time = from_skin_px(392.6913) / fade_speed
    fade_time += Options.slide_fade_offset / 1000
    return fade_time


def init_slide_score(archetypes: Iterable[type[WeightedArchetype]]):
    for archetype in archetypes:
        if not archetype.is_scored:
            continue
        weight = MAX_BREAK_WEIGHT if is_break_slide(archetype.key) else archetype.score_weight()
        archetype.archetype_score_multiplier = weight

def init_slide_life(archetypes: Iterable[type[WeightedArchetype]]):
    for archetype in archetypes:
        if not archetype.is_scored:
            continue
        weight = MAX_BREAK_WEIGHT if is_break_slide(archetype.key) else archetype.score_weight()
        init_life_loss(archetype, weight)


## Connection chains. The helpers read imported data only, so they're safe in any preprocess order,
## and find the current mode's archetypes by name, so play and watch share them.

# Upper bound on chain walks; guards against malformed (cyclic) level data.
MAX_CHAIN_LENGTH = 32

SlideRef: TypeAlias = int | EntityRef[Any]


class ChainSlide(Protocol):
    """What every slide archetype imports, in play and watch."""
    key: int | float
    beat: float
    track: SlideTrackKind
    wait_duration: float
    slide_duration: float
    prev_slide_ref: EntityRef[Any]


class SingleConnSlide(ChainSlide, Protocol):
    next_slide_ref: EntityRef[Any]


class WifiConnSlide(SingleConnSlide, Protocol):
    next_slide_l_ref: EntityRef[Any]
    next_slide_r_ref: EntityRef[Any]


def get_slide_index(slide: SlideRef) -> int:
    if isinstance(slide, EntityRef):
        return slide.index
    return slide


def slide_at(slide: SlideRef) -> ChainSlide:
    """Any slide: every slide archetype starts with the same fields."""
    archetype = get_archetype_by_name(archetype_names.NORMAL_SLIDE_NOTE)
    return cast(ChainSlide, archetype.at(get_slide_index(slide), check=False))


def single_conn_slide_at(slide: SlideRef) -> SingleConnSlide:
    archetype = get_archetype_by_name(archetype_names.CONN_SLIDE_NOTE)
    return cast(SingleConnSlide, archetype.at(get_slide_index(slide), check=False))


def wifi_conn_slide_at(slide: SlideRef) -> WifiConnSlide:
    archetype = get_archetype_by_name(archetype_names.CONN_WIFI_SLIDE_NOTE)
    return cast(WifiConnSlide, archetype.at(get_slide_index(slide), check=False))


def is_single_conn_slide_at(slide: SlideRef) -> bool:
    return get_archetype_by_name(archetype_names.CONN_SLIDE_NOTE).is_at(get_slide_index(slide))


def is_wifi_conn_slide_at(slide: SlideRef) -> bool:
    return get_archetype_by_name(archetype_names.CONN_WIFI_SLIDE_NOTE).is_at(get_slide_index(slide))


def is_wifi_slide_at(slide: SlideRef) -> bool:
    index = get_slide_index(slide)
    return (
        is_wifi_conn_slide_at(index)
        or get_archetype_by_name(archetype_names.NORMAL_WIFI_SLIDE_NOTE).is_at(index)
        or get_archetype_by_name(archetype_names.EACH_WIFI_SLIDE_NOTE).is_at(index)
        or get_archetype_by_name(archetype_names.BREAK_WIFI_SLIDE_NOTE).is_at(index)
    )


def get_next_slide_index(slide: SlideRef, branch: SlideBranch) -> int:
    """Index of the slide continuing from ``index`` on ``branch`` (0 if none)."""
    index = get_slide_index(slide)
    result = 0
    if is_single_conn_slide_at(index):
        if branch == SlideBranch.BRANCH_C:
            result = single_conn_slide_at(index).next_slide_ref.index
    elif is_wifi_conn_slide_at(index):
        wifi = wifi_conn_slide_at(index)
        match branch:
            case SlideBranch.BRANCH_C:
                result = wifi.next_slide_ref.index
            case SlideBranch.BRANCH_L:
                result = wifi.next_slide_l_ref.index
            case SlideBranch.BRANCH_R:
                result = wifi.next_slide_r_ref.index
            case _:
                assert_never(branch)
    return max(result, 0)


def get_first_next_slide_index(slide: SlideRef) -> int:
    """C, then L, then R."""
    index = get_slide_index(slide)
    result = get_next_slide_index(index, SlideBranch.BRANCH_C)
    if result <= 0:
        result = get_next_slide_index(index, SlideBranch.BRANCH_L)
    if result <= 0:
        result = get_next_slide_index(index, SlideBranch.BRANCH_R)
    return result


def get_slide_entity_area_count(slide: SlideRef) -> int:
    index = get_slide_index(slide)
    count = 0
    if is_wifi_slide_at(index):
        count = get_slide_area_count(SlideTrackKind.FAN_C)
    else:
        count = get_slide_area_count(slide_at(index).track)
    return count


def is_conn_slide_at(slide: SlideRef) -> bool:
    index = get_slide_index(slide)
    return is_single_conn_slide_at(index) or is_wifi_conn_slide_at(index)


def get_slide_bar_count(slide: SlideRef) -> int:
    index = get_slide_index(slide)
    return len(SLIDE_TRACK_POINTS[slide_at(index).track])


def get_primary_final_index(slide: SlideRef) -> int:
    """Final slide reached by following C, then L, then R."""
    index = get_slide_index(slide)
    current = index
    steps = 0
    while current > 0 and is_conn_slide_at(current) and steps < MAX_CHAIN_LENGTH:
        current = get_first_next_slide_index(current)
        steps += 1
    return current


def get_path_bar_count(slide: SlideRef) -> int:
    """Bars from the chain head to ``final_index`` (inclusive)."""
    final_index = get_slide_index(slide)
    bars = 0
    current = final_index
    steps = 0
    while current > 0 and steps < MAX_CHAIN_LENGTH:
        bars += get_slide_bar_count(current)
        current = slide_at(current).prev_slide_ref.index
        steps += 1
    return bars


def get_path_total_beats(slide: SlideRef) -> float:
    """Sum of imported slide durations from the chain head to ``final_index`` (inclusive)."""
    final_index = get_slide_index(slide)
    total = 0.0
    current = final_index
    steps = 0
    while current > 0 and steps < MAX_CHAIN_LENGTH:
        part = slide_at(current)
        total += part.slide_duration
        current = part.prev_slide_ref.index
        steps += 1
    return total


def get_conn_segment_beats(slide: SlideRef) -> float:
    """Constant star speed: the primary final's total, split by bar count."""
    index = get_slide_index(slide)
    final_index = get_primary_final_index(index)
    beats = 0.0
    if final_index > 0 and not is_conn_slide_at(final_index):
        beats = get_path_total_beats(final_index) * get_slide_bar_count(index) / get_path_bar_count(final_index)
    return beats


def get_segment_beats(slide: SlideRef) -> float:
    index = get_slide_index(slide)
    MIN_SEGMENT_BEATS = 1 / 64
    beats = 0.0
    if is_conn_slide_at(index):
        beats = get_conn_segment_beats(index)
    else:
        preceding = 0.0
        current = slide_at(index).prev_slide_ref.index
        steps = 0
        while current > 0 and steps < MAX_CHAIN_LENGTH:
            preceding += get_conn_segment_beats(current)
            current = slide_at(current).prev_slide_ref.index
            steps += 1
        beats = max(get_path_total_beats(index) - preceding, MIN_SEGMENT_BEATS)
    return beats


def get_chain_max_total(slide: SlideRef) -> float:
    """Longest path total among the finals reachable from ``index``."""
    index = get_slide_index(slide)
    stack = VarArray[int, Dim[16]].new()
    stack.append(index)
    result = 0.0
    steps = 0
    while len(stack) > 0 and steps < MAX_CHAIN_LENGTH:
        current = stack.pop()
        if is_conn_slide_at(current):
            for branch in range(3):
                next_index = get_next_slide_index(current, branch)
                if next_index > 0 and not stack.is_full():
                    stack.append(next_index)
        else:
            result = max(result, get_path_total_beats(current))
        steps += 1
    return result


def get_chain_total_areas(slide: SlideRef) -> int:
    """Total judge areas along the first-branch path:
    Σ(areas - 1) over non-final parts + areas of the final part."""
    head_index = get_slide_index(slide)
    total = 0
    current = head_index
    steps = 0
    while current > 0 and steps < MAX_CHAIN_LENGTH:
        next_index = get_first_next_slide_index(current)
        count = get_slide_entity_area_count(current)
        if next_index > 0:
            total += count - 1
        else:
            total += count
        current = next_index
        steps += 1
    return total


def get_conn_slide_kind(slide: SlideRef, wifi: bool) -> SlideKind:
    index = get_slide_index(slide)
    current = index
    steps = 0
    while current > 0 and (is_single_conn_slide_at(current) or is_wifi_conn_slide_at(current)) and steps < MAX_CHAIN_LENGTH:
        current = get_first_next_slide_index(current)
        steps += 1
    final_kind = SlideKind.NORMAL_SLIDE
    if current > 0 and not is_single_conn_slide_at(current) and not is_wifi_conn_slide_at(current):
        final_kind = cast(SlideKind, slide_at(current).key)
    return get_slide_kind_variant(final_kind, wifi)


STAR_ROTATE_SPEED_PER_LENGTH = 68.54838709677419 * 0.47 / 1000 / 0.0034803742562305 / 180
STAR_ROTATE_SPEED_MAX = 1080 / 180


def get_star_rotate_speed(slide_length: float, duration: float) -> float:
    """Star spin for a slide ``slide_length`` path points long (one more per segment), taking ``duration`` seconds."""
    speed = STAR_ROTATE_SPEED_MAX
    if duration > 0:
        # speed_deg = max(-68.548 * ratio, -1080) deg/s
        # ratio = (L * 0.47 / (T * 1000)) / 0.0034803742562305
        speed = min(STAR_ROTATE_SPEED_PER_LENGTH * slide_length / duration, STAR_ROTATE_SPEED_MAX)
    return speed


def get_chain_star_rotate_speed(slide: SlideRef, start_beat: float) -> float:
    """Star spin for the chain starting at ``head_index``, along its primary path."""
    head_index = get_slide_index(slide)
    slide_length = 0
    current = head_index
    steps = 0
    while current > 0 and steps < MAX_CHAIN_LENGTH:
        if is_wifi_slide_at(current):
            # Wifi length is the same as a straight 1 to 5 slide
            slide_length += len(SLIDE_TRACK_POINTS[SlideTrackKind.LINE_5]) + 1
        else:
            slide_length += get_slide_bar_count(current) + 1
        current = get_first_next_slide_index(current)
        steps += 1
    final_index = get_primary_final_index(head_index)
    total = 0.0
    if final_index > 0:
        total = get_path_total_beats(final_index)
    duration = beat_to_time(start_beat + total) - beat_to_time(start_beat)
    return get_star_rotate_speed(slide_length, duration)


def get_chain_start_beat(slide: SlideRef) -> float:
    """When the chain through ``index`` starts sliding: its head's beat and wait."""
    index = get_slide_index(slide)
    head_index = index
    prev_index = slide_at(index).prev_slide_ref.index
    steps = 0
    while prev_index > 0 and steps < MAX_CHAIN_LENGTH:
        head_index = prev_index
        prev_index = slide_at(prev_index).prev_slide_ref.index
        steps += 1
    head = slide_at(head_index)
    return head.beat + head.wait_duration
