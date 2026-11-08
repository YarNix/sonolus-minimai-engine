from math import ceil, pi
from typing import Iterable, Protocol, Self, assert_never, cast

from sonolus.script.globals import level_data
from sonolus.script.quad import Quad, Rect
from sonolus.script.vec import Vec2, pnpoly
from sonolus.script.array import Array, Dim
from sonolus.script.containers import VarArray
from sonolus.script.record import Record
from sonolus.script.interval import Interval, clamp
from sonolus.script.debug import assert_true, debug_log

from minimai.lib.game import Button, Sensor, SensorGroup, get_button_iterator, sensor_offset, sensor_to_group
from minimai.lib.layout import (
    BUTTON_DISTANCE, Layout, get_button_angle_horizontal, get_dist_from_center, get_sensor_angle_horizontal,
    get_sensor_distance, layout_px_size, layout_ring_pos,
)
from minimai.lib.options import Options

class PointTestResult(Record):
    # Whether the point was inside the sensor
    inside: bool
    # Whether the point overlapped with the sensor given the touch radius
    touch: bool
    # Whether the point overlapped with the sensor given the note radius
    note: bool


class HitBoxLike(Protocol):
    def contains_point(self, point: Vec2) -> bool: ...
    def test_point(self, point: Vec2, touch_radius: float = 0, note_radius: float = 0) -> PointTestResult: ...
    def as_quads(self) -> Iterable[Quad]: ...
    def as_outline(self) -> Iterable[Vec2]: ...


class CircTrapHitBox(Record):
    "A hitbox represent by the area of a circular trapezoid"
    center: Vec2
    angle: Interval
    distance: Interval

    def contains_point(self, point: Vec2) -> bool:
        from_center = (point - self.center)
        return from_center.magnitude in self.distance and from_center.angle in self.angle

    def test_point(self, point: Vec2, touch_radius: float = 0, note_radius: float = 0) -> PointTestResult:
        from_center = (point - self.center)
        dist_squared = 0.0
        if from_center.angle in self.angle:
            magnitude = from_center.magnitude
            outside = max(self.distance.start - magnitude, magnitude - self.distance.end, 0)
            dist_squared = outside * outside
        else:
            # Outside the angle, the nearest points are on the two straight sides.
            dist_squared = min(
                side_distance_squared(from_center, Vec2.unit(self.angle.start), self.distance),
                side_distance_squared(from_center, Vec2.unit(self.angle.end), self.distance),
            )
        return PointTestResult(
            inside=dist_squared == 0,
            touch=dist_squared <= touch_radius * touch_radius,
            note=dist_squared <= note_radius * note_radius,
        )

    def as_quads(self):
        segements = ceil(self.angle.length / (pi / 8))
        for s in range(segements):
            start_angle = self.angle.start + s * pi / 8
            end_angle = start_angle + min(self.angle.end - start_angle, pi / 8)
            # For some reason Sonolus refuse to draw if two point overlaps (distance=0)
            # we'll offset the distance by 1e-3
            start_dist = max(self.distance.start, 1e-3)
            yield Quad(
                bl=self.center + Vec2.unit(start_angle) * start_dist,
                tl=self.center + Vec2.unit(end_angle) * start_dist,
                tr=self.center + Vec2.unit(end_angle) * self.distance.end,
                br=self.center + Vec2.unit(start_angle) * self.distance.end,
            )

    def as_outline(self) -> Iterable[Vec2]:
        point = +Vec2
        segments = ceil(self.angle.length / (pi / 8))
        is_circle = self.angle.length >= 2 * pi
        for s in range(segments if is_circle else segments + 1):
            angle = min(self.angle.start + s * pi / 8, self.angle.end)
            point @= self.center + Vec2.unit(angle) * self.distance.end
            yield point
        if not is_circle:
            for s in range(segments + 1):
                angle = max(self.angle.end - s * pi / 8, self.angle.start)
                point @= self.center + Vec2.unit(angle) * self.distance.start
                yield point

def side_distance_squared(point: Vec2, direction: Vec2, distance: Interval) -> float:
    """Squared distance from the segment along ``direction`` (a unit vector) over ``distance``."""
    offset = point - direction * distance.clamp(point.dot(direction))
    return offset.dot(offset)

def cross(a: Vec2, b: Vec2) -> float:
    return a.x * b.y - a.y * b.x

