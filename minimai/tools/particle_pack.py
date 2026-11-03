"""Build a Minimai particle pack in ``resources/particles/<name>`` from a folder of sprites.

Usage: python -m minimai.tools.particle_pack <name> <folder> [--author A] [--desc D] [--thumbnail IMAGE]

Needs Pillow (``uv sync --extra tools``).

The folder holds white (or coloured) PNG sprites; the effects tint them. Effects whose sprites are
missing are left out, and the engine falls back to the standard effects for them:

    tap_perfect.png    tap_great.png    tap_good.png      Tap, star and hold end hits
    break_perfect.png  break_great.png  break_good.png    The same for breaks
    touch_circle.png   touch_star.png                     Touch hits
    touch_star_hollow.png                                 Touch hits' outer stars (else touch_star)
    hold_glow.png                                         Held holds and touch holds
    thumbnail.png                                         Optional

The animations are timelines taken from the reference player's effects, in its units (the judgment
ring is 4.8 across from the center), with linear keys. A particle effect can't follow a curve or a
parent's rotation, so each sprite becomes a chain of particles, one per stretch between keys, with
long turns cut into short ones. Sonolus Studio can tweak the result.
"""

import argparse
import io
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

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

PARTICLES_DIR = Path(__file__).parent.parent.parent / "resources" / "particles"
SPRITE_NAMES = (
    "tap_perfect",
    "tap_great",
    "tap_good",
    "break_perfect",
    "break_great",
    "break_good",
    "touch_circle",
    "touch_star",
    "touch_star_hollow",
    "hold_glow",
)
# Reference units per ring unit (the judgment ring radius).
REFERENCE_UNITS = SKIN_RING_RADIUS_PX / 100
# A turn longer than this (degrees) is split, so circling sprites stay on their circle.
MAX_SEGMENT_TURN = 30
# A colour change in a sprite's track is stepped at this many seconds.
COLOR_STEP = 0.1
WHITE = (1.0, 1.0, 1.0)
# A sprite that may be missing, and the one drawn instead.
SPRITE_FALLBACKS = {"touch_star_hollow": "touch_star"}


class Track:
    """Keys (time, value), linear between them and held outside them. Values are floats or tuples."""

    def __init__(self, *keys):
        self.keys = sorted(keys, key=lambda key: key[0])

    @classmethod
    def constant(cls, value):
        return cls((0.0, value))

    def at(self, t: float):
        keys = self.keys
        if t <= keys[0][0]:
            return keys[0][1]
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t <= t1:
                x = 0 if t1 == t0 else (t - t0) / (t1 - t0)
                if isinstance(v0, tuple):
                    return tuple(a + (b - a) * x for a, b in zip(v0, v1))
                return v0 + (v1 - v0) * x
        return keys[-1][1]

    @property
    def times(self) -> list[float]:
        return [t for t, _ in self.keys]

    def changes(self, t0: float, t1: float) -> bool:
        return self.at(t0) != self.at(t1) or any(t0 < t < t1 for t in self.times)


@dataclass
class Node:
    """A transform (Unity style: position, then rotation in degrees, then uniform scale), and maybe a
    sprite of ``size`` reference units square drawn at it."""
    pos: Track = field(default_factory=lambda: Track.constant((0.0, 0.0)))
    rot: Track = field(default_factory=lambda: Track.constant(0.0))
    scale: Track = field(default_factory=lambda: Track.constant(1.0))
    sprite: str | None = None
    size: float = 0.0
    alpha: Track = field(default_factory=lambda: Track.constant(1.0))
    color: Track = field(default_factory=lambda: Track.constant(WHITE))
    children: list["Node"] = field(default_factory=list)


@dataclass
class World:
    x: float
    y: float
    rot: float
    scale: float


def world_at(chain: list[Node], t: float) -> World:
    x = y = rot = 0.0
    scale = 1.0
    for node in chain:
        px, py = node.pos.at(t)
        c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        x, y = x + scale * (c * px - s * py), y + scale * (s * px + c * py)
        rot += node.rot.at(t)
        scale *= node.scale.at(t)
    return World(x, y, rot, scale)


