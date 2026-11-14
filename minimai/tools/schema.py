"""The JSON objects the pack tools read and write: the packs' ``item.json`` / ``data.json``, and the
``pack.toml`` configs (docs/packs.md)."""

from typing import Literal, NotRequired, Required, TypedDict

# A plain string, or one per language code ({"en": "Deluxe", "ja": "デラックス"}).
type LocalizableText = str | dict[str, str]

# item.json keys whose values are LocalizableText (as Sonolus' build reads them).
LOCALIZED_KEYS = {"title", "subtitle", "author", "description", "artists"}


# ==== Pack files ==================================================================================


class Tag(TypedDict):
    title: LocalizableText


class ItemJson(TypedDict):
    """``item.json`` of a skin, effect or particle pack."""

    name: NotRequired[str]
    version: int
    title: LocalizableText
    subtitle: LocalizableText
    author: LocalizableText
    tags: list[Tag]
    description: LocalizableText


# A Sonolus sprite transform: each output corner coordinate ("x1".."y4") as a weighted sum of the
# quad's corner coordinates. Missing weights are 0.
type Transform = dict[str, dict[str, float]]


class SkinSprite(TypedDict):
    name: str
    x: int
    y: int
    w: int
    h: int
    transform: Transform


class SkinData(TypedDict):
    """A skin's ``data.json``."""

    width: int
    height: int
    interpolation: bool
    sprites: list[SkinSprite]


# ==== pack.toml ===================================================================================


class ItemConfig(TypedDict, total=False):
    """``[item]``, shared by every pack."""

    title: LocalizableText
    subtitle: LocalizableText
    author: LocalizableText
    description: LocalizableText
    tags: list[LocalizableText]
    # A path in the source.
    thumbnail: str


class TextureConfig(TypedDict, total=False):
    max_size: int
    padding: int
    interpolation: bool


class Levels(TypedDict, total=False):
    multiply: float
    add: float


class CrossSection(TypedDict, total=False):
    # 1-4, clockwise from the top-right side.
    side: int
    width: int
    length: int
    radius: float | Literal["auto"]


type Size = list[int]
type Point = list[float]
# [x, y, w, h]: a negative x / y counts from the far edge, a w / h of 0 or less reaches the far edge.
type Rect = list[int]
type Color = str | list[float]


class Shape(TypedDict, total=False):
    """A shape ``paint`` draws."""

    shape: Required[Literal["line", "rect", "circle", "polygon"]]
    color: Color
    fill: bool
    width: float
    # line, polygon
    points: list[Point]
    # rect; default the whole image
    rect: Rect
    # circle; default the image's center
    center: Point
    radius: float


class Operations(TypedDict, total=False):
    """Run in this order, in the stage's px."""

    crop: Rect
    paint: list[Shape]
    flip: Literal["x", "y"]
    rotate: float


class SourceStage(Operations, total=False):
    path: str | list[str]


class CanvasStage(Operations, total=False):
    # A 0 keeps the source's size on that axis.
    size: Size
    stretch: bool


class SpriteRecipe(TypedDict, total=False):
    """A skin sprite's recipe (``[sprites."<name>"]``). Any value may be ``"$param"`` or ``"-$param"``."""

    # A path (or list) is short for { path = ... }.
    source: str | list[str] | SourceStage
    canvas: CanvasStage
    cross_section: CrossSection
    tint: Color
    levels: Levels
    # Texture px per canvas px.
    scale: float
    transform: Transform
    skip: bool


class SkinConfig(TypedDict, total=False):
    """A skin source's ``pack.toml`` (and the defaults in ``tools/defaults/skin.toml``)."""

    item: ItemConfig
    texture: TextureConfig
    # A source path the recipes use -> the file to read instead.
    files: dict[str, str]
    params: dict[str, object]
    sprites: dict[str, SpriteRecipe]
