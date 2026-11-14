# Pack configs

The pack tools build Minimai's packs into `resources/<skins|effects|particles>/<name>`. The skin's:

```
python -m minimai.tools.skin_pack <name> <folder or zip>
```

The tools need the `tools` extra (`uv sync --extra tools`): Pillow for images.

A zip file whose files all sit in one top folder, as zipping a folder makes, is read from inside that folder.

Each source may hold a `pack.toml` (TOML). Every section and key is optional: what a config leaves out keeps the tool's default. Tables merge key by key, so a config only lists what differs.

`base`, a top-level key, names another config the `pack.toml` is merged over, as if its contents came first: a file in the source (`base = "shared.toml"`, or `"../shared.toml"` beside a source folder), else one in [`minimai/tools/defaults`](../minimai/tools/defaults) (`base = "skin_counter_header.toml"`). A list of them merges each over the one before. A base can have a base of its own.

```toml
base = "skin_counter_header.toml"     # before any [table]
```

## Localizable text

Item texts (`title`, `subtitle`, `author`, `description`, tag titles) are either a plain string or a table by language code:

```toml
title = "Minimai"
title = { en = "Minimai", ja = "ミニマイ" }
```

The pack's `item.json` keeps the form given: a string stays a string, a table stays a table. When building a collection, Sonolus picks the `en` text, or the alphabetically first language when there is no `en`.

## `[item]`

Shared by every pack.

| Key | Type | Default |
|---|---|---|
| `title` | text | the pack's name |
| `subtitle` | text | `"Minimai"` |
| `author` | text | `"Unknown"` |
| `description` | text | `""` |
| `tags` | list of text | `[]` |
| `thumbnail` | path in the source | `thumbnail.png` (or `.jpg`) in the source, else a generated one |

```toml
[item]
title = { en = "minimai-default", ja = "ミニマイデフォルト" }
subtitle = "Minimai default skin"
author = "MD"
tags = ["neon"]
thumbnail = "art/cover.png"
```

## Skin

Every sprite of the skin (`BaseSkin` in `lib/skin.py`, and the counter's [header words](#center-counter-sprites)) has a **recipe**: its source (usually a file in the skin's source) and the steps that turn it into the sprite. The default recipes are in [`minimai/tools/defaults/skin.toml`](../minimai/tools/defaults/skin.toml), which uses the same format as a `pack.toml`; the source's `pack.toml` is merged over it. The source is a folder or a zip file.

### Where a sprite comes from

1. The `[sprites."<name>"]` entry of the source's `pack.toml`, merged over the rest (see [Merging](#merging)).
2. A PNG named exactly after the sprite (`Mai Normal Note.png`, anywhere in the source), used as it is: `source = { path = "<that file>" }` with no canvas, keeping the default's `transform` and `skip`.
3. The default recipe.

A sprite whose source file is missing is left out and reported by folder. The engine skips it or falls back.

### The default folder layout

The defaults read a skin folder laid out by note type: `TapSkins/`, `StarSkins/`, `HoldSkins/`, `TouchSkins/`, `TouchHoldSkins/`, `SlideSkins/`, `WifiSkins/`, `SlideOKSkins/`, `JudgeTextSkins/`, `NoteGuideSkins/`, `sensor_outline.png` and `outline.png` (the ring). Minimai has extra sprites which come in these folders: `TouchFeedbackSkins/`, `FireworkSkins/`, `CounterSkins/`, `PreviewSkins/`. [font_render](font_render.md) and [art](arts.md) draw most of them, into these folders under these names.

The full sprite-by-sprite list is the `[sprites]` table of the defaults file.

### Center counter sprites

Each center display has its own glyph group, `Mai Counter <group> <glyph>`. Where the skin lacks one of its glyphs, that glyph is drawn from the colour group the display falls back to, `Mai Counter <colour> <glyph>`:

| Display | Group | Falls back to |
|---|---|---|
| Combo | `Combo` | Pink |
| Grade combo | `AP Plus Combo`, `AP Combo`, `FC Plus Combo`, `FC Combo`, `Miss Combo` | Gold, Yellow, Pink, Green, Silver |
| Achievement | `Triple S` (≥ 100%), `Pass S` (≥ 97%), `Pass` (≥ 80%), `Fail` | Gold, Yellow, Red, Blue |
| Borders | `Border SSS`, `Border SS`, `Border S` | Gold, Yellow, Red |
| DX score | `DX` | Green |
| DX rank | `DX High` (✧5), `DX Mid` (✧3–4), `DX Low` (✧1–2) | Gold, Red, Green |
| Life | `High Life` (none lost yet), `Mid Life` (below 100), `Low Life` (below 10), `Ended Life` (0) | Green, Yellow, Red, Silver |