def walk(node: Node, chain: list[Node] | None = None):
    """(chain from the root, node) for every node with a sprite, in drawing order."""
    chain = [*(chain or []), node]
    if node.sprite is not None:
        yield chain
    for child in node.children:
        yield from walk(child, chain)


def segment_times(chain: list[Node], duration: float) -> list[float]:
    sprite = chain[-1]
    times = {0.0, duration}
    for node in chain:
        for track in (node.pos, node.rot, node.scale):
            times.update(t for t in track.times if 0 < t < duration)
    times.update(t for t in sprite.alpha.times if 0 < t < duration)
    times.update(t for t in sprite.color.times if 0 < t < duration)
    ordered = sorted(times)
    result = [ordered[0]]
    for t0, t1 in zip(ordered, ordered[1:]):
        turn = max(abs(world_at(chain[: i + 1], t1).rot - world_at(chain[: i + 1], t0).rot) for i in range(len(chain)))
        pieces = max(1, math.ceil(turn / MAX_SEGMENT_TURN))
        if sprite.color.changes(t0, t1):
            pieces = max(pieces, math.ceil((t1 - t0) / COLOR_STEP))
        result.extend(t0 + (t1 - t0) * (i + 1) / pieces for i in range(pieces))
    return result


def color_hex(rgb) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in rgb)


def expression(value: float) -> dict:
    value = round(value, 5)
    return {"c": value} if value else {}


def prop(start: float, end: float) -> dict:
    return {"from": expression(start), "to": expression(end), "ease": "linear"}


@dataclass
class Effect:
    name: str
    # The spawn quad's side, in reference units.
    quad_size: float
    duration: float
    root: Node
    # A looped effect: copies of every particle, this many, evenly offset over the loop.
    loop_copies: int = 1


def sprite_state(chain: list[Node], t: float, half: float) -> tuple[float, ...]:
    """x, y, half-size, rotation and alpha of the chain's sprite, in the spawn quad's space."""
    sprite = chain[-1]
    world = world_at(chain, t)
    return (world.x / half, world.y / half, sprite.size * world.scale / 2 / half, math.radians(world.rot), sprite.alpha.at(t))


def merge_segments(times: list[float], states: list[tuple], colors: list) -> list[int]:
    """Indexes of the times to keep: a key in the middle of a straight stretch (same colour, every
    value on the line between its neighbours) is dropped."""
    keep = [0]
    for i in range(1, len(times) - 1):
        start = keep[-1]
        x = (times[i] - times[start]) / (times[i + 1] - times[start])
        straight = colors[i - 1] == colors[i] and all(
            abs(a + (b - a) * x - m) < 1e-4 for a, m, b in zip(states[start], states[i], states[i + 1])
        )
        if not straight:
            keep.append(i)
    keep.append(len(times) - 1)
    return keep


def build_particles(effect: Effect, sprite_ids: dict[str, int]) -> list[dict]:
    half = effect.quad_size / 2
    particles = []
    for chain in walk(effect.root):
        sprite = chain[-1]
        times = segment_times(chain, effect.duration)
        states = [sprite_state(chain, t, half) for t in times]
        # The colour of each stretch (a particle's colour can't change).
        colors = [color_hex(sprite.color.at((t0 + t1) / 2)) for t0, t1 in zip(times, times[1:])]
        keep = merge_segments(times, states, colors)
        for k0, k1 in zip(keep, keep[1:]):
            (x0, y0, s0, r0, a0), (x1, y1, s1, r1, a1) = states[k0], states[k1]
            if (a0 <= 0.001 and a1 <= 0.001) or (s0 == 0 and s1 == 0):
                continue
            for copy in range(effect.loop_copies):
                offset = copy / effect.loop_copies
                # Rounded ends, so back-to-back particles leave no gap.
                start = round(times[k0] / effect.duration + offset, 5)
                end = round(times[k1] / effect.duration + offset, 5)
                wrap = math.floor(start)
                particles.append({
                    "sprite": sprite_ids[sprite.sprite],
                    "color": colors[k0],
                    "start": round(start - wrap, 5),
                    "duration": round(end - start, 5),
                    "x": prop(x0, x1),
                    "y": prop(y0, y1),
                    "w": prop(s0, s1),
                    "h": prop(s0, s1),
                    "r": prop(r0, r1),
                    "a": prop(a0, a1),
                })
    return particles


