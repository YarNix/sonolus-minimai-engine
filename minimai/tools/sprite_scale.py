"""Resize skin sprite PNGs, e.g. to fit more of them in the skin texture.

Usage: python -m minimai.tools.sprite_scale <sprite> <new_size> [--filter F] [--output O]

Needs Pillow (``uv sync --extra tools``). ``<sprite>`` is a PNG, or a folder whose PNGs are all
scaled. ``<new_size>`` is ``<width>x<height>`` (e.g. ``214x70``) or a ratio (e.g. ``0.5``). The
files are overwritten unless ``--output`` names a ``.png`` (for one sprite) or a folder.

The engine draws sprites at the size in ``lib/layout.py``, not the texture size, so a smaller
texture only loses detail. Resizing is done on premultiplied alpha, so edges don't darken.
"""

import argparse
from pathlib import Path

FILTERS = ("nearest", "bilinear", "bicubic", "lanczos")


def parse_size(text: str) -> tuple[float, float] | float:
    """``(width, height)`` in px, or a ratio."""
    try:
        if "x" in text.lower():
            width, height = text.lower().split("x")
            return int(width), int(height)
        return float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected <width>x<height> or a ratio, not {text!r}") from None


def scale_sprite(source: Path, target: Path, size: tuple[float, float] | float, resample: int):
    from PIL import Image

    image = Image.open(source).convert("RGBA")
    if isinstance(size, tuple):
        width, height = size
    else:
        width, height = image.width * size, image.height * size
    new_size = (max(1, round(width)), max(1, round(height)))
    scaled = image.convert("RGBa").resize(new_size, resample).convert("RGBA")
    target.parent.mkdir(parents=True, exist_ok=True)
    scaled.save(target)
    print(f"{source.name}: {image.width}x{image.height} -> {new_size[0]}x{new_size[1]}")


def main():
    parser = argparse.ArgumentParser(description="Resize skin sprite PNGs.")
    parser.add_argument("sprite", type=Path, help="a PNG, or a folder of PNGs")
    parser.add_argument("new_size", type=parse_size, help="<width>x<height> or a ratio")
    parser.add_argument("--filter", choices=FILTERS, default="lanczos")
    parser.add_argument("--output", type=Path, help="a .png (one sprite) or a folder; default overwrites")
    args = parser.parse_args()

    try:
        from PIL import Image
    except ImportError as error:
        raise SystemExit("Pillow is needed: uv sync --extra tools") from error
    resample = {
        "nearest": Image.Resampling.NEAREST,
        "bilinear": Image.Resampling.BILINEAR,
        "bicubic": Image.Resampling.BICUBIC,
        "lanczos": Image.Resampling.LANCZOS,
    }[args.filter]

    if args.sprite.is_dir():
        sources = sorted(args.sprite.glob("*.png"))
        if not sources:
            raise SystemExit(f"No PNGs in {args.sprite}")
        folder = args.output or args.sprite
        for source in sources:
            scale_sprite(source, folder / source.name, args.new_size, resample)
    else:
        target = args.output or args.sprite
        if target.is_dir() or not target.suffix:
            target = target / args.sprite.name
        scale_sprite(args.sprite, target, args.new_size, resample)


if __name__ == "__main__":
    main()
