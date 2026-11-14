"""Build a Minimai particle pack in ``resources/particles/<name>`` from a folder or zip file of sprites.

Usage: python -m minimai.tools.particle_pack <name> <source> (or ``python main.py particle ...``).
Needs Pillow (``uv sync --extra tools``).

Every effect the engine plays draws a **rig**: a tree of nodes, each a transform animated by keys, maybe
with a sprite. The defaults are in ``tools/defaults/particle.toml``; the source's ``pack.toml`` is merged
over them. The format is in docs/packs.md.

A Sonolus particle moves in a straight line (or along one ease) and can't follow a parent's rotation, so
each sprite becomes a chain of particles, one per stretch between keys, with long turns cut into short
ones. Random values become Sonolus' per-instance random values (``r``, and ``sinr`` / ``cosr`` for a full
turn).
"""

from __future__ import annotations

import argparse
import io
import json
import math
import tomllib
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING

from minimai.lib.layout import (
    HOLD_EFFECT_SIZE,
    SKIN_RING_RADIUS_PX,
    TAP_EFFECT_SIZE,
    TOUCH_EFFECT_SIZE,
)
from minimai.lib.particle import (
    HOLD_DURATION,
    TAP_GOOD_DURATION,
    TAP_GREAT_DURATION,
    TAP_PERFECT_DURATION,
    TOUCH_DURATION,
)
from minimai.tools.imaging import build_sheet
from minimai.tools.pack_config import (
    RESOURCES_DIR,
    get_item_info,
    item_json,
    load_config,
    merged,
    parse_color,
    resolve,
    resolved_params,
)
from minimai.tools.schema import ParticleConfig, ParticleSprite, RigNode
from minimai.tools.sprite_recipe import SourceFiles, build_sprite, check_recipe, combined_recipe, report_missing

# Pillow is an optional extra (uv sync --extra tools): the image functions import it when they run.
if TYPE_CHECKING:
    from PIL import Image

PARTICLES_DIR = RESOURCES_DIR / "particles"
DEFAULTS_PATH = Path(__file__).parent / "defaults" / "particle.toml"


def skin_px(size: float) -> float:
    """Ring units (lib/layout.py) to skin px."""
    return size * SKIN_RING_RADIUS_PX


# Every effect the engine spawns (lib/particle.py): how long it plays, in seconds, and the side of the
# square it's spawned on, in skin px. The hold effects loop.
ENGINE_EFFECTS: dict[str, tuple[float, float]] = {
    "Mai Tap Perfect": (TAP_PERFECT_DURATION, skin_px(TAP_EFFECT_SIZE)),
    "Mai Tap Great": (TAP_GREAT_DURATION, skin_px(TAP_EFFECT_SIZE)),
    "Mai Tap Good": (TAP_GOOD_DURATION, skin_px(TAP_EFFECT_SIZE)),
    "Mai Break Perfect": (TAP_PERFECT_DURATION, skin_px(TAP_EFFECT_SIZE)),
    "Mai Break Great": (TAP_PERFECT_DURATION, skin_px(TAP_EFFECT_SIZE)),
    "Mai Break Good": (TAP_PERFECT_DURATION, skin_px(TAP_EFFECT_SIZE)),
    **{f"Mai Touch {grade}": (TOUCH_DURATION, skin_px(TOUCH_EFFECT_SIZE)) for grade in ("Perfect", "Great", "Good")},
    **{
        f"Mai Hold {grade}": (HOLD_DURATION, skin_px(HOLD_EFFECT_SIZE))
        for grade in ("Perfect", "Great", "Good", "Miss")
    },
}

NODE_KEYS = {
    *("pos", "rot", "scale", "sprite", "size", "alpha", "color", "children"),
    *("repeat", "count", "rig", "args", "params"),
}
EFFECT_KEYS = {"rig", "args", "loop_copies", "skip"}
MAX_RANDOMS = 8
# Rigs referring to rigs deeper than this are taken for a loop.
MAX_RIG_DEPTH = 16


class RigError(Exception):
    """A rig that can't be built or can't become particles; the message names where."""


# ==== Eases =======================================================================================
# Sonolus' eases (as Sonolus Studio draws them): progress 0..1 -> 0..1.

BACK = 1.70158


def _out(ease: Callable[[float], float]) -> Callable[[float], float]:
    return lambda x: 1 - ease(1 - x)


def _in_out(ease: Callable[[float], float]) -> Callable[[float], float]:
    return lambda x: ease(2 * x) / 2 if x < 0.5 else 1 - ease(2 - 2 * x) / 2


def _out_in(ease: Callable[[float], float]) -> Callable[[float], float]:
    out = _out(ease)
    return lambda x: out(2 * x) / 2 if x < 0.5 else 0.5 + ease(2 * x - 1) / 2