# --- The effects -------------------------------------------------------------------------------

PERFECT_ALPHA = Track((0, 1.0), (0.233, 0.995), (0.417, 0.0))


def perfect_effect(sprite: str) -> Node:
    """A hex in the middle grows, while four more spin in toward it; breaks use this for every grade."""
    hexes = (
        (1, ((0.552, 0.5), (0.437, 0.396), 0.567), 0.6),
        (1, ((-0.431, -0.527), (-0.319, -0.39), 0.5), 0.6),
        (-1, ((0.473, -0.468), (0.35, -0.347), 0.5), 0.8),
        (-1, ((-0.502, 0.492), (-0.372, 0.364), 0.5), 0.8),
    )
    children = []
    for turn, (start, middle, end_time), end_scale in hexes:
        children.append(Node(
            pos=Track.constant((0.0, -0.002)),
            rot=Track((0, 0.0), (0.467, 180.0 * turn), (0.717, 360.0 * turn)),
            children=[Node(
                pos=Track((0, start), (0.25, middle), (end_time, (0.0, 0.0))),
                rot=Track((0, 0.0), (0.467, -180.0 * turn), (0.717, -360.0 * turn)),
                scale=Track((0, 0.479), (0.267, end_scale)),
                sprite=sprite,
                size=2.56,
                alpha=PERFECT_ALPHA,
            )],
        ))
    return Node(
        rot=Track.constant(90.0),
        scale=Track((0, 0.0), (0.083, 0.7), (0.45, 1.3)),
        sprite=sprite,
        size=2.56,
        alpha=PERFECT_ALPHA,
        children=children,
    )


def great_effect(sprite: str) -> Node:
    """Three rings of the hex, one after another, growing and fading."""
    rings = (
        ((0.0, -0.002), ((0, 0.0), (0.083, 0.693), (0.283, 1.3)), (0.006, 0.002), 0.746, 28.615, ((0, 1.0), (0.133, 1.0), (0.283, 0.0))),
        ((0.0, -0.002), ((0, 0.0), (0.083, 0.0), (0.1, 0.693), (0.317, 1.8)), (0.001, -0.007), 0.547, 0.0, ((0, 1.0), (0.167, 1.0), (0.317, 0.0))),
        ((0.0, 0.0), ((0, 0.0), (0.083, 0.0), (0.117, 0.693), (0.35, 2.5)), (0.001, -0.009), 0.382, -29.931, ((0, 1.0), (0.2, 1.0), (0.35, 0.0))),
    )
    return Node(
        rot=Track.constant(120.6),
        children=[
            Node(
                pos=Track.constant(pivot),
                scale=Track(*scale_keys),
                children=[Node(
                    pos=Track.constant(pos),
                    rot=Track.constant(rot),
                    scale=Track.constant(scale),
                    sprite=sprite,
                    size=2.56,
                    alpha=Track(*alpha_keys),
                )],
            )
            for pivot, scale_keys, pos, scale, rot, alpha_keys in rings
        ],
    )


def good_effect(sprite: str) -> Node:
    """Three hexes burst out and back while the whole effect pops and shrinks away."""
    bursts = (
        ((0.702, 0.411), (0.791, 0.439), -30.941),
        ((-0.017, -0.801), (-0.018, -0.925), -30.851),
        ((-0.678, 0.39), (-0.808, 0.465), -29.931),
    )
    return Node(
        rot=Track.constant(120.09),
        scale=Track((0, 0.0), (0.117, 0.7), (0.15, 0.7), (0.4, 0.0)),
        children=[
            Node(
                pos=Track((0, (0.0, 0.0)), (0.117, out), (0.15, far), (0.2, (0.0, 0.0)), (0.25, out)),
                rot=Track.constant(rot),
                sprite=sprite,
                size=1.92,
            )
            for out, far, rot in bursts
        ],
    )


