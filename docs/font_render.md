# font_render

```
python -m minimai.tools.font_render <folder> [--config C] [--font F] [--scale S]
```

Draws sprites from text into a folder, each where the skin's default recipe reads it (`CounterSkins/counter_combo_0.png`, `PreviewSkins/preview_label_b.png`, …), so the folder can be a skin's source as it is, or be merged into one ([packs.md](packs.md)); a sprite the skin has no recipe for (a config's own) is written as `<sprite name>.png`. By default it draws the center counter's glyphs and header words ([the sprites](packs.md#center-counter-sprites)), and the preview's sensor group marks and slide shape labels. It needs the `tools` extra (`uv sync --extra tools`) and a font: `font` in the config (relative to the config file) or `--font`; groups without one are skipped. The files it writes are listed in the folder's `.drawn.json`, so `python main.py clean --drawn` removes them and leaves the folder's other files.

What it draws, and how, is a config: the defaults in [`font_render.toml`](../minimai/tools/defaults/font_render.toml), with `--config` merged over them. `--font` and `--scale` override the config's. Sizes are in px, 1 texture px at `scale` 1 (skin px for the counter); the counter's cells are checked against `lib/layout.py`, and the tool warns when a config changes one, since the engine stretches the sprite to its layout size anyway.

## Sprite groups

`[[sprite_groups]]` lists the groups. A config's groups merge into the defaults' by `name`, so restyling one group takes only its changed keys; a group of a new name is added.

| Key | |
|---|---|
| `name` | the sprites' names, with `{sprite}` for each sprite's own name: `"Mai Counter Combo {sprite}"` |
| `look` | a [look](#looks) to start from |
| `sprites` | the sprites: tables, or lists of them (`"$counter_glyphs"`, `["$preview_group_labels", { name = "A", lines = "A" }]`) |
| `glyph_style` | [character styles](#glyph-styles) for this group |
| `skip` | `true` leaves the group out |
| any property | for every sprite of the group |

Each sprite is a table of properties, with at least a `name`, its [`lines`](#lines) and its `cell`.

`[params]` holds values the config refers to as `"$name"` (`"-$name"` negated), such as the shared sprites (`counter_glyphs`, `counter_combo_header`, `counter_achievement_header`, `preview_group_labels`, `preview_shape_labels`) and the layout's cells.

## Where a property comes from

From the least to the most specific: `[defaults]`, the group's look (and the looks it starts from), the group, the sprite, then the [line](#lines). A character's own properties then come from the top-level `[glyph_style]`, the group's, the sprite's and the line's. Tables merge key by key; `false` turns off a table or colour property (`shine = false`, `counter_fill = false`).

## Lines

A sprite's text is in its `lines`: one or more lines, each laid out on its own in a `box` of the cell and drawn over the lines before it. A line takes every property of its sprite and can set its own (its `size`, `fill`, `outlines`, alignment, …), except the sprite's own `cell`, `scale`, `supersample`, `opacity` and `brightness`.

| Key | |
|---|---|
| `text` | what the line says; only a line has text |
| `box` | `[x, y, w, h]` px in the cell; default the whole cell. The line is laid out in it as a one-line sprite in its cell: centered, at its `margin`, shrunk to its width, … Outlines and shadows past the box are kept, up to the cell's edges |
| `skip` | `true` leaves the line out |

`lines = "0"` is short for `lines = [{ text = "0" }]`, and in a list a string is short for a line with that text. A look's, a group's and a sprite's `lines` merge by index, line 1 over line 1 and so on, so a group can place its lines and each sprite fill in their text:

```toml
[params]
grades = [
    { name = "Fast Good", lines = ["FAST", { text = "GOOD", fill = [79, 214, 106] }] },
    { name = "Too Late", lines = ["TOO LATE", { skip = true }] },
]

[[sprite_groups]]
name = "Mai Slide OK Straight R {sprite}"
sprites = "$grades"
cell = [428, 140]
lines = [
    { box = [30, 17, 352, 70], align_x = "right", margin = 5, size = { ink_height = 29, reference = "H" } },
    { box = [30, 92, 352, 26], align_x = "right", margin = 7, size = { ink_height = 19, reference = "H" } },
]
```

## Looks

`[looks.<name>]` are named sets of properties for groups to share. A look can start from another with `look = "<name>"`: the defaults' colour looks (`Yellow`, `Pink`, …) start from `Counter`, which has the counter's size, outline, counters and edge.

## Glyph styles

`glyph_style` maps a character to its own properties, looked up after `case`:

```toml
[glyph_style]
"✧" = { shape = "star", power = 3 }      # the font has none: draw an astroid
"7" = { fill_hooks = false }             # this font's 7 fools the hook filling
"%" = { font = "fonts/Fallback.otf" }
```

## Character properties

A sprite or group sets these for all its characters; a glyph style overrides them per character.

| Key | |
|---|---|
| `font`, `font_index` | a .ttf / .otf / .ttc, and the face in a collection |
| `variation` | a variable font's axes by name (`{ Weight = 800 }`), or a named instance (`"Bold"`) |
| `stretch_x`, `skew` | widen or narrow (`0.9`), slant (degrees, to the right) |
| `bolden` | thicken the strokes by this many px |
| `offset` | `[x, y]` px, after layout |
| `advance` | the character's width in px, instead of the font's |
| `left`, `right` | px added before and after it |
| `fill_counters` | fill its holes (`0`, `8`) |
| `fill_hooks` | `{ radius, room_width, enclosure }`: also bridge hook openings (`2`, `3`), keeping a room the glyph makes up `enclosure` of the edge of; implies `fill_counters`; `false` for none |
| `shape` | draw a shape instead of the font: `"star"` (with `power`), `shape_size` times the reference's ink height, centered on the cell's middle line |

## Sprite properties

A sprite or group sets these for its lines, and a line can set its own; for a line, the cell (in alignment, `fit` and `overflow`) is its box.

| Key | Default | |
|---|---|---|
| `lines` | | the sprite's [lines](#lines) |
| `case` | | `"upper"` / `"lower"` |
| `cell` | | `[w, h]` px: the sprite's size |
| `size` | | `{ ink_height = 56, reference = "1" }`: the font sized so the reference's ink is that tall; or `{ em = 72 }` |
| `features` | | OpenType features for the whole text (`["tnum"]`); needs Pillow built with Raqm |
| `tracking`, `kerning` | | px between characters; per pair (`{ "AV" = -3 }`), on top of the font's own kerning |
| `align_x` | `"advance"` | `"advance"` (the text's advance centered, keeping the font's offsets: a `1` sits left), `"ink"` (its ink centered), `"left"` / `"right"` (at `margin`) |
| `align_y` | `"reference"` | `"reference"` (the reference's ink centered on the cell), `"baseline"` (at `baseline` px from the top), `"ink"` (its ink centered) |
| `margin` | 0 | px kept clear at the sides |
| `fill_scope` | `"character"` | `"character"`: holes and hooks are filled character by character, each with its own `fill_counters` / `fill_hooks`; `"sprite"`: once, on the whole text, with the sprite's (a gap between two letters can then be filled too) |
| `fit` | | `"width"`: stretch the text to fill the cell's width, less the margins, outlines and `bolden` |
| `overflow` | `"shrink"` | when the outlined text is wider than the cell: `"shrink"`: moved back inside when it's narrow enough (a `"left"` text whose first letter reaches left of its advance), else shrunk (a smaller `size`, just enough to fit), `"shrink_group"` (every sprite of the group to the size its widest one needs, line by line, so a set stays even), `"warn"` and cut its sides, or `"cut"` quietly |
| `outlines` | | `[{ width, color }, ...]`, stacked outward |
| `shadow` | | `{ offset = [x, y], blur, color = [r, g, b, a] }` under everything |
| `fill` | white | the text's colour |
| `counter_fill` | | the filled-in holes and hooks' colour |
| `shine` | | `{ tone = "light" / "dark", amount, reach, fade }`: a tint `amount` of the way to white or black, from the top left out to `reach` of the diagonal, fading over `fade` |
| `pattern` | | `{ kind = "checker" / "stripes", size, shade }`: squares or `\` stripes `size` px, the colour under them times `shade` |
| `edge` | | `{ width, shade }`: a darker edge inside the fill |
| `opacity`, `brightness` | 1 | the finished sprite's alpha and colours, times these |
| `scale`, `supersample` | 1, 4 | texture px per px; drawn this many times bigger, then scaled down |
| `skip` | | `true` leaves the sprite out |

Each line of a sprite is drawn in this order, then painted over the lines before it: the text is laid out as one run (with its features and the font's kerning) and each character is placed and drawn; the characters are aligned, and fitted to the box (a run to fit is drawn on a canvas of its own width, then resized); each character's holes and hooks are filled (or, with `fill_scope = "sprite"`, the whole text's); the outlines and shadow go round the whole; and it's painted. Text whose characters all share their settings, with no spacing changes, filled as a whole, is drawn in one call, as the font lays it out.

To give a display a look of its own, add a look and point its group at it:

```toml
font = "fonts/MyFont.otf"

[looks.Rainbow]
look = "Counter"
fill = [180, 120, 255]
pattern = { kind = "stripes", size = 6.0, shade = 0.85 }
shine = { tone = "light", amount = 0.5, reach = 0.3, fade = 0.12 }

[[sprite_groups]]
name = "Mai Counter AP Plus Combo {sprite}"
look = "Rainbow"
```