def segment_distance_squared(point: Vec2, a: Vec2, b: Vec2) -> float:
    edge = b - a
    t = clamp((point - a).dot(edge) / edge.dot(edge), 0, 1)
    offset = point - a - edge * t
    return offset.dot(offset)

class NQuadHitBox[Size](Record):
    "A hitbox represent by combine n quads together"
    quads: Array[Quad, Size]

    def contains_point(self, point: Vec2) -> bool:
        return any(quad.contains_point(point) for quad in self.quads)

    def test_point(self, point: Vec2, touch_radius: float = 0, note_radius: float = 0) -> PointTestResult:
        dist_squared = 1e9
        for quad in self.quads:
            if quad.contains_point(point):
                dist_squared = 0.0
            else:
                dist_squared = min(
                    dist_squared,
                    segment_distance_squared(point, quad.bl, quad.tl),
                    segment_distance_squared(point, quad.tl, quad.tr),
                    segment_distance_squared(point, quad.tr, quad.br),
                    segment_distance_squared(point, quad.br, quad.bl),
                )
        return PointTestResult(
            inside=dist_squared == 0,
            touch=dist_squared <= touch_radius * touch_radius,
            note=dist_squared <= note_radius * note_radius,
        )

    def as_quads(self):
        return self.quads

    def as_outline(self) -> Iterable[Vec2]:
        quad = self.quads[0]
        point = +Vec2
        for corner in (quad.bl, quad.tl, quad.tr, quad.br):
            point @= corner
            yield point