def touch_effect(circle_color, star_color) -> Node:
    """A circle flashes out while 16 stars burst from the sensor, hold, then shrink away. Measured
    from a recording of the reference (30 fps) rather than its prefab, which has fewer stars."""
    # Seconds, for the recorded frames (the first one a frame after the hit).
    f = [1 / 60 + i / 30 for i in range(8)]

    def star(angle: float, radius: Track, size: Track, sprite: str, rot: float) -> Node:
        direction = (math.cos(math.radians(angle)), math.sin(math.radians(angle)))
        return Node(
            pos=Track(*((t, (direction[0] * r, direction[1] * r)) for t, r in radius.keys)),
            rot=Track.constant(rot),
            scale=size,
            sprite=sprite,
            size=1.0,
            alpha=Track((f[5], 1.0), (f[7], 0.6)),
            color=Track.constant(star_color),
        )

    # Outer stars fly out to their place; inner ones appear there.
    outer_radius = Track((0, 0.42), (f[0], 0.5), (f[1], 0.61), (f[2], 0.65), (f[3], 0.7))
    inner_radius = Track.constant(0.4)
    # Full widths in reference units (a little over the measured, for the thin star sprite):
    # medium, big, then small.
    outer_size = Track((0, 0.22), (f[0], 0.28), (f[1], 0.37), (f[2], 0.3), (f[3], 0.25), (f[5], 0.25), (f[6], 0.19), (f[7], 0.0))
    inner_size = Track((0, 0.13), (f[0], 0.16), (f[1], 0.21), (f[2], 0.14), (f[3], 0.13), (f[5], 0.13), (f[6], 0.05), (f[7], 0.0))
    stars = []
    for i in range(4):
        axis = 90.0 * i
        diagonal = axis + 45.0
        stars.append(star(diagonal, outer_radius, outer_size, "touch_star", 0.0))
        # Hollow stars lean one way or the other, alternating around the ring.
        lean = 22.5 if i % 2 == 0 else -22.5
        stars.append(star(axis, outer_radius, outer_size, "touch_star_hollow", lean))
        stars.append(star(axis, inner_radius, inner_size, "touch_star", 0.0))
        stars.append(star(diagonal, inner_radius, inner_size, "touch_star_hollow", -lean))
    return Node(children=[
        Node(
            scale=Track((0, 0.25), (f[0], 0.475), (f[1], 1.1), (f[2], 1.34), (f[3], 1.4)),
            sprite="touch_circle",
            size=1.0,
            alpha=Track((0, 1.0), (f[0], 0.9), (f[1], 0.45), (f[2], 0.15), (f[3], 0.0)),
            color=Track.constant(circle_color),
        ),
        *stars,
    ])


def hold_glow(color) -> Node:
    """One ring of the held note's glow: it spreads out fast, slows, and fades near its widest.
    Measured from a recording of the reference: a ring lives about 0.24 seconds of the 0.3 second
    loop, and reaches about 1.1 units across its middle (the sprite's ring is at 0.72 of its
    half-size, so the sprite is about 3 units wide then)."""
    life = 0.8 * HOLD_DURATION
    widest = 3.0
    spread = ((0, 0.0), (0.14, 0.15), (0.28, 0.4), (0.42, 0.62), (0.56, 0.8), (0.69, 0.93), (0.83, 1.0), (1.0, 1.05))
    return Node(
        scale=Track(*((x * life, widest * f) for x, f in spread)),
        sprite="hold_glow",
        size=1.0,
        alpha=Track((0, 0.0), (0.14 * life, 0.75), (0.56 * life, 0.75), (0.69 * life, 0.7), (0.83 * life, 0.25), (life, 0.0)),
        color=Track.constant(color),
    )