def _in_elastic(x: float) -> float:
    if x in (0, 1):
        return x
    return -(2 ** (10 * x - 10)) * math.sin((x * 10 - 10.75) * 2 * math.pi / 3)


EASE_INS: dict[str, Callable[[float], float]] = {
    "Sine": lambda x: 1 - math.cos(x * math.pi / 2),
    "Quad": lambda x: x**2,
    "Cubic": lambda x: x**3,
    "Quart": lambda x: x**4,
    "Quint": lambda x: x**5,
    "Expo": lambda x: 0.0 if x == 0 else 2 ** (10 * x - 10),
    "Circ": lambda x: 1 - math.sqrt(max(0.0, 1 - x * x)),
    "Back": lambda x: (BACK + 1) * x**3 - BACK * x**2,
    "Elastic": _in_elastic,
}
EASES: dict[str, Callable[[float], float]] = {
    "linear": lambda x: x,
    "none": lambda x: 1.0 if x == 1 else 0.0,
    **{f"in{name}": ease for name, ease in EASE_INS.items()},
    **{f"out{name}": _out(ease) for name, ease in EASE_INS.items()},
    **{f"inOut{name}": _in_out(ease) for name, ease in EASE_INS.items()},
    **{f"outIn{name}": _out_in(ease) for name, ease in EASE_INS.items()},
    # As Sonolus has them: their second halves don't start at exactly 0.5.
    "outInExpo": lambda x: (
        x if x in (0, 1) else 0.5 - 0.5 * 2 ** (-20 * x) if x < 0.5 else 0.5 + 0.5 * 2 ** (20 * x - 20)
    ),
    "outInElastic": lambda x: (
        x
        if x in (0, 1)
        else _out(_in_elastic)(2 * x) / 2
        if x < 0.5
        else 0.5 - 0.5 * 2 ** (20 * x - 20) * math.sin((20 * x - 20.75) * 2 * math.pi / 3)
    ),
}


# ==== Values and tracks ===========================================================================


@dataclass(eq=False)
class Random:
    """A value drawn between ``low`` and ``high`` once per spawn (per group instance), from Sonolus' random
    value ``index`` (1-8). ``shared`` is the index a config asked for, so values can share one draw."""

    low: float
    high: float
    shared: int | None = None
    index: int = 0

    def value(self, randoms: Mapping[int, float]) -> float:
        return self.low + (self.high - self.low) * randoms.get(self.index, 0.0)


type Scalar = float | Random
type Randoms = Mapping[int, float]
# No random values drawn: each is its low end.
NO_RANDOMS: Randoms = MappingProxyType({})


def value_of(scalar: Scalar, randoms: Randoms) -> float:
    return scalar.value(randoms) if isinstance(scalar, Random) else scalar


def parse_scalar(raw, where: str) -> Scalar:
    if isinstance(raw, bool):
        raise RigError(f"{where}: expected a number, not {raw!r}")
    if isinstance(raw, int | float):
        return float(raw)
    if isinstance(raw, Mapping) and "random" in raw:
        low_high = raw["random"]
        if not (isinstance(low_high, list) and len(low_high) == 2):
            raise RigError(f"{where}: random must be [low, high], not {low_high!r}")
        low, high = (parse_scalar(part, where) for part in low_high)
        if isinstance(low, Random) or isinstance(high, Random):
            raise RigError(f"{where}: a random value's ends must be numbers")
        shared = raw.get("r")
        if shared is not None and (not isinstance(shared, int) or not 1 <= shared <= MAX_RANDOMS):
            raise RigError(f"{where}: r must be 1-{MAX_RANDOMS}, not {shared!r}")
        unknown = set(raw) - {"random", "r"}
        if unknown:
            raise RigError(f"{where}: unknown keys in a random value: {', '.join(sorted(unknown))}")
        return Random(low, high, shared)
    raise RigError(f"{where}: expected a number or {{ random = [low, high] }}, not {raw!r}")


def parse_pair(raw, where: str) -> tuple[Scalar, Scalar]:
    if not (isinstance(raw, list) and len(raw) == 2):
        raise RigError(f"{where}: expected [x, y], not {raw!r}")
    return parse_scalar(raw[0], where), parse_scalar(raw[1], where)


def parse_rgb(raw, where: str) -> tuple[float, float, float]:
    try:
        return parse_color(raw)
    except (TypeError, ValueError) as error:
        raise RigError(f"{where}: expected a colour (\"#rrggbb\" or [r, g, b]), not {raw!r}") from error


@dataclass
class Key:
    time: float
    value: object
    # How the value moves from this key to the next.
    ease: str = "linear"


