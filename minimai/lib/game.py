from enum import IntEnum, auto
from typing import assert_never, cast

from minimai.lib.options import Options

Button = int

class ArcadeJudgment(IntEnum):
    """The arcade's grades (Sonolus' Judgment has only four)."""
    NONE = 0
    CRITICAL_PERFECT = auto()
    HIGH_PERFECT = auto()
    LOW_PERFECT = auto()
    CRITICAL_GREAT = auto()
    HIGH_GREAT = auto()
    LOW_GREAT = auto()
    GOOD = auto()
    MISS = auto()


class Sensor(IntEnum):
    N0 = 0 # Not assigned / Invalid / None
    A1 = auto()
    A2 = auto()
    A3 = auto()
    A4 = auto()
    A5 = auto()
    A6 = auto()
    A7 = auto()
    A8 = auto()
    B1 = auto()
    B2 = auto()
    B3 = auto()
    B4 = auto()
    B5 = auto()
    B6 = auto()
    B7 = auto()
    B8 = auto()
    C = auto()
    D1 = auto()
    D2 = auto()
    D3 = auto()
    D4 = auto()
    D5 = auto()
    D6 = auto()
    D7 = auto()
    D8 = auto()
    E1 = auto()
    E2 = auto()
    E3 = auto()
    E4 = auto()
    E5 = auto()
    E6 = auto()
    E7 = auto()
    E8 = auto()

class SensorGroup(IntEnum):
    N = 0 # Not assigned / Invalid / None
    A = auto()
    B = auto()
    C = auto()
    D = auto()
    E = auto()

def sensor_to_group(sensor: Sensor):
   match sensor:
        case Sensor.N0:
            return SensorGroup.N
        case (
            Sensor.A1 | Sensor.A2 | Sensor.A3 | Sensor.A4 |
            Sensor.A5 | Sensor.A6 | Sensor.A7 | Sensor.A8
        ):
            return SensorGroup.A
        case (
            Sensor.B1 | Sensor.B2 | Sensor.B3 | Sensor.B4 |
            Sensor.B5 | Sensor.B6 | Sensor.B7 | Sensor.B8
        ):
            return SensorGroup.B
        case Sensor.C:
            return SensorGroup.C
        case (
            Sensor.D1 | Sensor.D2 | Sensor.D3 | Sensor.D4 |
            Sensor.D5 | Sensor.D6 | Sensor.D7 | Sensor.D8
        ):
            return SensorGroup.D
        case (
            Sensor.E1 | Sensor.E2 | Sensor.E3 | Sensor.E4 |
            Sensor.E5 | Sensor.E6 | Sensor.E7 | Sensor.E8
        ):
            return SensorGroup.E
        case _:
            assert_never(sensor)

def sensor_shift(sensor: Sensor, offset: int) -> Sensor:
    if offset == 0 or sensor == Sensor.N0:
        return sensor
    base_sensor = Sensor.N0
    group = sensor_to_group(sensor)
    match group:
        case SensorGroup.A:
            base_sensor = Sensor.A1
        case SensorGroup.B:
            base_sensor = Sensor.B1
        case SensorGroup.C:
            return sensor
        case SensorGroup.D:
            base_sensor = Sensor.D1
        case SensorGroup.E:
            base_sensor = Sensor.E1
        case _:
            assert_never(group)
            return sensor
    offset = (sensor - base_sensor + offset) % 8
    return cast(Sensor, base_sensor + offset)

def sensor_offset(sensor: Sensor) -> int:
    group = sensor_to_group(sensor)
    if group in (SensorGroup.A, SensorGroup.B):
        return (sensor - Sensor.A1) % 8
    if group in (SensorGroup.D, SensorGroup.E):
        return (sensor - Sensor.D1) % 8
    return 0

def is_sensor_same_axis(source: Sensor, target: Sensor) -> bool:
    """Return whether the two sensors lie on the same center-crossing axis."""
    source_group = sensor_to_group(source)
    target_group = sensor_to_group(target)

    if source_group == SensorGroup.C or target_group == SensorGroup.C:
        return True

    axis_group_ab = (SensorGroup.A, SensorGroup.B)
    axis_group_de = (SensorGroup.D, SensorGroup.E)
    same_axis_group_ab = source_group in axis_group_ab and target_group in axis_group_ab
    same_axis_group_de = source_group in axis_group_de and target_group in axis_group_de
    same_axis_group = same_axis_group_ab or same_axis_group_de

    if not same_axis_group:
        return False

    difference = abs(sensor_offset(source) - sensor_offset(target))
    return difference % 4 == 0

