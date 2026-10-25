from math import ceil, pi
from typing import Iterable, Protocol, assert_never, cast

from sonolus.script.globals import level_data
from sonolus.script.quad import Quad, Rect
from sonolus.script.vec import Vec2
from sonolus.script.array import Array, Dim
from sonolus.script.containers import VarArray
from sonolus.script.record import Record
from sonolus.script.interval import Interval
from sonolus.script.debug import assert_true, debug_log

from minimai.lib.game import Button, Sensor, SensorGroup, get_button_iterator, sensor_offset, sensor_to_group
from minimai.lib.layout import Layout, get_button_angle_horizontal, get_dist_from_center, get_pos_from_center, get_sensor_angle_horizontal, get_sensor_group_dist_from_center
from minimai.lib.options import Options

class HitBoxLike(Protocol):
    def contains_point(self, point: Vec2) -> bool: ...
    def as_quads(self) -> Iterable[Quad]: ...


class CircTrapHitBox(Record):
    "A hitbox represent by the area of a circular trapezoid"
    center: Vec2
    angle: Interval
    distance: Interval

    def contains_point(self, point: Vec2, radius: float = 0) -> bool:
        from_center = (point - self.center)
        expand_distance = self.distance.expand(radius / 2)
        return from_center.magnitude in expand_distance \
            and from_center.angle in self.angle

    def as_quads(self):
        segements = ceil(self.angle.length / (pi / 8))
        for s in range(segements):
            start_angle = self.angle.start + s * pi / 8
            end_angle = start_angle + min(self.angle.end - start_angle, pi / 8)
            # For some reason Sonolus refuse to draw if two point overlaps (distance=0)
            # we'll offset the distance by 1e-3
            start_dist = max(self.distance.start, 1e-3)
            yield Quad(
                bl=get_pos_from_center(start_angle, start_dist),
                tl=get_pos_from_center(end_angle, start_dist),
                tr=get_pos_from_center(end_angle, self.distance.end),
                br=get_pos_from_center(start_angle, self.distance.end),
            )

def expand_quad(quad: Quad, radius: float):
    new_quad = +quad
    if radius == 0:
        return new_quad
    vertices = Array[Vec2, Dim[4]](quad.bl, quad.tl, quad.tr, quad.br)
    normals = +Array[Vec2, Dim[4]]
    for i in range(4):
        edge = vertices[(i + 1) % 4] - vertices[i]
        normals[i] = edge.orthogonal().normalize()
    expanded = +Array[Vec2, Dim[4]]
    for i in range(4):
        pv_normal = normals[(i - 1) % 4]
        normal = normals[i]
        miter = (normal + pv_normal).normalize()
        denominator = miter.dot(normal)
        scale_factor = radius / denominator if denominator != 0 else radius
        expanded[i] = vertices[i] + (miter * scale_factor)
    new_quad @= Quad(expanded[0], expanded[1], expanded[2], expanded[3])
    return new_quad

class NQuadHitBox[Size](Record):
    "A hitbox represent by combine n quads together"
    quads: Array[Quad, Size]

    def contains_point(self, point: Vec2, radius: float = 0) -> bool:
        return any(expand_quad(quad, radius).contains_point(point) for quad in self.quads)

    def as_quads(self):
        return self.quads