class Track:
    """A value over time: keys, eased from each to the next and held before the first and after the last.
    Values are a scalar, a pair of scalars, or an RGB colour."""

    def __init__(self, keys: list[Key]):
        self.keys = sorted(keys, key=lambda key: key.time)

    @classmethod
    def constant(cls, value) -> Track:
        return cls([Key(0.0, value)])

    @staticmethod
    def evaluate(value, randoms: Randoms):
        if isinstance(value, tuple):
            return tuple(value_of(part, randoms) for part in value)
        return value_of(value, randoms)

    def at(self, t: float, randoms: Randoms = NO_RANDOMS):
        keys = self.keys
        if t <= keys[0].time:
            return self.evaluate(keys[0].value, randoms)
        for k0, k1 in pairwise(keys):
            if t <= k1.time:
                x = 0 if k1.time == k0.time else (t - k0.time) / (k1.time - k0.time)
                v0, v1 = self.evaluate(k0.value, randoms), self.evaluate(k1.value, randoms)
                if k0.ease != "linear":
                    x = EASES[k0.ease](x)
                if isinstance(v0, tuple):
                    return tuple(a + (b - a) * x for a, b in zip(v0, v1))
                return v0 + (v1 - v0) * x
        return self.evaluate(keys[-1].value, randoms)

    @property
    def times(self) -> list[float]:
        return [key.time for key in self.keys]

    def randoms(self) -> Iterator[Random]:
        for key in self.keys:
            for part in key.value if isinstance(key.value, tuple) else (key.value,):
                if isinstance(part, Random):
                    yield part

    def changes(self, t0: float, t1: float, samples: list[Randoms]) -> bool:
        return any(t0 < t < t1 for t in self.times) or any(self.at(t0, r) != self.at(t1, r) for r in samples)

    def ease_between(self, t0: float, t1: float) -> str:
        """The ease of the key stretch holding [t0, t1] (no key strictly inside); linear outside the keys."""
        for k0, k1 in pairwise(self.keys):
            if k0.time <= t0 and t1 <= k1.time:
                return k0.ease
        return "linear"


def parse_track(raw, parse: Callable[[object, str], object], where: str) -> Track:
    """A constant, or keys ``[[time, value], [time, value, ease], ...]``."""
    if not (isinstance(raw, list) and raw and isinstance(raw[0], list)):
        return Track.constant(parse(raw, where))
    keys = []
    for i, key in enumerate(raw):
        here = f"{where} key {i + 1}"
        timed = isinstance(key, list) and len(key) in (2, 3) and isinstance(key[0], int | float)
        if not timed or isinstance(key[0], bool):
            raise RigError(f"{here}: expected [time, value] or [time, value, ease], not {key!r}")
        ease = key[2] if len(key) == 3 else "linear"
        if ease not in EASES:
            raise RigError(
                f"{here}: unknown ease {ease!r}; one of linear, none, or in/out/inOut/outIn + "
                "Sine, Quad, Cubic, Quart, Quint, Expo, Circ, Back, Elastic"
            )
        keys.append(Key(float(key[0]), parse(key[1], here), ease))
    return Track(keys)


# ==== Rigs ========================================================================================


@dataclass(eq=False)
class Node:
    """A transform (position, then rotation in degrees, then uniform scale, applied to its children too),
    and maybe a sprite ``size`` skin px wide and high drawn at it."""

    where: str
    pos: Track = field(default_factory=lambda: Track.constant((0.0, 0.0)))
    rot: Track = field(default_factory=lambda: Track.constant(0.0))
    scale: Track = field(default_factory=lambda: Track.constant(1.0))
    sprite: str | None = None
    size: tuple[Scalar, Scalar] = (0.0, 0.0)
    alpha: Track = field(default_factory=lambda: Track.constant(1.0))
    color: Track = field(default_factory=lambda: Track.constant((1.0, 1.0, 1.0)))
    children: list[Node] = field(default_factory=list)
    # A repeat copy's turn about the parent, in degrees; with orient off it moves the copy's position (and
    # its children's) but not their angle.
    turn: float = 0.0
    orient: bool = True
    # Spawned this many times, each with its own random values (its own particle group).
    count: int | None = None

    def randoms(self) -> Iterator[Random]:
        for track in (self.pos, self.rot, self.scale, self.alpha):
            yield from track.randoms()
        yield from (part for part in self.size if isinstance(part, Random))


