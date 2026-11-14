"""Draw the skin sprites made of shapes: the life counter's rings, the preview's each line and firework
halo, the firework's rays and pale ball, and the touch feedback's ring and petal.

Usage: python -m minimai.tools.art <folder> [--config C] [--scale S] [--only ART ...]

Needs Pillow (``uv sync --extra tools``). How they look is a config: the defaults are in
``tools/defaults/art.toml`` and ``--config`` is merged over them (docs/arts.md). Each sprite is written where
the skin's default recipe reads it (``CounterSkins/counter_high_life_ring.png``), so the folder works as a
skin source; ``--only`` draws some of the arts (``life_ring``, ``each_line``, ``firework``, ``touch_feedback``).
"""

from __future__ import annotations

import argparse
import colorsys
import math
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING

from minimai.lib.firework import FIREWORK_HUES
from minimai.lib.layout import COUNTER_LIFE_SIZE, FIREWORK_RAY_SIZE, SKIN_RING_RADIUS_PX, TOUCH_FEEDBACK_RING_RIM
from minimai.tools.pack_config import merged
from minimai.tools.skin_pack import default_source_path

if TYPE_CHECKING:
    from PIL import Image

DEFAULTS_PATH = Path(__file__).parent / "defaults" / "art.toml"
ARTS = ("life_ring", "each_line", "firework", "touch_feedback")


def rgb(value) -> tuple[int, ...]:
    return tuple(int(part) for part in value)


def shade(colour: tuple[int, ...], factor: float) -> tuple[int, ...]:
    return tuple(round(c * factor) for c in colour)


def mix(colour: tuple[int, ...], other: tuple[int, ...], amount: float) -> tuple[int, ...]:
    return tuple(round(a + (b - a) * amount) for a, b in zip(colour, other))


def smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def downsampled(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    from PIL import Image

    return image.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")


# ==== Life ring ===================================================================================


def heart_points(width: float, center: tuple[float, float]) -> list[tuple[float, float]]:
    """A heart ``width`` wide, its bounding box centered on ``center`` (image coordinates)."""
    points = []
    for i in range(400):
        t = 2 * math.pi * i / 400
        points.append((16 * math.sin(t) ** 3, 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)))
    xs, ys = [x for x, _ in points], [y for _, y in points]
    scale = width / (max(xs) - min(xs))
    middle = (max(ys) + min(ys)) / 2
    return [(center[0] + x * scale, center[1] - (y - middle) * scale) for x, y in points]


def deep_shade(colour: tuple[int, ...], amount: float) -> tuple[int, ...]:
    """The colour multiplied by itself and darkened: green stays green, yellow turns orange."""
    return tuple(round(v * v / 255 * amount) for v in colour)


def draw_life_ring(state: Mapping, px: float, supersample: int, life: Mapping) -> Image.Image:
    """One state's backdrop, at ``px`` texture px per skin px (supersampled)."""
    from PIL import Image, ImageDraw

    base = rgb(state["color"])
    mark_light = rgb(life["mark_light"])
    side = round(float(life["size"]) * px / supersample) * supersample
    c = side / 2
    image = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    def disc(radius: float):
        return (c - radius * px, c - radius * px, c + radius * px, c + radius * px)

    def ring(outer: float, inner: float):
        mask = Image.new("L", (side, side))
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse(disc(outer), fill=255)
        mask_draw.ellipse(disc(inner), fill=0)
        return mask

    deep = deep_shade(base, life["deep_shade"])
    draw.ellipse(disc(life["ring_inner"]), fill=rgb(life["backdrop"]))
    draw.ellipse(
        disc(life["ring_outer"]), outline=deep + (255,), width=round((life["ring_outer"] - life["ring_inner"]) * px)
    )
    # The marks between the rims, the coloured ones centered on the buttons (22.5° off the top).
    marks = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    mark_draw = ImageDraw.Draw(marks)
    for i in range(16):
        start = -90 - 11.25 + 22.5 * i
        colour_mark = base if i % 2 else mark_light
        mark_draw.pieslice(disc(life["ring_outer"]), start, start + 22.5, fill=colour_mark + (255,))
    image.paste(marks, mask=ring(life["ring_outer"] - life["ring_rim"], life["ring_inner"] + life["ring_rim"]))
    strip_outer = life["ring_outer"] - life["ring_rim"]
    image.paste(mark_light + (255,), mask=ring(strip_outer, strip_outer - life["light_strip"]))
    # Dividers between the marks, through the strip.
    for i in range(16):
        angle = math.radians(-90 - 11.25 + 22.5 * i)
        inner, outer = life["ring_inner"] * px, life["ring_outer"] * px
        draw.line(
            [(c + inner * math.cos(angle), c + inner * math.sin(angle)), (c + outer * math.cos(angle), c + outer * math.sin(angle))],
            fill=deep + (255,),
            width=round(life["mark_gap"] * px),
        )
    width = state.get("heart_width", 0)
    if width:
        heart_side = round(width * 1.2 * px)
        heart = draw_heart(base, width * px, heart_side, life)
        image.alpha_composite(heart, (round(c - heart_side / 2), round(c + life["heart_drop"] * px - heart_side / 2)))
    red, green, blue, alpha = image.split()
    red, green, blue = (band.point(lambda v: round(v * life["brightness"])) for band in (red, green, blue))
    return Image.merge("RGBA", (red, green, blue, alpha))