@level_data
class Hitboxes:
    touch_radius: float
    button: Array[CircTrapHitBox, Dim[8]]
    group_a: Array[NQuadHitBox[2], Dim[8]]
    group_b: Array[NQuadHitBox[2], Dim[8]]
    group_c: CircTrapHitBox
    group_d: Array[NQuadHitBox[2], Dim[8]]
    group_e: Array[NQuadHitBox[1], Dim[8]]

    @staticmethod
    def of_button_contains_point(btn: Button, pos: Vec2):
        if Options.button_size == 0:
            return False
        return Hitboxes.button[btn - 1].contains_point(pos)

    @staticmethod
    def of_button_as_quads(btn: Button):
        return Hitboxes.button[btn - 1].as_quads()

    @staticmethod
    def of_sensor_contains_point(sensor: Sensor, pos: Vec2):
        group = sensor_to_group(sensor)
        offset = sensor_offset(sensor)
        match group:
            case SensorGroup.A:
                return Hitboxes.group_a[offset].contains_point(pos, Hitboxes.touch_radius)
            case SensorGroup.B:
                return Hitboxes.group_b[offset].contains_point(pos, Hitboxes.touch_radius)
            case SensorGroup.C:
                return Hitboxes.group_c.contains_point(pos, Hitboxes.touch_radius)
            case SensorGroup.D:
                return Hitboxes.group_d[offset].contains_point(pos, Hitboxes.touch_radius)
            case SensorGroup.E:
                return Hitboxes.group_e[offset].contains_point(pos, Hitboxes.touch_radius)
            case _:
                assert_never(group)
                return False

    @staticmethod
    def of_sensor_as_quads(sensor: Sensor):
        quads = +VarArray[Quad, Dim[16]]
        group = sensor_to_group(sensor)
        def copy_to(quads: VarArray[Quad, Dim[16]], other: Iterable[Quad]):
            for quad in other:
                quads.append(quad)
                if quads.is_full():
                    break
        offset = sensor_offset(sensor)
        match group:
            case SensorGroup.A:
                copy_to(quads, Hitboxes.group_a[offset].as_quads())
            case SensorGroup.B:
                copy_to(quads, Hitboxes.group_b[offset].as_quads())
            case SensorGroup.C:
                copy_to(quads, Hitboxes.group_c.as_quads())
            case SensorGroup.D:
                copy_to(quads, Hitboxes.group_d[offset].as_quads())
            case SensorGroup.E:
                copy_to(quads, Hitboxes.group_e[offset].as_quads())
            case _:
                assert_never(group)
        return quads

BASE_TOUCH_RADIUS = 0.06
BUTTON_HITBOX_SIZE = 0.35

GROUP_A_ANGLE_WIDTH = 14 / 180 * pi
GROUP_A_BOT_L_DIST = 0.11
GROUP_A_BOT_R_DIST = 0.2
GROUP_A_TOP_DIST = 0.295

GROUP_B_TOP_ANGLE = 10 / 180 * pi
GROUP_B_MID_ANGLE = 22 / 180 * pi
GROUP_B_BOT_ANGLE = 22 / 180 * pi
GROUP_B_TOP_DIST = 0.16
GROUP_B_MID_DIST = 0.01
GROUP_B_BOT_DIST = 0.13

GROUP_C_HITBOX_SIZE = 0.225

GROUP_D_ANGLE_WIDTH = 8.5 / 180 * pi
GROUP_D_BOT_L_DIST = 0.13
GROUP_D_BOT_R_DIST = 0.03
GROUP_D_TOP_DIST = 0.27

GROUP_E_HITBOX_SIZE = 0.21