class RigParser:
    """Rig tables (from the config) to node trees. ``"$name"`` values are the rig's params: the config's
    ``[params]``, the rig's own ``params`` (defaults) and the args it's drawn with, in that order."""

    def __init__(self, rigs: Mapping[str, RigNode], params: Mapping):
        self.rigs = rigs
        self.params = params
        self.warned: set[str] = set()

    def rig(self, name, args: Mapping, where: str, depth: int = 0) -> list[Node]:
        if not isinstance(name, str) or name not in self.rigs:
            raise RigError(f"{where}: no rig {name!r} (the rigs: {', '.join(self.rigs)})")
        if depth > MAX_RIG_DEPTH:
            raise RigError(f"{where}: rigs draw each other in a loop")
        table = self.rigs[name]
        try:
            defaults = resolve(table.get("params", {}), self.params)
        except ValueError as error:
            raise RigError(f"rigs.{name}.params: {error}") from error
        return self.nodes(table, {**self.params, **defaults, **args}, f"rigs.{name}", depth)

    def nodes(self, table: Mapping, scope: Mapping, where: str, depth: int) -> list[Node]:
        """The node (or its repeat copies) for a table."""
        if not isinstance(table, Mapping):
            raise RigError(f"{where}: a node must be a table, not {table!r}")
        unknown = sorted(set(table) - NODE_KEYS)
        if unknown and where not in self.warned:
            self.warned.add(where)
            print(f"{where}: unknown keys (ignored): {', '.join(unknown)}")

        def get(key: str, default=None):
            if key not in table:
                return default
            try:
                return resolve(table[key], scope)
            except ValueError as error:
                raise RigError(f"{where}.{key}: {error}") from error

        repeat = get("repeat", {})
        if not isinstance(repeat, Mapping) or not repeat.keys() <= {"count", "rot", "start", "orient"}:
            raise RigError(f"{where}.repeat: expected {{ count, rot, start, orient }}, not {repeat!r}")
        count = repeat.get("count", 1)
        if not isinstance(count, int) or count < 1:
            raise RigError(f"{where}.repeat: count must be a whole number of at least 1, not {count!r}")
        step = float(repeat.get("rot", 360 / count))
        start = float(repeat.get("start", 0))
        group_count = get("count")
        if group_count is not None and (not isinstance(group_count, int) or group_count < 1):
            raise RigError(f"{where}.count: must be a whole number of at least 1, not {group_count!r}")
        size = get("size", 0)
        size_where = f"{where}.size"
        copies = []
        for copy in range(count):
            # Parsed again for each copy, so each draws its own random values.
            node = Node(
                where=where if count == 1 else f"{where} (copy {copy + 1})",
                pos=parse_track(get("pos", [0, 0]), parse_pair, f"{where}.pos"),
                rot=parse_track(get("rot", 0), parse_scalar, f"{where}.rot"),
                scale=parse_track(get("scale", 1), parse_scalar, f"{where}.scale"),
                sprite=get("sprite"),
                size=parse_pair(size, size_where) if isinstance(size, list) else (parse_scalar(size, size_where),) * 2,
                alpha=parse_track(get("alpha", 1), parse_scalar, f"{where}.alpha"),
                color=parse_track(get("color", "#ffffff"), parse_rgb, f"{where}.color"),
                turn=start + step * copy,
                orient=bool(repeat.get("orient", True)),
                count=group_count,
            )
            if node.sprite is not None and not isinstance(node.sprite, str):
                raise RigError(f"{where}.sprite: expected a sprite id, not {node.sprite!r}")
            if "rig" in table:
                args = get("args", {})
                if not isinstance(args, Mapping):
                    raise RigError(f"{where}.args: expected a table, not {args!r}")
                node.children += self.rig(get("rig"), args, where, depth + 1)
            for i, child in enumerate(table.get("children", [])):
                node.children += self.nodes(child, scope, f"{where}.children[{i}]", depth)
            copies.append(node)
        return copies


def sprite_chains(node: Node, chain: tuple[Node, ...] = ()) -> Iterator[tuple[Node, ...]]:
    """The chain from the root to every node with a sprite, in drawing order."""
    chain = (*chain, node)
    if node.sprite is not None:
        yield chain
    for child in node.children:
        yield from sprite_chains(child, chain)


# ==== Compiling ===================================================================================
# A sprite's state, in the spawn quad's space (its half side is 1): x, y, half width, half height,
# rotation in radians, alpha.

PROPERTIES = ("x", "y", "w", "h", "r", "a")
type State = tuple[float, float, float, float, float, float]
# c + sum of coefficient x random value, by Sonolus expression key ("c", "r1", "sinr1", "cosr1", ...).
type Expression = dict[str, float]


@dataclass
class World:
    x: float
    y: float
    rot: float
    scale: float


def world_at(chain: tuple[Node, ...], t: float, randoms: Randoms = NO_RANDOMS) -> World:
    x = y = rot = 0.0
    # Turns from repeat copies that don't orient: they turn positions but not angles.
    position_turn = 0.0
    scale = 1.0
    for node in chain:
        if node.orient:
            rot += node.turn
        else:
            position_turn += node.turn
        px, py = node.pos.at(t, randoms)
        angle = math.radians(rot + position_turn)
        c, s = math.cos(angle), math.sin(angle)
        x, y = x + scale * (c * px - s * py), y + scale * (s * px + c * py)
        rot += node.rot.at(t, randoms)
        scale *= node.scale.at(t, randoms)
    return World(x, y, rot, scale)