def draw_heart(base: tuple[int, ...], width: float, side: int, life: Mapping) -> Image.Image:
    """A heart ``width`` wide (texture px) in the middle of a ``side`` square: a shade of ``base``,
    darker toward its point, then shaded from its border in."""
    from PIL import Image, ImageDraw

    heart_center = (side / 2, side / 2)
    heart = Image.new("L", (side, side))
    ImageDraw.Draw(heart).polygon(heart_points(width, heart_center), fill=int(life["heart_alpha"]))
    deep = deep_shade(base, life["deep_shade"])
    top = shade(mix(base, rgb(life["heart_warm"]), life["heart_top_warmth"]), life["heart_shade"])
    bottom = shade(mix(base, deep, life["heart_bottom_depth"]), life["heart_shade"])
    # Top to bottom over the heart itself.
    _, box_top, _, box_bottom = heart.getbbox()
    gradient = Image.new("L", (side, side))
    gradient.paste(255, (0, box_bottom, side, side))
    gradient.paste(Image.linear_gradient("L").resize((side, box_bottom - box_top)), (0, box_top))
    body = Image.composite(Image.new("RGB", (side, side), bottom), Image.new("RGB", (side, side), top), gradient)
    # How far in: nested hearts, each smaller one drawn over the last.
    depth = Image.new("L", (side, side))
    depth_draw = ImageDraw.Draw(depth)
    steps = round(width / 4)
    for step in range(steps):
        depth_draw.polygon(heart_points(width * (1 - step / steps), heart_center), fill=round(255 * step / steps))
    body = shade_heart(body, depth, deep, life)
    image = body.convert("RGBA")
    image.putalpha(heart)
    return image


def shade_heart(body, depth, deep: tuple[int, ...], life: Mapping):
    """``depth`` 0 at the heart's border to 255 at its center: a rim in ``deep``, then a light bevel
    fading into the body."""
    from PIL import Image

    def bevel(value: int) -> float:
        d = value / 255
        if d < life["heart_bevel"]:
            return life["heart_bevel_light"]
        return life["heart_bevel_light"] * max(1 - (d - life["heart_bevel"]) / life["heart_bevel_fade"], 0)

    light = depth.point(lambda v: round(255 * bevel(v)))
    rim = depth.point(lambda v: 255 if v / 255 < life["heart_rim"] else 0)
    body = Image.composite(Image.new("RGB", body.size, (255, 255, 255)), body, light)
    return Image.composite(Image.new("RGB", body.size, deep), body, rim)