def init_hitboxes():
    Hitboxes.touch_radius = Options.input_radius_scale * BASE_TOUCH_RADIUS

    for i, b in get_button_iterator():
        center_angle = get_button_angle_horizontal(b)
        start_distance = Layout.button_distance
        angle = Options.button_angle * pi / 180
        button_size = BUTTON_HITBOX_SIZE * Layout.button_distance * Options.button_size
        Hitboxes.button[i] = CircTrapHitBox(
            center=Layout.ring_center,
            distance=Interval(start_distance, start_distance + button_size),
            angle=Interval(center_angle - angle / 2, center_angle + angle / 2)
        )

    for i in range(8):
        dist = get_sensor_group_dist_from_center(SensorGroup.A)
        angle = get_sensor_angle_horizontal(Sensor.A1 + i)
        l_angle = angle + GROUP_A_ANGLE_WIDTH
        r_angle = angle - GROUP_A_ANGLE_WIDTH
        bl_dist = dist - GROUP_A_BOT_L_DIST * Options.ring_size
        br_dist = dist - GROUP_A_BOT_R_DIST * Options.ring_size
        t_dist = dist + GROUP_A_TOP_DIST * Options.ring_size
        Hitboxes.group_a[i].quads[0] = Quad(
            bl=get_pos_from_center(l_angle, bl_dist),
            tl=get_pos_from_center(l_angle, t_dist),
            tr=get_pos_from_center(angle, t_dist),
            br=get_pos_from_center(angle, br_dist)
        )
        Hitboxes.group_a[i].quads[1] = Quad(
            br=get_pos_from_center(r_angle, bl_dist),
            tr=get_pos_from_center(r_angle, t_dist),
            tl=get_pos_from_center(angle, t_dist),
            bl=get_pos_from_center(angle, br_dist)
        )

    for i in range(8):
        dist = get_sensor_group_dist_from_center(SensorGroup.B)
        angle = get_sensor_angle_horizontal(Sensor.B1 + i)
        mid_dist = dist + GROUP_B_MID_DIST * Options.ring_size
        top_dist = dist + GROUP_B_TOP_DIST * Options.ring_size
        bot_dist = dist - GROUP_B_BOT_DIST * Options.ring_size
        Hitboxes.group_b[i].quads[0] = Quad(
            bl=get_pos_from_center(angle + GROUP_B_MID_ANGLE, mid_dist),
            tl=get_pos_from_center(angle + GROUP_B_TOP_ANGLE, top_dist),
            tr=get_pos_from_center(angle - GROUP_B_TOP_ANGLE, top_dist),
            br=get_pos_from_center(angle - GROUP_B_MID_ANGLE, mid_dist)
        )
        Hitboxes.group_b[i].quads[1] = Quad(
            br=get_pos_from_center(angle + GROUP_B_MID_ANGLE, mid_dist),
            tr=get_pos_from_center(angle + GROUP_B_BOT_ANGLE, bot_dist),
            tl=get_pos_from_center(angle - GROUP_B_BOT_ANGLE, bot_dist),
            bl=get_pos_from_center(angle - GROUP_B_MID_ANGLE, mid_dist)
        )

    center_size = GROUP_C_HITBOX_SIZE * Options.ring_size
    Hitboxes.group_c = CircTrapHitBox(
        center=Layout.ring_center,
        distance=Interval(0, center_size),
        angle=Interval(-pi, pi)
    )

    for i in range(8):
        dist = get_sensor_group_dist_from_center(SensorGroup.D)
        angle = get_sensor_angle_horizontal(Sensor.D1 + i)
        l_angle = angle + GROUP_D_ANGLE_WIDTH
        r_angle = angle - GROUP_D_ANGLE_WIDTH
        bl_dist = dist - GROUP_D_BOT_L_DIST * Options.ring_size
        br_dist = dist - GROUP_D_BOT_R_DIST * Options.ring_size
        t_dist = dist + GROUP_D_TOP_DIST * Options.ring_size
        Hitboxes.group_d[i].quads[0] = Quad(
            bl=get_pos_from_center(l_angle, bl_dist),
            tl=get_pos_from_center(l_angle, t_dist),
            tr=get_pos_from_center(angle, t_dist),
            br=get_pos_from_center(angle, br_dist)
        )
        Hitboxes.group_d[i].quads[1] = Quad(
            br=get_pos_from_center(r_angle, bl_dist),
            tr=get_pos_from_center(r_angle, t_dist),
            tl=get_pos_from_center(angle, t_dist),
            bl=get_pos_from_center(angle, br_dist)
        )

    for i in range(8):
        dist = get_sensor_group_dist_from_center(SensorGroup.E)
        angle = get_sensor_angle_horizontal(Sensor.E1 + i)
        center = get_pos_from_center(angle, dist)
        size = GROUP_E_HITBOX_SIZE * Options.ring_size
        rotate = ((i + 1) % 2) * pi / 4
        quad = Rect.from_center(center, Vec2(size, size)).as_quad().rotate_centered(rotate)
        Hitboxes.group_e[i] = NQuadHitBox(
            quads = Array(quad)
        )


def in_bounds(point: Vec2):
    max_distance = Hitboxes.button[0].distance.end
    return get_dist_from_center(point) <= max_distance