def sprite_state(chain: tuple[Node, ...], t: float, half: float, randoms: Randoms = NO_RANDOMS) -> State:
    sprite = chain[-1]
    world = world_at(chain, t, randoms)
    w, h = (value_of(part, randoms) * world.scale / 2 / half for part in sprite.size)
    return (world.x / half, world.y / half, w, h, math.radians(world.rot), sprite.alpha.at(t, randoms))


def random_samples(indexes: list[int]) -> list[dict[int, float]]:
    """Random values to check a chain at: none drawn, and a few spread out."""
    if not indexes:
        return [{}]
    return [{}, *({i: (offset + 0.37 * i) % 1 for i in indexes} for offset in (0.13, 0.58, 0.91))]


def fit_expressions(state: Callable[[Randoms], State], indexes: list[int], where: str) -> list[Expression]:
    """Each property of a state that depends on random values, as a Sonolus expression: a constant plus,
    for each random value r, a·r + b·cos(2πr) + c·sin(2πr). Checked against the state, since products of
    random values (or a turn short of a full one) can't be written so."""
    base = state({})
    expressions: list[Expression] = [{"c": value} for value in base]
    for i in indexes:
        quarter, half, three_quarters = state({i: 0.25}), state({i: 0.5}), state({i: 0.75})
        for expression, v0, v1, v2, v3 in zip(expressions, base, quarter, half, three_quarters):
            # g(r) = v(r) - v(0) = a·r + b·(cos 2πr - 1) + c·sin 2πr, from r = 1/4, 1/2 and 3/4.
            g1, g2, g3 = v1 - v0, v2 - v0, v3 - v0
            a = 2 * (g1 + g3 - g2)
            b = (a / 2 - g2) / 2
            c = (g1 - g3 + a / 2) / 2
            for key, coefficient in ((f"r{i}", a), (f"cosr{i}", b), (f"sinr{i}", c)):
                if abs(coefficient) > 1e-9:
                    expression[key] = coefficient
            expression["c"] -= b if abs(b) > 1e-9 else 0.0
    checks = [{i: x} for i in indexes for x in (0.1, 0.6, 0.85)] + random_samples(indexes)[1:]
    for randoms in checks:
        for name, expression, actual in zip(PROPERTIES, expressions, state(randoms)):
            if abs(evaluate(expression, randoms) - actual) > 1e-6 * max(1.0, abs(actual)):
                raise RigError(
                    f"{where}: its {name} can't follow its random values. A particle adds random values (and, "
                    "for a turn of a whole 360°, their sine and cosine), but can't multiply them: a random "
                    "rotation must be a whole turn to move children, and two random values can't scale each other"
                )
    return expressions


def evaluate(expression: Expression, randoms: Randoms) -> float:
    total = 0.0
    for key, coefficient in expression.items():
        if key == "c":
            total += coefficient
            continue
        kind, index = key.rstrip("0123456789"), int(key.lstrip("sincor"))
        r = randoms.get(index, 0.0)
        total += coefficient * {"r": r, "sinr": math.sin(2 * math.pi * r), "cosr": math.cos(2 * math.pi * r)}[kind]
    return total


def expression_json(expression: Expression) -> dict[str, float]:
    result = {}
    for key, coefficient in expression.items():
        coefficient = round(coefficient, 5)
        if coefficient:
            result[key] = coefficient
    return result


def color_hex(rgb) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in rgb)


@dataclass
class Segment:
    start: float
    end: float
    # Each property's ease, or None for linear.
    eases: tuple[str, ...] | None
    color: str


def fitted_eases(
    chain: tuple[Node, ...], t0: float, t1: float, half: float, candidates: list[str], samples: list[Randoms]
) -> tuple[str, ...] | None:
    """For each property, the first candidate ease it follows from t0 to t1; None when one follows none."""
    steps = [i / 8 for i in range(1, 8)]
    ends = [(sprite_state(chain, t0, half, r), sprite_state(chain, t1, half, r)) for r in samples]
    middles = [[sprite_state(chain, t0 + (t1 - t0) * u, half, r) for u in steps] for r in samples]
    eases = []
    for p in range(len(PROPERTIES)):
        for ease in candidates:
            function = EASES[ease]
            if all(
                abs(start[p] + (end[p] - start[p]) * function(u) - middle[p]) < 1e-4
                for (start, end), row in zip(ends, middles)
                for u, middle in zip(steps, row)
            ):
                eases.append(ease)
                break
        else:
            return None
    return tuple(eases)