class PolygonHitBox[VertexCount, QuadCount](Record):
    "A hitbox represent by a polygon, vertices in outline order"
    vertices: Array[Vec2, VertexCount]
    # A circle around every vertex, to skip far away points.
    bound_center: Vec2
    bound_radius: float
    # The polygon split into quads, for drawing.
    quads: Array[Quad, QuadCount]

    @classmethod
    def new(cls, center: Vec2, vertices: Array[Vec2, VertexCount]) -> Self:
        """A polygon hitbox around ``center``, with its bound circle and its quads"""
        count = len(vertices)
        radius = 0.0
        for v in vertices:
            radius = max(radius, (v - center).magnitude)
        hitbox = cls(
            vertices=vertices,
            bound_center=center,
            bound_radius=radius,
            quads=+Array[Quad, (count - 1) // 2],
        )

        # Fan triangulation, with pairs of triangles merged into quads.
        # The fan starts from the reflex vertex if there is one, so it stays inside the polygon.
        area = 0.0
        for i in range(count):
            area += cross(vertices[i], vertices[(i + 1) % count])
        start = 0
        for i in range(count):
            prev = vertices[(i + count - 1) % count]
            here = vertices[i]
            after = vertices[(i + 1) % count]
            if cross(here - prev, after - here) * area < 0:
                start = i
        for q in range(len(hitbox.quads)):
            origin = vertices[start]
            first = vertices[(start + 2 * q + 1) % count]
            second = vertices[(start + 2 * q + 2) % count]
            if 2 * q + 3 < count:
                hitbox.quads[q] = Quad(origin, first, second, vertices[(start + 2 * q + 3) % count])
            else:
                # A triangle left over: split its outer edge in two.
                hitbox.quads[q] = Quad(origin, first, (first + second) / 2, second)
        return hitbox

    def contains_point(self, point: Vec2) -> bool:
        return pnpoly(self.vertices, point)

    def test_point(self, point: Vec2, touch_radius: float = 0, note_radius: float = 0) -> PointTestResult:
        dist_squared = self.distance_squared(point, max(touch_radius, note_radius))
        return PointTestResult(
            inside=dist_squared == 0,
            touch=dist_squared <= touch_radius * touch_radius,
            note=dist_squared <= note_radius * note_radius,
        )

    def distance_squared(self, point: Vec2, reach: float) -> float:
        """Squared distance from the polygon, 0 inside. Above reach² when farther than reach."""
        bound = self.bound_radius + reach
        to_bound = point - self.bound_center
        bound_dist_squared = to_bound.dot(to_bound)
        if bound_dist_squared > bound * bound:
            return bound_dist_squared
        if pnpoly(self.vertices, point):
            return 0.0
        count = len(self.vertices)
        return min(
            segment_distance_squared(point, self.vertices[i], self.vertices[(i + 1) % count]) for i in range(count)
        )

    def as_quads(self):
        return self.quads

    def as_outline(self) -> Iterable[Vec2]:
        """The outline as a closed loop of points"""
        for v in self.vertices:
            yield v

@level_data
class Hitboxes:
    touch_radius: float
    note_radius: float
    button: Array[CircTrapHitBox, Dim[8]]
    group_a: Array[PolygonHitBox[7, 3], Dim[8]]
    group_b: Array[PolygonHitBox[7, 3], Dim[8]]
    group_c: CircTrapHitBox
    group_d: Array[PolygonHitBox[6, 2], Dim[8]]
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
    def of_sensor_test_point(sensor: Sensor, pos: Vec2) -> PointTestResult:
        group = sensor_to_group(sensor)
        offset = sensor_offset(sensor)
        result = +PointTestResult
        match group:
            case SensorGroup.A:
                result @= Hitboxes.group_a[offset].test_point(pos, Hitboxes.touch_radius, Hitboxes.note_radius)
            case SensorGroup.B:
                result @= Hitboxes.group_b[offset].test_point(pos, Hitboxes.touch_radius, Hitboxes.note_radius)
            case SensorGroup.C:
                result @= Hitboxes.group_c.test_point(pos, Hitboxes.touch_radius, Hitboxes.note_radius)
            case SensorGroup.D:
                result @= Hitboxes.group_d[offset].test_point(pos, Hitboxes.touch_radius, Hitboxes.note_radius)
            case SensorGroup.E:
                result @= Hitboxes.group_e[offset].test_point(pos, Hitboxes.touch_radius, Hitboxes.note_radius)
            case _:
                assert_never(group)
        return result

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

    @staticmethod
    def of_sensor_as_outline(sensor: Sensor) -> Iterable[Vec2]:
        group = sensor_to_group(sensor)
        offset = sensor_offset(sensor)
        out = +Vec2
        match group:
            case SensorGroup.A:
                for point in Hitboxes.group_a[offset].as_outline():
                    out @= point
                    yield out
            case SensorGroup.B:
                for point in Hitboxes.group_b[offset].as_outline():
                    out @= point
                    yield out
            case SensorGroup.C:
                for point in Hitboxes.group_c.as_outline():
                    out @= point
                    yield out
            case SensorGroup.D:
                for point in Hitboxes.group_d[offset].as_outline():
                    out @= point
                    yield out
            case SensorGroup.E:
                for point in Hitboxes.group_e[offset].as_outline():
                    out @= point
                    yield out
            case _:
                assert_never(group)

# Ring units. Option scales are percentages of NOTE_RADIUS.
NOTE_RADIUS = 0.125
# Button hitbox depth, as a fraction of the button distance.
BUTTON_HITBOX_SIZE = 0.35

# Sensor hitbox distances and sizes are in ring units (0 = center, 1 = judgment ring).
GROUP_A_ANGLE_WIDTH = 14 / 180 * pi
GROUP_A_BOT_L_DIST = 0.113111
GROUP_A_BOT_MID_ANGLE = 6.72 / 180 * pi
GROUP_A_BOT_MID_DIST = 0.1694
GROUP_A_TOP_DIST = 0.303342

GROUP_B_TOP_ANGLE = 10 / 180 * pi
GROUP_B_MID_ANGLE = 22 / 180 * pi
GROUP_B_BOT_ANGLE = 22 / 180 * pi
GROUP_B_TOP_DIST = 0.164524
GROUP_B_MID_DIST = 0.010283
GROUP_B_BOT_DIST = 0.0587
GROUP_B_TIP_DIST = 0.1555

GROUP_C_HITBOX_SIZE = 0.231362

GROUP_D_ANGLE_WIDTH = 8.5 / 180 * pi
GROUP_D_BOT_L_DIST = 0.133676
GROUP_D_BOT_R_DIST = 0.030848
GROUP_D_TOP_DIST = 0.277635

GROUP_E_HITBOX_SIZE = 0.215938

def init_hitboxes():
    Hitboxes.touch_radius = layout_px_size(NOTE_RADIUS, Options.touch_radius)
    Hitboxes.note_radius = layout_px_size(NOTE_RADIUS, Options.note_radius)

    for i, b in get_button_iterator():
        center_angle = get_button_angle_horizontal(b)
        start_distance = layout_px_size(BUTTON_DISTANCE)
        angle = Options.button_angle * pi / 180
        button_size = layout_px_size(BUTTON_HITBOX_SIZE * BUTTON_DISTANCE, Options.button_size)
        Hitboxes.button[i] = CircTrapHitBox(
            center=Layout.ring_center,
            distance=Interval(start_distance, start_distance + button_size),
            angle=Interval(center_angle - angle / 2, center_angle + angle / 2)
        )

    for i in range(8):
        dist = get_sensor_distance(SensorGroup.A)
        angle = get_sensor_angle_horizontal(Sensor.A1 + i)
        l_angle = angle + GROUP_A_ANGLE_WIDTH
        r_angle = angle - GROUP_A_ANGLE_WIDTH
        b_dist = dist - GROUP_A_BOT_L_DIST
        bm_dist = dist - GROUP_A_BOT_MID_DIST
        t_dist = dist + GROUP_A_TOP_DIST
        Hitboxes.group_a[i] = PolygonHitBox.new(layout_ring_pos(angle, dist), Array(
            layout_ring_pos(l_angle, b_dist),
            layout_ring_pos(l_angle, t_dist),
            layout_ring_pos(angle, t_dist),
            layout_ring_pos(r_angle, t_dist),
            layout_ring_pos(r_angle, b_dist),
            layout_ring_pos(angle - GROUP_A_BOT_MID_ANGLE, bm_dist),
            layout_ring_pos(angle + GROUP_A_BOT_MID_ANGLE, bm_dist),
        ))

    for i in range(8):
        dist = get_sensor_distance(SensorGroup.B)
        angle = get_sensor_angle_horizontal(Sensor.B1 + i)
        mid_dist = dist + GROUP_B_MID_DIST
        top_dist = dist + GROUP_B_TOP_DIST
        bot_dist = dist - GROUP_B_BOT_DIST
        Hitboxes.group_b[i] = PolygonHitBox.new(layout_ring_pos(angle, dist), Array(
            layout_ring_pos(angle + GROUP_B_MID_ANGLE, mid_dist),
            layout_ring_pos(angle + GROUP_B_TOP_ANGLE, top_dist),
            layout_ring_pos(angle - GROUP_B_TOP_ANGLE, top_dist),
            layout_ring_pos(angle - GROUP_B_MID_ANGLE, mid_dist),
            layout_ring_pos(angle - GROUP_B_BOT_ANGLE, bot_dist),
            layout_ring_pos(angle, dist - GROUP_B_TIP_DIST),
            layout_ring_pos(angle + GROUP_B_BOT_ANGLE, bot_dist),
        ))

    center_size = layout_px_size(GROUP_C_HITBOX_SIZE)
    Hitboxes.group_c = CircTrapHitBox(
        center=Layout.ring_center,
        distance=Interval(0, center_size),
        angle=Interval(-pi, pi)
    )

    for i in range(8):
        dist = get_sensor_distance(SensorGroup.D)
        angle = get_sensor_angle_horizontal(Sensor.D1 + i)
        l_angle = angle + GROUP_D_ANGLE_WIDTH
        r_angle = angle - GROUP_D_ANGLE_WIDTH
        bl_dist = dist - GROUP_D_BOT_L_DIST
        br_dist = dist - GROUP_D_BOT_R_DIST
        t_dist = dist + GROUP_D_TOP_DIST
        Hitboxes.group_d[i] = PolygonHitBox.new(layout_ring_pos(angle, dist), Array(
            layout_ring_pos(l_angle, bl_dist),
            layout_ring_pos(l_angle, t_dist),
            layout_ring_pos(angle, t_dist),
            layout_ring_pos(r_angle, t_dist),
            layout_ring_pos(r_angle, bl_dist),
            layout_ring_pos(angle, br_dist),
        ))

    for i in range(8):
        dist = get_sensor_distance(SensorGroup.E)
        angle = get_sensor_angle_horizontal(Sensor.E1 + i)
        center = layout_ring_pos(angle, dist)
        size = layout_px_size(GROUP_E_HITBOX_SIZE)
        rotate = ((i + 1) % 2) * pi / 4
        quad = Rect.from_center(center, Vec2(size, size)).as_quad().rotate_centered(rotate)
        Hitboxes.group_e[i] = NQuadHitBox(
            quads = Array(quad)
        )


def in_bounds(point: Vec2):
    max_distance = Hitboxes.button[0].distance.end
    return get_dist_from_center(point) <= max_distance