The glyphs are `0`–`9`, `Dot`, `Percent`, `Plus`, `Minus` and `Star`. The life counter's backdrop is `Mai Counter <state> Ring` (`Mai Counter High Life Ring`, …), with no fallback. The defaults skip the glyphs no display draws (a combo's `Dot`, say), even when the source has them; set `skip = false` to pack one.

Each combo and achievement display also has a header word: `Mai Counter Header Combo` (the plain combo), `Mai Counter Header Combo <grade>` (`AP Plus`, `AP`, `FC Plus`, `FC`, `Miss`) and `Mai Counter Header Achievement <achievement>` (`Triple S`, `Pass S`, `Pass`, `Fail`), in `CounterSkins/counter_header_combo.png`, `counter_header_combo_ap_plus.png`, `counter_header_achievement_triple_s.png`, …. The engine doesn't draw them yet, so the defaults skip them; a `pack.toml` with `base = "skin_counter_header.toml"` packs them ([`skin_counter_header.toml`](../minimai/tools/defaults/skin_counter_header.toml) unskips them).

[font_render](font_render.md) draws every glyph and header word, and [art](arts.md) the rings.

### `[texture]`

| Key | Default | |
|---|---|---|
| `max_size` | 8192 | the largest texture side tried; the texture is the smallest power-of-two square that fits |
| `padding` | 1 | px of each sprite's edge repeated around it, so filtering doesn't pick up its neighbours |
| `interpolation` | `true` | the skin's `interpolation` |

Sprites with the same pixels share one place on the texture, so a duplicate costs only its entry in `data.json`.

### `[files]`

A source path the recipes use → the file to read instead (paths are case-insensitive). The recipes' steps stay as they are:

```toml
[files]
"TapSkins/tap.png" = "notes/my_tap.png"
```

### `[params]`

Values recipes refer to as `"$name"`; `"-$name"` is the value negated. Changing a param changes every recipe that uses it.

| Param | Default | |
|---|---|---|
| `hold_border` | 58 | the hold images' head and tail caps, in source px: the hold recipes crop the head, body and tail with it |
| `break_light`, `break_dark` | levels `1.634 × + 1.43`, `0.9 ×` | break notes pulse between these copies |
| `hold_on_light`, `hold_on_dark` | levels `1.45 ×`, `0.95 ×` | a held hold shines between these copies of its "on" image |
| `ex_tint_normal`, `ex_tint_star`, `ex_tint_each`, `ex_tint_break` | pink, cyan, yellow, yellow | EX outlines: one white image tinted per kind |
| `line_scale` | 0.5 | the note guide lines' `scale` |
| `border_bar_radius`, `border_bar_width`, `border_bar_length` | 66.5, 8, 52 | the touch hold border bars: the band's middle from the border's center (`"auto"` measures it), and the strip's size |
| `*_cell` | from `lib/layout.py` | the canvas sizes; the tool checks them against the layout |
| `bar_transform` | | the border bars' sprite transform |

New params can be added and used in any recipe.

### `[sprites]`

One table per sprite: its **recipe**. Any value may be a `"$param"`. A sprite is built in three stages, each working in its own pixels:

1. **`source`**: the file is read, and the source's operations run on it in **source px** (the file's pixels).
2. **`canvas`**: the result is fitted to the canvas, and the canvas's operations run on it in **canvas px**.
3. The sprite steps run on the canvas, in this order: `cross_section`, `tint`, `levels`, then `scale`.