def chain_segments(
    chain: tuple[Node, ...], duration: float, half: float, build: Mapping, samples: list[Randoms]
) -> list[Segment]:
    """The stretches of a sprite's life, each one particle: between keys, with long turns, colour changes
    and eases no particle can follow cut into pieces."""
    sprite = chain[-1]
    motion = [track for node in chain for track in (node.pos, node.rot, node.scale)] + [sprite.alpha]
    times = sorted({0.0, duration} | {t for track in (*motion, sprite.color) for t in track.times if 0 < t < duration})
    segments = []
    for t0, t1 in pairwise(times):
        turn = max(
            abs(world_at(chain[: i + 1], t1, r).rot - world_at(chain[: i + 1], t0, r).rot)
            for r in samples
            for i in range(len(chain))
        )
        pieces = max(1, math.ceil(turn / build["max_segment_turn"]))
        if sprite.color.changes(t0, t1, [{}]):
            pieces = max(pieces, math.ceil((t1 - t0) / build["color_step"]))
        eases = sorted({track.ease_between(t0, t1) for track in motion if track.changes(t0, t1, samples)} - {"linear"})
        if eases:
            if pieces == 1:
                fitted = fitted_eases(chain, t0, t1, half, ["linear", *eases], samples)
                if fitted is not None:
                    color = color_hex(sprite.color.at((t0 + t1) / 2))
                    segments.append(Segment(t0, t1, None if set(fitted) == {"linear"} else fitted, color))
                    continue
            pieces = max(pieces, math.ceil((t1 - t0) / build["ease_step"]))
        bounds = [t0] + [t0 + (t1 - t0) * (i + 1) / pieces for i in range(pieces)]
        for a, b in pairwise(bounds):
            segments.append(Segment(a, b, None, color_hex(sprite.color.at((a + b) / 2))))
    return segments


def straight(start: list[Expression], middle: list[Expression], end: list[Expression], x: float) -> bool:
    """Whether ``middle`` is on the line from ``start`` to ``end``, ``x`` of the way along."""
    for s, m, e in zip(start, middle, end):
        for key in s.keys() | m.keys() | e.keys():
            a, b = s.get(key, 0.0), e.get(key, 0.0)
            if abs(a + (b - a) * x - m.get(key, 0.0)) >= 1e-4:
                return False
    return True


def merge_segments(segments: list[Segment], states: Callable[[float], list[Expression]]) -> list[Segment]:
    """Back-to-back linear segments of one colour that make one straight line, as one."""
    merged_segments: list[Segment] = []
    for segment in segments:
        if merged_segments:
            last = merged_segments[-1]
            if last.eases is None and segment.eases is None and last.color == segment.color:
                x = (segment.start - last.start) / (segment.end - last.start)
                if straight(states(last.start), states(segment.start), states(segment.end), x):
                    last.end = segment.end
                    continue
        merged_segments.append(Segment(segment.start, segment.end, segment.eases, segment.color))
    return merged_segments


def invisible(start: list[Expression], end: list[Expression]) -> bool:
    """Whether a particle never shows: no alpha, or no width or height, at both ends (and nothing random)."""
    def constant(expression: Expression) -> float | None:
        return expression.get("c", 0.0) if expression.keys() <= {"c"} else None

    def gone(p: int, test: Callable[[float], bool]) -> bool:
        values = (constant(start[p]), constant(end[p]))
        return all(value is not None and test(value) for value in values)

    return gone(5, lambda a: a <= 0.001) or gone(2, lambda w: w == 0) or gone(3, lambda h: h == 0)


@dataclass
class Effect:
    name: str
    duration: float
    # The spawn quad's side, in skin px.
    quad_size: float
    root: list[Node]
    # A looped effect: copies of every particle, this many, evenly offset over the loop.
    loop_copies: int = 1


def effect_groups(effect: Effect, sprite_ids: Mapping[str, int], build: Mapping) -> list[dict]:
    """The effect's particle groups: one for the rig, and one for each node with a count."""
    half = effect.quad_size / 2
    # Group (the node with a count, or None) -> its chains.
    groups: dict[Node | None, list[tuple[Node, ...]]] = {None: []}
    for root in effect.root:
        for chain in sprite_chains(root):
            counted = [i for i, node in enumerate(chain) if node.count is not None]
            if len(counted) > 1:
                raise RigError(f"{chain[counted[1]].where}: a node with a count can't be inside another")
            if counted and any(True for node in chain[: counted[0]] for _ in node.randoms()):
                raise RigError(f"{chain[counted[0]].where}: a node with a count can't be inside random values")
            groups.setdefault(chain[counted[0]] if counted else None, []).append(chain)

    result = []
    for group, chains in groups.items():
        assign_random_indexes(chains)
        particles = []
        for chain in chains:
            particles += chain_particles(chain, effect, half, sprite_ids, build)
        if particles:
            result.append({"count": 1 if group is None else group.count, "particles": particles})
    return result