TOUCH_COLORS = {
    # Perfect from the recording; great and good from the reference player's colours.
    "Perfect": ((1.0, 0.97, 0.1), (0.98, 0.79, 0.01)),
    "Great": ((1.0, 0.675, 0.883), (1.0, 0.675, 0.883)),
    "Good": ((0.368, 0.99, 0.405), (0.368, 0.9, 0.405)),
}
# The reference player's tints, halfway to white: the recorded perfect rings are a pale yellow.
HOLD_COLORS = {
    "Perfect": (1.0, 0.95, 0.55),
    "Great": (1.0, 0.85, 0.97),
    "Good": (0.78, 1.0, 0.8),
    "Miss": WHITE,
}
# Rings per loop: one starts every 0.1 seconds.
HOLD_GLOW_COPIES = 3


def all_effects() -> list[tuple[Effect, set[str]]]:
    """Every effect and the sprites it needs."""
    tap = TAP_EFFECT_SIZE * REFERENCE_UNITS
    effects = []
    for prefix in ("tap", "break"):
        title = prefix.capitalize()
        perfect, great, good = f"{prefix}_perfect", f"{prefix}_great", f"{prefix}_good"
        if prefix == "tap":
            grades = (
                (perfect, perfect_effect(perfect), TAP_PERFECT_DURATION),
                (great, great_effect(great), TAP_GREAT_DURATION),
                (good, good_effect(good), TAP_GOOD_DURATION),
            )
        else:
            grades = tuple((sprite, perfect_effect(sprite), TAP_PERFECT_DURATION) for sprite in (perfect, great, good))
        for (sprite, root, duration), grade in zip(grades, ("Perfect", "Great", "Good")):
            effects.append((Effect(f"Mai {title} {grade}", tap, duration, root), {sprite}))
    for grade, (circle, star) in TOUCH_COLORS.items():
        effects.append((
            Effect(f"Mai Touch {grade}", TOUCH_EFFECT_SIZE * REFERENCE_UNITS, TOUCH_DURATION, touch_effect(circle, star)),
            {"touch_circle", "touch_star"},
        ))
    for grade, color in HOLD_COLORS.items():
        effects.append((
            Effect(f"Mai Hold {grade}", HOLD_EFFECT_SIZE * REFERENCE_UNITS, HOLD_DURATION, hold_glow(color), HOLD_GLOW_COPIES),
            {"hold_glow"},
        ))
    return effects


IDENTITY_TRANSFORM = {f"{axis}{i}": {f"{axis}{i}": 1} for i in range(1, 5) for axis in "xy"}


def build_data(sprite_names: list[str]) -> tuple[dict, list[str]]:
    """data.json (without the atlas rects) and the effects left out."""
    sprite_ids = {name: i for i, name in enumerate(sprite_names)}
    for name, fallback in SPRITE_FALLBACKS.items():
        if name not in sprite_ids and fallback in sprite_ids:
            sprite_ids[name] = sprite_ids[fallback]
    effects = []
    skipped = []
    for effect, needs in all_effects():
        if not needs <= sprite_ids.keys():
            skipped.append(effect.name)
            continue
        effects.append({
            "name": effect.name,
            "transform": IDENTITY_TRANSFORM,
            "groups": [{"count": 1, "particles": build_particles(effect, sprite_ids)}],
        })
    return {"interpolation": True, "sprites": [], "effects": effects}, skipped


def pack_atlas(images: list) -> tuple[object, list[dict]]:
    """Shelf-pack the sprites into a square power-of-two texture. Each sprite gets a 1 px border
    copied from its edge, so filtering doesn't pick up its neighbours."""
    from PIL import Image

    order = sorted(range(len(images)), key=lambda i: -images[i].height)
    size = 64
    while True:
        placed = {}
        x = y = row = 0
        fits = True
        for i in order:
            w, h = images[i].width + 2, images[i].height + 2
            if x + w > size:
                x, y, row = 0, y + row, 0
            if y + h > size or w > size:
                fits = False
                break
            placed[i] = (x, y)
            x += w
            row = max(row, h)
        if fits:
            break
        size *= 2
    atlas = Image.new("RGBA", (size, size))
    rects = [{}] * len(images)
    for i, (x, y) in placed.items():
        image = images[i]
        w, h = image.size
        atlas.paste(image, (x + 1, y + 1))
        atlas.paste(image.crop((0, 0, w, 1)), (x + 1, y))
        atlas.paste(image.crop((0, h - 1, w, h)), (x + 1, y + h + 1))
        atlas.paste(atlas.crop((x + 1, y, x + 2, y + h + 2)), (x, y))
        atlas.paste(atlas.crop((x + w, y, x + w + 1, y + h + 2)), (x + w + 1, y))
        rects[i] = {"x": x + 1, "y": y + 1, "w": image.width, "h": image.height}
    return atlas, rects