def sensor_mirror(source: Sensor, baseline: Sensor) -> Sensor:
    """Reflect ``source`` across the center-crossing axis of ``baseline``."""
    source_group = sensor_to_group(source)
    baseline_group = sensor_to_group(baseline)

    if source_group == SensorGroup.C or is_sensor_same_axis(source, baseline):
        return source
    if source_group == SensorGroup.N or baseline_group == SensorGroup.N:
        return source

    source_offset = sensor_offset(source)
    baseline_offset = sensor_offset(baseline)
    source_is_axis_ab = source_group in (SensorGroup.A, SensorGroup.B)
    baseline_is_axis_ab = baseline_group in (SensorGroup.A, SensorGroup.B)

    # Same axis: 2 * baseline - source.
    phase_offset = 0
    # Different axis change the phase offset
    if source_is_axis_ab != baseline_is_axis_ab:
        phase_offset = -1 if source_is_axis_ab else 1

    mirrored_offset = (2 * baseline_offset - source_offset + phase_offset) % 8
    return sensor_shift(source, mirrored_offset - source_offset)


def button_shift(button: Button, offset: int) -> Button:
    """``button`` moved ``offset`` buttons clockwise (negative: counterclockwise), wrapping in 1..8."""
    return (button - 1 + offset) % 8 + 1


def button_mirror(source: Button, baseline: Sensor) -> Button:
    """Reflect button ``source`` across the center-crossing axis of ``baseline``."""
    baseline_group = sensor_to_group(baseline)
    if baseline_group == SensorGroup.C or baseline_group == SensorGroup.N:
        return source
    # The axis passes through the baseline: buttons sit on the A / B axes, half a step from D / E.
    phase_offset = 0
    if baseline_group in (SensorGroup.D, SensorGroup.E):
        phase_offset = -1
    return button_shift(1, 2 * sensor_offset(baseline) - (source - 1) + phase_offset)


class MirrorMode(IntEnum):
    """The chart mirror option. Reflections are across an axis between buttons, through two D
    sensors; ROTATE_180 is left-right and up-down together."""
    OFF = 0
    LEFT_RIGHT = auto()
    UP_DOWN = auto()
    ROTATE_180 = auto()
    DIAGONAL_LEFT = auto()
    DIAGONAL_RIGHT = auto()


def get_mirror_axis(mode: MirrorMode) -> Sensor:
    """The D sensor the reflection axis of ``mode`` passes through (N0 for OFF / ROTATE_180)."""
    result = Sensor.N0
    match mode:
        case MirrorMode.LEFT_RIGHT:
            result = Sensor.D1
        case MirrorMode.DIAGONAL_RIGHT:
            result = Sensor.D2
        case MirrorMode.UP_DOWN:
            result = Sensor.D3
        case MirrorMode.DIAGONAL_LEFT:
            result = Sensor.D4
        case _:
            result = Sensor.N0
    return result


def is_mirror_reflection(mode: MirrorMode) -> bool:
    """Whether ``mode`` reflects the chart (reversing slide shapes); OFF and ROTATE_180 don't."""
    return mode != MirrorMode.OFF and mode != MirrorMode.ROTATE_180


def apply_button_mirror_option(button: Button) -> Button:
    """``button`` under the mirror option (unchanged when it's OFF)."""
    mode = Options.mirror
    result = button
    if mode == MirrorMode.ROTATE_180:
        result = button_shift(button, 4)
    elif mode != MirrorMode.OFF:
        result = button_mirror(button, get_mirror_axis(mode))
    return result


def apply_sensor_mirror_option(sensor: Sensor) -> Sensor:
    """``sensor`` under the mirror option (unchanged when it's OFF)."""
    mode = Options.mirror
    result = sensor
    if mode == MirrorMode.ROTATE_180:
        result = sensor_shift(sensor, 4)
    elif mode != MirrorMode.OFF:
        result = sensor_mirror(sensor, get_mirror_axis(mode))
    return result


def is_mirror_option_reflection() -> bool:
    """Whether the mirror option reflects the chart (slides flip their mirrored flag)."""
    return is_mirror_reflection(Options.mirror)


def get_button_range():
    return range(1, 9)


def get_button_iterator():
    return enumerate(get_button_range())


SENSOR_COUNT = Sensor.E8 - Sensor.N0 # 33


def get_sensor_iterator():
    return enumerate(s for s in Sensor if s is not Sensor.N0)