def assign_random_indexes(chains: list[tuple[Node, ...]]):
    """Give each random value of a group a Sonolus random value (1-8): the one a config shared, else a free one."""
    values = list({id(value): value for chain in chains for node in chain for value in node.randoms()}.values())
    taken = {value.shared for value in values if value.shared is not None}
    free = (i for i in range(1, MAX_RANDOMS + 1) if i not in taken)
    for value in values:
        if value.shared is not None:
            value.index = value.shared
            continue
        index = next(free, None)
        if index is None:
            raise RigError(
                f"more than {MAX_RANDOMS} random values in one particle group; share some with r = 1-{MAX_RANDOMS}"
            )
        value.index = index


def chain_particles(
    chain: tuple[Node, ...], effect: Effect, half: float, sprite_ids: Mapping[str, int], build: Mapping
) -> list[dict]:
    sprite = chain[-1]
    indexes = sorted({value.index for node in chain for value in node.randoms()})
    samples = random_samples(indexes)
    cache: dict[float, list[Expression]] = {}

    def states(t: float) -> list[Expression]:
        if t not in cache:
            cache[t] = fit_expressions(lambda randoms: sprite_state(chain, t, half, randoms), indexes, sprite.where)
        return cache[t]

    particles = []
    for segment in merge_segments(chain_segments(chain, effect.duration, half, build, samples), states):
        start, end = states(segment.start), states(segment.end)
        if invisible(start, end):
            continue
        eases = segment.eases or ("linear",) * len(PROPERTIES)
        for copy in range(effect.loop_copies):
            offset = copy / effect.loop_copies
            # Rounded ends, so back-to-back particles leave no gap.
            begin = round(segment.start / effect.duration + offset, 5)
            finish = round(segment.end / effect.duration + offset, 5)
            wrap = math.floor(begin)
            particle = {
                "sprite": sprite_ids[sprite.sprite],
                "color": segment.color,
                "start": round(begin - wrap, 5),
                "duration": round(finish - begin, 5),
            }
            for p, name in enumerate(PROPERTIES):
                particle[name] = {"from": expression_json(start[p]), "to": expression_json(end[p]), "ease": eases[p]}
            particles.append(particle)
    return particles


# ==== Packing =====================================================================================

IDENTITY_TRANSFORM = {f"{axis}{i}": {f"{axis}{i}": 1} for i in range(1, 5) for axis in "xy"}


def load_defaults() -> ParticleConfig:
    with DEFAULTS_PATH.open("rb") as file:
        defaults = tomllib.load(file)
    names = set(defaults["effects"])
    if names != set(ENGINE_EFFECTS):
        raise SystemExit(
            f"{DEFAULTS_PATH.name} is out of step with lib/particle.py: "
            f"missing {sorted(set(ENGINE_EFFECTS) - names)}, unknown {sorted(names - set(ENGINE_EFFECTS))}"
        )
    return defaults


SPRITE_KEYS = set(ParticleSprite.__annotations__)


def build_sprites(
    files: SourceFiles, defaults: Mapping, entries: Mapping, params: Mapping
) -> tuple[dict[str, Image.Image], dict[str, str], dict[str, dict]]:
    """Each sprite id's image, from its recipe (as the skin's: sprite_recipe), the fallbacks, and the recipes
    of the sprites with no image."""
    images: dict[str, Image.Image] = {}
    fallbacks: dict[str, str] = {}
    missing: dict[str, dict] = {}
    for sprite in dict.fromkeys([*defaults, *entries]):
        recipe = combined_recipe(defaults.get(sprite), files.exact(sprite), entries.get(sprite), ("skip", "fallback"))
        check_recipe(sprite, recipe, SPRITE_KEYS)
        fallback = recipe.pop("fallback", None)
        if fallback:
            fallbacks[sprite] = fallback
        if recipe.get("skip"):
            continue
        try:
            recipe = resolve(recipe, params)
            image = build_sprite(sprite, recipe, files)
        except Exception as error:
            print(f"{sprite}: {error}")
            image = None
        if image is None:
            missing[sprite] = recipe
        else:
            images[sprite] = image
    return images, fallbacks, missing


def sprite_ids_for(found: Iterable[str], fallbacks: Mapping[str, str]) -> dict[str, int]:
    ids = {sprite: i for i, sprite in enumerate(found)}
    for sprite, fallback in fallbacks.items():
        seen = {sprite}
        while fallback not in ids and fallback in fallbacks and fallback not in seen:
            seen.add(fallback)
            fallback = fallbacks[fallback]
        if sprite not in ids and fallback in ids:
            ids[sprite] = ids[fallback]
    return ids


