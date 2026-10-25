from enum import IntEnum, auto
from typing import assert_never, cast

Button = int

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


def get_button_range():
    return range(1, 9)


def get_button_iterator():
    return enumerate(get_button_range())


SENSOR_COUNT = Sensor.E8 - Sensor.N0 # 33


def get_sensor_iterator():
    return enumerate(s for s in Sensor if s is not Sensor.N0)