def life_rings(config: Mapping) -> dict[str, Image.Image]:
    life, supersample = config["life_ring"], int(config["supersample"])
    px = float(config["scale"]) * supersample
    result = {}
    for name, state in life["states"].items():
        image = draw_life_ring(state, px, supersample, life)
        result[f"Mai Counter {name} Ring"] = downsampled(image, (image.width // supersample, image.height // supersample))
    return result


# ==== Each line ===================================================================================


def each_line(config: Mapping) -> dict[str, Image.Image]:
    from PIL import Image

    settings = config["each_line"]
    width, height = (round(float(side) * float(config["scale"])) for side in settings["size"])
    colour = rgb(settings["color"])
    core = float(settings["core"])
    line = Image.new("RGBA", (width, height), colour + (0,))
    for y in range(height):
        # 0 at the middle, 1 at the edges.
        d = abs((y + 0.5) / height * 2 - 1)
        fade = (d - core) / (1 - core)
        alpha = 1 - max(0.0, min(1.0, fade))
        for x in range(width):
            line.putpixel((x, y), colour + (round(255 * alpha),))
    return {"Mai Preview Each Line": line}


# ==== Firework ====================================================================================


def length_alpha(u: float, settings: Mapping) -> float:
    fade_in, fade_out = float(settings["fade_in_end"]), float(settings["fade_out_start"])
    return smoothstep(u / fade_in) * (1 - smoothstep((u - fade_out) / (1 - fade_out)))


def draw_ray_masks(width: int, height: int, supersample: int, settings: Mapping):
    """The ray's alpha, and where it shows the full colour (the rest is the dark shade), each
    ``width`` x ``height`` pixels, drawn big and scaled down."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    s = supersample
    w, h = width * s, height * s
    wedge = Image.new("L", (w, h), 0)
    ImageDraw.Draw(wedge).polygon([(w / 2, h), (0, 0), (w, 0)], fill=255)

    # Supersampled pixels per skin pixel.
    px = s * height / float(settings["ray_size"][1])
    spacing = float(settings["dot_spacing"]) * px
    dots_start, dots_merged = float(settings["dots_start"]), float(settings["dots_merged"])
    light = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(light)
    merged_y = h * (1 - dots_merged)
    draw.rectangle((0, 0, w, merged_y), fill=255)
    # Rows of dots from where they merge back toward the tip, each a little smaller.
    row = 0
    y = merged_y
    while y < h * (1 - dots_start):
        u = 1 - y / h
        radius = float(settings["dot_merged_radius"]) * spacing * smoothstep((u - dots_start) / (dots_merged - dots_start))
        x = w / 2 + (spacing / 2 if row % 2 else 0)
        while x - spacing > 0:
            x -= spacing
        while x < w:
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)
            x += spacing
        y += spacing * 0.87
        row += 1

    fade = Image.new("L", (1, h))
    for py in range(h):
        fade.putpixel((0, py), round(255 * length_alpha(1 - (py + 0.5) / h, settings)))
    fade = fade.resize((w, h))

    alpha = ImageChops.multiply(wedge, fade).filter(ImageFilter.GaussianBlur(s / 2))
    light = light.filter(ImageFilter.GaussianBlur(s / 3))
    return alpha.resize((width, height), Image.Resampling.LANCZOS), light.resize((width, height), Image.Resampling.LANCZOS)


def ray_color(index: int, settings: Mapping, value: float = 1.0) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb(index / FIREWORK_HUES, float(settings["saturation"]), float(settings["value"]) * value)
    return round(r * 255), round(g * 255), round(b * 255)


def draw_preview_halo(size: int, supersample: int, preview: Mapping) -> Image.Image:
    """Twelve plain wedges aimed at the center of a ``size`` square, from ``hole`` of the way out to the
    edge, ``ray_width`` of the radius wide there."""
    from PIL import Image, ImageDraw

    big = size * supersample
    center = big / 2
    half_width = center * float(preview["ray_width"]) / 2
    halo = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(halo)
    for i in range(FIREWORK_HUES):
        r, g, b = colorsys.hsv_to_rgb(i / FIREWORK_HUES, float(preview["saturation"]), float(preview["value"]))
        # Clockwise from up, in image coordinates (y down).
        angle = 2 * math.pi * i / FIREWORK_HUES
        out = (math.sin(angle), -math.cos(angle))
        side = (math.cos(angle), math.sin(angle))
        end = (center + out[0] * center, center + out[1] * center)
        draw.polygon(
            [
                (center, center),
                (end[0] + side[0] * half_width, end[1] + side[1] * half_width),
                (end[0] - side[0] * half_width, end[1] - side[1] * half_width),
            ],
            fill=(round(r * 255), round(g * 255), round(b * 255), 255),
        )
    hole = Image.new("L", (big, big), 255)
    hole_radius = center * float(preview["hole"])
    ImageDraw.Draw(hole).ellipse(
        (center - hole_radius, center - hole_radius, center + hole_radius, center + hole_radius), fill=0
    )
    alpha = halo.getchannel("A")
    halo.putalpha(Image.composite(alpha, hole, hole))
    return halo.resize((size, size), Image.Resampling.LANCZOS)


def draw_pale_ball(size: int, ball: Mapping) -> Image.Image:
    """A soft white-pink ball, fading out from the middle to the edge."""
    from PIL import Image

    small = Image.new("L", (size, size))
    for y in range(size):
        for x in range(size):
            d = ((x + 0.5 - size / 2) ** 2 + (y + 0.5 - size / 2) ** 2) ** 0.5 / (size / 2)
            small.putpixel((x, y), round(255 * float(ball["alpha"]) * (1 - smoothstep((d - 0.1) / 0.9))))
    result = Image.new("RGBA", (size, size), rgb(ball["color"]) + (0,))
    result.putalpha(small)
    return result


def firework(config: Mapping) -> dict[str, Image.Image]:
    from PIL import Image

    settings, scale, supersample = config["firework"], float(config["scale"]), int(config["supersample"])
    width, height = (round(float(side) * scale) for side in settings["ray_size"])
    alpha, light = draw_ray_masks(width, height, supersample, settings)
    result = {}
    for i in range(FIREWORK_HUES):
        ray = Image.composite(
            Image.new("RGB", (width, height), ray_color(i, settings)),
            Image.new("RGB", (width, height), ray_color(i, settings, float(settings["dark_value"]))),
            light,
        ).convert("RGBA")
        ray.putalpha(alpha)
        result[f"Mai Firework Ray {i + 1}"] = ray
    result["Mai Firework Ball Pale"] = draw_pale_ball(round(float(settings["pale_ball"]["size"]) * scale), settings["pale_ball"])
    preview = settings["preview"]
    result["Mai Preview Firework"] = draw_preview_halo(round(float(preview["size"]) * scale), supersample, preview)
    return result


# ==== Touch feedback ==============================================================================


def ring_alpha(d: float, settings: Mapping) -> float:
    """``d``: distance from the center as a part of the half size."""
    rim_at = TOUCH_FEEDBACK_RING_RIM
    x = d / rim_at
    base, rise, power = float(settings["gradient_base"]), float(settings["gradient_rise"]), float(settings["gradient_power"])
    gradient = base + rise * min(x, 1) ** power if x <= 1 else 0.0
    rim = math.exp(-0.5 * ((d - rim_at) / float(settings["rim_width"])) ** 2)
    glow = 0.3 * math.exp(-max(d - rim_at, 0) / float(settings["glow_width"])) if d > rim_at else 0.0
    return min(1.0, gradient + rim + glow) if d < 1 else 0.0


def draw_feedback_ring(size: int, supersample: int, settings: Mapping) -> Image.Image:
    from PIL import Image

    big = size * supersample
    half = big / 2
    alpha = Image.new("L", (big, big))
    pixels = alpha.load()
    # Only the radial profile matters: fill each pixel from a lookup by distance.
    table = [round(255 * ring_alpha(i / 1000, settings)) for i in range(1001)]
    for y in range(big):
        dy = (y + 0.5 - half) / half
        for x in range(big):
            dx = (x + 0.5 - half) / half
            d = (dx * dx + dy * dy) ** 0.5
            pixels[x, y] = table[min(round(d * 1000), 1000)]
    ring = Image.new("RGBA", (big, big), (255, 255, 255, 0))
    ring.putalpha(alpha)
    return ring.resize((size, size), Image.Resampling.LANCZOS)


def draw_petal(width: int, height: int, supersample: int, settings: Mapping) -> Image.Image:
    from PIL import Image, ImageFilter

    big_w, big_h = width * supersample, height * supersample
    alpha = Image.new("L", (big_w, big_h))
    pixels = alpha.load()
    margin = 0.08
    taper = float(settings["petal_taper"])
    for py in range(big_h):
        # v: -1 at the inner (bottom) end, 1 at the outer (top) end.
        v = 1 - 2 * (py + 0.5) / big_h
        v /= 1 - margin
        if abs(v) >= 1:
            continue
        half_width = (1 - v * v) ** 0.5 * (1 - taper * v) / (1 + taper) * (1 - margin)
        for px in range(big_w):
            u = 2 * (px + 0.5) / big_w - 1
            if abs(u) < half_width:
                pixels[px, py] = 255
    alpha = alpha.filter(ImageFilter.GaussianBlur(supersample * 0.8))
    petal = Image.new("RGBA", (big_w, big_h), (255, 255, 255, 0))
    petal.putalpha(alpha)
    return petal.resize((width, height), Image.Resampling.LANCZOS)


def touch_feedback(config: Mapping) -> dict[str, Image.Image]:
    settings, supersample = config["touch_feedback"], int(config["supersample"])
    size = round(float(settings["size"]) * float(config["scale"]))
    return {
        "Mai Touch Feedback Ring": draw_feedback_ring(size, supersample, settings),
        "Mai Touch Feedback Petal": draw_petal(size // 4, size // 2, supersample, settings),
    }


# ==== Main ========================================================================================


def layout_sizes() -> dict[str, object]:
    """The config sizes that must match lib/layout.py."""
    return {
        "life_ring.size": round(COUNTER_LIFE_SIZE * SKIN_RING_RADIUS_PX),
        "firework.ray_size": [round(FIREWORK_RAY_SIZE.x * SKIN_RING_RADIUS_PX), round(FIREWORK_RAY_SIZE.y * SKIN_RING_RADIUS_PX)],
    }


def check_sizes(config: Mapping, strict: bool):
    stale = {}
    for key, value in layout_sizes().items():
        section, name = key.split(".")
        if config[section][name] != value:
            stale[key] = (config[section][name], value)
    if stale and strict:
        raise SystemExit(f"{DEFAULTS_PATH.name}: sizes differ from lib/layout.py: {stale}")
    if stale:
        print(f"Sizes that differ from the layout (the engine stretches those sprites): {stale}")


def load_config(path: Path | None) -> dict:
    with DEFAULTS_PATH.open("rb") as file:
        config = tomllib.load(file)
    check_sizes(config, strict=True)
    if path is not None:
        with path.open("rb") as file:
            config = merged(config, tomllib.load(file))
        check_sizes(config, strict=False)
    return config


DRAWERS = {"life_ring": life_rings, "each_line": each_line, "firework": firework, "touch_feedback": touch_feedback}


def draw_arts(folder: Path, config: Mapping, only: list[str] | None = None) -> int:
    """Writes the arts' sprites into ``folder``; returns how many."""
    try:
        import PIL  # noqa: F401
    except ImportError as error:
        raise SystemExit("Pillow is needed: uv sync --extra tools") from error
    folder.mkdir(parents=True, exist_ok=True)
    count = 0
    for art in only or ARTS:
        if config[art].get("skip"):
            continue
        for name, image in DRAWERS[art](config).items():
            path = folder / default_source_path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            image.save(path)
            count += 1
    return count


def main():
    parser = argparse.ArgumentParser(description="Draw the skin sprites made of shapes.")
    parser.add_argument("folder", type=Path, help="where the sprites go")
    parser.add_argument("--config", type=Path, help="a TOML config merged over the defaults")
    parser.add_argument("--scale", type=float, help="texture px per skin px; overrides the config's")
    parser.add_argument("--only", nargs="+", choices=ARTS, help="draw only these arts")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.scale is not None:
        config["scale"] = args.scale
    count = draw_arts(args.folder, config, args.only)
    print(f"{count} sprites written to {args.folder}")


if __name__ == "__main__":
    main()