def build_effects(config: ParticleConfig, sprite_ids: Mapping[str, int]) -> tuple[list[dict], list[str]]:
    """The effects (for data.json), and the names of those left out for missing sprites."""
    parser = RigParser(config.get("rigs", {}), config.get("params", {}))
    effects = []
    left_out = []
    known = set(config.get("sprites", {}))
    for name, entry in config["effects"].items():
        if name not in ENGINE_EFFECTS:
            raise SystemExit(f"[effects.\"{name}\"]: not an effect the engine plays ({', '.join(ENGINE_EFFECTS)})")
        unknown = sorted(set(entry) - EFFECT_KEYS)
        if unknown:
            print(f"[effects.\"{name}\"]: unknown keys (ignored): {', '.join(unknown)}")
        if entry.get("skip"):
            continue
        duration, quad_size = ENGINE_EFFECTS[name]
        try:
            args = resolve(entry.get("args", {}), config.get("params", {}))
            root = parser.rig(entry.get("rig"), args, "rig")
            needs = {chain[-1].sprite for node in root for chain in sprite_chains(node)}
            strangers = sorted(needs - known)
            if strangers:
                raise RigError(f"sprites not in [sprites]: {', '.join(strangers)}")
            if not needs <= sprite_ids.keys():
                left_out.append(name)
                continue
            effect = Effect(name, duration, quad_size, root, int(entry.get("loop_copies", 1)))
            groups = effect_groups(effect, sprite_ids, config["build"])
        except (RigError, ValueError) as error:
            raise SystemExit(f"[effects.\"{name}\"]: {error}") from error
        effects.append({"name": name, "transform": IDENTITY_TRANSFORM, "groups": groups})
    return effects, left_out


def build_thumbnail(image: Image.Image) -> Image.Image:
    from PIL import Image

    thumbnail = Image.new("RGBA", (128, 128), (32, 32, 40, 255))
    preview = image.copy()
    preview.thumbnail((96, 96))
    thumbnail.alpha_composite(preview, ((128 - preview.width) // 2, (128 - preview.height) // 2))
    return thumbnail


def pack_particle(name: str, source: Path, *, particles_dir: Path = PARTICLES_DIR) -> Path:
    """Build the pack from ``source`` (folder or zip) and return its folder."""
    try:
        from PIL import Image
    except ImportError as error:
        raise SystemExit("Pillow is needed: uv sync --extra tools") from error

    defaults = load_defaults()
    source_config: ParticleConfig = load_config(source)
    config: ParticleConfig = merged(defaults, source_config)
    config["params"] = resolved_params(config.get("params", {}))
    info = get_item_info(name, source, config)
    files = SourceFiles(source, config.get("files", {}))
    found, fallbacks, missing = build_sprites(
        files, defaults["sprites"], source_config.get("sprites", {}), config.get("params", {})
    )
    # The ones with a fallback aren't missed.
    report_missing({sprite: recipe for sprite, recipe in missing.items() if sprite not in fallbacks})
    if not found:
        raise SystemExit(f"No sprites in {source}")
    sprite_ids = sprite_ids_for(found, fallbacks)
    effects, left_out = build_effects(config, sprite_ids)
    if left_out:
        print(f"Left out for missing sprites (the engine falls back to standard effects): {', '.join(left_out)}")

    images = list(found.values())
    texture = config["texture"]
    try:
        sheet, origins = build_sheet(images, int(texture["padding"]), int(texture["max_size"]))
    except ValueError as error:
        raise SystemExit(f"{error.args[0].capitalize()}; raise [texture] max_size or scale them down") from error
    data = {
        "width": sheet.width,
        "height": sheet.height,
        "interpolation": bool(texture["interpolation"]),
        "sprites": [{"x": x, "y": y, "w": image.width, "h": image.height} for image, (x, y) in zip(images, origins)],
        "effects": effects,
    }

    target = particles_dir / name
    target.mkdir(parents=True, exist_ok=True)
    item = item_json(3, info)
    (target / "item.json").write_text(json.dumps(item, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    (target / "data.json").write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
    sheet.save(target / "texture.png")
    if info.thumbnail is not None:
        output = io.BytesIO()
        Image.open(io.BytesIO(info.thumbnail)).convert("RGBA").save(output, "PNG")
        (target / "thumbnail.png").write_bytes(output.getvalue())
    else:
        build_thumbnail(images[0]).save(target / "thumbnail.png")
    count = sum(len(group["particles"]) for effect in effects for group in effect["groups"])
    print(f"{len(effects)} effects, {count} particles, {len(images)} sprites on a {sheet.width} px texture")
    return target


def add_arguments(parser: argparse.ArgumentParser):
    parser.add_argument("name", help="the pack's folder name in resources/particles")
    parser.add_argument("source", type=Path, help="the folder or zip file of sprites (and its pack.toml)")


def main():
    parser = argparse.ArgumentParser(description="Build a Minimai particle pack from a folder or zip file of sprites.")
    add_arguments(parser)
    args = parser.parse_args()
    print(f"Particle pack written to {pack_particle(args.name, args.source)}")


if __name__ == "__main__":
    main()