| Key | |
|---|---|
| `source` | the [source](#source) table, or a path (or list of paths) as short for `{ path = ... }` |
| `canvas` | the [canvas](#canvas) table |
| `cross_section` | a strip across a touch hold border side, in canvas px: `side` (1–4, clockwise from the top-right), `width`, `length`, `radius` (the band's middle from the canvas's center, or `"auto"`) |
| `tint` | multiply the colour: `"#rrggbb"`, or `[r, g, b]` in 0–255 (0–1 when no part is over 1) |
| `levels` | `{ multiply = 1.0, add = 0 }`: `rgb × multiply + add` (0–255), alpha kept |
| `scale` | texture px per canvas px, the last step (default 1): `0.5` halves the texture, and the engine still draws the sprite at its layout size |
| `transform` | the Sonolus sprite transform (`x1`–`y4`, each a table of weights; missing weights are 0); default identity. `data.json` keeps only the non-zero weights |
| `skip` | `true` leaves the sprite out |

Keys the tool doesn't know are reported and ignored.

#### `source`

| Key | |
|---|---|
| `path` | a path in the source, or a list tried in order |
| `crop`, `paint`, `flip`, `rotate` | [operations](#operations), in source px |

A source without a `path` is **empty**: the canvas starts as a transparent image of its `size`, which then needs both sides, and the source can't have operations. A `path` that matches no file leaves the sprite out.

#### `canvas`

| Key | Default | |
|---|---|---|
| `size` | `[0, 0]` | `[w, h]` in canvas px; a 0 keeps the source's size on that axis |
| `stretch` | `false` | `false`: the source is centered on the canvas at 1 px per px, padded with transparent px or cut (the tool warns when visible pixels are cut). `true`: the source is resized to the canvas |
| `crop`, `paint`, `flip`, `rotate` | | [operations](#operations), in canvas px, after the fit |

With no canvas (or a `size` of `[0, 0]`), the canvas is the source as it is, so canvas px are source px. `stretch` only matters on an axis whose size isn't 0: the hold canvas `[122, 0]` keeps the source's height and, with `stretch`, resizes only its width.

#### Operations

`source` and `canvas` both take these. They run in this order, each in that stage's px:

| Key | | Example |
|---|---|---|
| `crop` | `[x, y, w, h]`. A negative `x` / `y` counts from the right / bottom edge; a `w` / `h` of 0 reaches the right / bottom edge, and a negative one stops that many px short of it. Parts outside the image are transparent | `[0, -58, 0, 0]`: the bottom 58 rows |
| `paint` | a list of [shapes](#shapes), drawn over the image in order | |
| `flip` | `"x"` (mirrored left to right) or `"y"` (top to bottom) | |
| `rotate` | degrees counterclockwise about the center. In the source, the image grows to fit the turned art; in the canvas, it keeps the canvas size and cuts what turns outside it | `90` |

The hold recipes cut their image into three with `crop`:

```toml
"Mai Hold Note Head" = { source = { path = "HoldSkins/hold.png", crop = [0, 0, 0, "$hold_border"] }, canvas = { size = "$hold_cell" } }
"Mai Hold Note Body" = { source = { path = "HoldSkins/hold.png", crop = [0, "$hold_border", 0, "-$hold_border"] }, canvas = { size = "$hold_cell" } }
"Mai Hold Note Tail" = { source = { path = "HoldSkins/hold.png", crop = [0, "-$hold_border", 0, 0] }, canvas = { size = "$hold_cell" } }
```

#### Shapes

Coordinates are px from the image's top-left corner, on pixel edges: pixel (0, 0) spans 0 to 1, so its center is (0.5, 0.5), and a 1 px line along the pixel row 4 is at `y = 4.5`. Fractions are fine; edges are antialiased.

| Key | Shapes | |
|---|---|---|
| `shape` | | `"line"`, `"rect"`, `"circle"` or `"polygon"` |
| `color` | all | `"#rrggbb"`, `"#rrggbbaa"`, `[r, g, b]` or `[r, g, b, a]` in 0–255; default white |
| `width` | all | the line's width, centered on it, or the outline's, drawn inside the edge; default 1 |
| `fill` | rect, circle, polygon | `true` fills the shape; `false` (default) draws its outline |
| `points` | line, polygon | `[[x, y], ...]`: a line joins them in order, a polygon also closes back to the first |
| `rect` | rect | `[x, y, w, h]`, read like `crop`; default the whole image |
| `center` | circle | `[x, y]`; default the image's center |
| `radius` | circle | |

```toml
"White Square" = { canvas = { size = [8, 8], paint = [{ shape = "rect", fill = true, color = "#ffffff" }] } }
"White Outline" = { canvas = { size = [100, 100], paint = [{ shape = "rect", width = 2, color = "#ffffff" }] } }
```

#### Merging

A `pack.toml` entry merges into the sprite's recipe key by key, like the rest of the config, with one exception: an entry's `source` replaces the recipe's whole `source`, since the default's `crop` and `paint` were written for the default file. To read another file and keep the default's steps, use `[files]`.

```toml
[sprites."Mai Normal Note"]
source = ["TapSkins/tap.png", "notes/tap.png"]   # the default's crop and paint (if any) are dropped
tint = "#ffd0f0"

[sprites."Mai Normal Touch Hold Fan 1"]
tint = [255, 80, 16]                            # white fans tinted per side

[sprites."Mai Judge Fast"]
canvas = { stretch = false }                    # keeps the default size; the default stretches it to 217 x 76

[sprites."Mai Sensor Outline"]
skip = true

[sprites."Mai Each Note"]
source = {}                                     # empty: painted on a blank 180 x 180 canvas
canvas = { paint = [{ shape = "circle", radius = 60, width = 12, color = "#ffd040" }] }
```