def build_thumbnail(images: list):
    from PIL import Image

    thumbnail = Image.new("RGBA", (128, 128), (32, 32, 40, 255))
    preview = images[0].copy()
    preview.thumbnail((96, 96))
    thumbnail.alpha_composite(preview, ((128 - preview.width) // 2, (128 - preview.height) // 2))
    return thumbnail


def pack_particle(
    name: str,
    folder: Path,
    *,
    title: str | None = None,
    author: str = "Unknown",
    description: str = "",
    thumbnail: Path | None = None,
    particles_dir: Path = PARTICLES_DIR,
) -> Path:
    try:
        from PIL import Image
    except ImportError as error:
        raise SystemExit("Pillow is needed: uv sync --extra tools") from error

    sprite_names = [stem for stem in SPRITE_NAMES if (folder / f"{stem}.png").is_file()]
    missing = [stem for stem in SPRITE_NAMES if stem not in sprite_names and stem not in SPRITE_FALLBACKS]
    if missing:
        print(f"Missing sprites: {', '.join(missing)}")
    if not sprite_names:
        raise SystemExit(f"No sprites in {folder}")
    images = [Image.open(folder / f"{stem}.png").convert("RGBA") for stem in sprite_names]
    data, skipped = build_data(sprite_names)
    if skipped:
        print(f"Left out (the engine falls back to standard effects): {', '.join(skipped)}")
    atlas, rects = pack_atlas(images)
    data = {"width": atlas.width, "height": atlas.height, **data, "sprites": rects}

    target = particles_dir / name
    target.mkdir(parents=True, exist_ok=True)
    item = {
        "version": 3,
        "title": {"en": title or name},
        "subtitle": {"en": "Minimai"},
        "author": {"en": author},
        "tags": [],
        "description": {"en": description},
    }
    (target / "item.json").write_text(json.dumps(item, indent=4, ensure_ascii=False) + "\n", encoding="utf-8")
    (target / "data.json").write_text(json.dumps(data, separators=(",", ":")) + "\n", encoding="utf-8")
    atlas.save(target / "texture.png")
    if thumbnail is None and (folder / "thumbnail.png").is_file():
        thumbnail = folder / "thumbnail.png"
    if thumbnail is not None:
        output = io.BytesIO()
        Image.open(thumbnail).convert("RGBA").save(output, "PNG")
        (target / "thumbnail.png").write_bytes(output.getvalue())
    else:
        build_thumbnail(images).save(target / "thumbnail.png")
    count = sum(len(effect["groups"][0]["particles"]) for effect in data["effects"])
    print(f"{len(data['effects'])} effects, {count} particles")
    return target


def main():
    parser = argparse.ArgumentParser(description="Build a Minimai particle pack from a folder of sprites.")
    parser.add_argument("name", help="the pack's folder name in resources/particles")
    parser.add_argument("folder", type=Path, help="folder with the sprites")
    parser.add_argument("--author", default="Unknown")
    parser.add_argument("--desc", default="", help="the pack's description")
    parser.add_argument("--thumbnail", type=Path, help="image file; overrides a thumbnail.png in the folder")
    args = parser.parse_args()
    folder = pack_particle(args.name, args.folder, author=args.author, description=args.desc, thumbnail=args.thumbnail)
    print(f"Particle pack written to {folder}")


if __name__ == "__main__":
    main()
