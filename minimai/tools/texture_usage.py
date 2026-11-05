"""Report how full a skin's sprite sheet is: the sprites' area / the sheet's area.

Usage: python -m minimai.tools.texture_usage <data.json> [--max-size N]

Reads the sheet size and the sprite rectangles from ``data.json``. Overlapping sprites are counted
once. With ``--max-size N`` it also compares against an N x N sheet (the largest the skin may grow
to), so you can see how much room is left.
"""

import argparse
import json
from pathlib import Path


def union_area(rects: list[tuple[int, int, int, int]]) -> int:
    """Area covered by (x, y, w, h) rectangles, overlaps counted once."""
    xs = sorted({x for x, _, w, _ in rects} | {x + w for x, _, w, _ in rects})
    area = 0
    for left, right in zip(xs, xs[1:]):
        # The rectangles spanning this column strip, merged along y.
        spans = sorted((y, y + h) for x, y, w, h in rects if x <= left and x + w >= right)
        covered, top, bottom = 0, None, None
        for start, end in spans:
            if top is None or start > bottom:
                if top is not None:
                    covered += bottom - top
                top, bottom = start, end
            else:
                bottom = max(bottom, end)
        if top is not None:
            covered += bottom - top
        area += covered * (right - left)
    return area


def percent(part: int, whole: int) -> str:
    return f"{100 * part / whole:.2f}%"


def report(data_path: Path, max_size: int | None):
    data = json.loads(data_path.read_text(encoding="utf-8"))
    width, height = data["width"], data["height"]
    rects = [(s["x"], s["y"], s["w"], s["h"]) for s in data["sprites"] if s["w"] > 0 and s["h"] > 0]
    used = union_area(rects)
    total = sum(w * h for _, _, w, h in rects)

    print(f"Sheet {width} x {height}, {len(data['sprites'])} sprites, {used:,} px occupied")
    print(f"  of the sheet: {percent(used, width * height)}, remaining {width * height - used:,} px")
    if max_size:
        whole = max_size * max_size
        print(f"  of {max_size} x {max_size}: {percent(used, whole)}, remaining {whole - used:,} px")
    if total != used:
        shared = len(rects) - len(set(rects))
        print(f"Sprites overlap by {total - used:,} px ({shared} reuse another sprite's rectangle).")
    outside = [s["name"] for s in data["sprites"] if s["x"] < 0 or s["y"] < 0 or s["x"] + s["w"] > width or s["y"] + s["h"] > height]
    if outside:
        print(f"{len(outside)} sprite(s) reach outside the sheet: {', '.join(outside)}")


def main():
    parser = argparse.ArgumentParser(description="Report how full a skin's sprite sheet is.")
    parser.add_argument("data", type=Path, help="the skin's data.json")
    parser.add_argument("--max-size", type=int, help="also compare against an N x N sheet")
    args = parser.parse_args()
    report(args.data, args.max_size)


if __name__ == "__main__":
    main()
