# Pack configs

The pack tools build Minimai's skin, effect and particle packs into `resources/<skins|effects|particles>/<name>`:

```
python main.py skin <name> <folder or zip>
python main.py effect <name> <folder or zip>
python main.py particle <name> <folder or zip>
python main.py all <name> <folder>      # <folder>/skin, <folder>/effect and <folder>/particle, each a folder or a .zip
```

The tools need the `tools` extra (`uv sync --extra tools`): Pillow for images, and the ffmpeg that imageio-ffmpeg ships for audio that has to be decoded or resampled.

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

One table per sprite: its **recipe**. Any value may be a `"$param"`. The particle pack's [sprites](#sprites-1) are made the same way. A sprite is built in three stages, each working in its own pixels:

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

## Effect

Every clip the engine plays (`Effects` in `lib/effect.py`) can have a **recipe**: its sources and the edits that make the clip. The default recipes are in [`minimai/tools/defaults/effect.toml`](../minimai/tools/defaults/effect.toml), which uses the same format as a `pack.toml`; the source's `pack.toml` is merged over it. The source is a folder or a zip file.

### Where a clip comes from

1. The `[clips."<name>"]` entry of the source's `pack.toml`, merged over the rest. Its `sources` replaces the default's whole list.
2. An audio file named exactly after the clip (`Mai Slide.wav`, `Mai Perfect Hit.ogg`, anywhere in the source), as its only source with no edits (converted only when it isn't in the clip's [format](#formats)).
3. The default recipe.

A clip whose source file is missing is left out and reported; the engine falls back or stays silent. Files no clip uses are listed. The engine plays the Mai clips and falls back to Sonolus' standard clips (`#PERFECT`, …) when a pack lacks them; the defaults pack both, so other engines can use the pack too. `#GREAT_ALTERNATIVE`, `#GOOD_ALTERNATIVE` and `#HOLD` (fallbacks for Mai Break Hit, Mai Touch Hit and Mai Touch Hold Sustain) have no default recipe, but a `pack.toml` can give them one.

Clips that come out the same share one file in `audio.zip`, so a duplicate costs only its entry in `data.json`; the same recipe is also built only once.

A recipe's `path` is a file stem (`tap_perfect`, any folder, any audio suffix) or a path with its suffix (`hits/tap.ogg`). Both are case-insensitive. The defaults read these stems:

| Clip | Stem |
|---|---|
| Mai Perfect Hit, Mai Great Hit, Mai Good Hit, Mai Ex Hit | `tap_perfect`, `tap_great`, `tap_good`, `tap_ex` |
| `#PERFECT`, `#GREAT`, `#GOOD`, `#PERFECT_ALTERNATIVE` | the same, as their fallbacks |
| Mai Break Hit, Mai Break Critical | `break_tap`, `break` |
| Mai Break Critical Hit | `break_tap` and `break` mixed |
| Mai Touch Hit, Mai Firework | `touch`, `touch_hanabi` |
| Mai Touch Hold Start, Mai Touch Hold Sustain | cut from `touch_hold_riser` |
| Mai Slide, Mai Break Slide, Mai Break Slide End | `slide`, `slide_break_start`, `slide_break_slide`, each at `$slide_gain` |
| Mai Break Slide End Critical | `slide_break_slide` (at `$slide_gain`) and `break` mixed |
| Mai Guide, Mai Count In | `answer` (at `$guide_gain`), `answer_clock` |

### Formats

Sources can be wav, mp3, ogg or flac. A clip's output **format** is `"mp3"`, `"ogg"`, `"flac"` or `"wav"`, chosen in this order:

1. The clip's `format`.
2. The pack's `format`, a top-level key of the config. The defaults leave it empty.
3. When both are empty (`""`, or left out): a clip with one source keeps that source's format, and a mix of several sources is an mp3.

A clip with one source and no edits isn't decoded: it's copied byte for byte when it's already in its format, and converted otherwise. An edited clip is encoded once, at the end (wav as 16-bit). So the defaults keep the source files as they are; a config can convert every clip, or one:

```toml
format = "ogg"                        # before any [table]

[clips."Mai Touch Hold Sustain"]
format = "wav"                        # this clip only
```

mp3 is encoded at VBR quality 2 and ogg (Vorbis) at quality 6. The mp3 files carry the encoder delay in their header, so players that read it play them without the encoder's leading and trailing silence.

PCM wav sources (8, 16, 24 or 32-bit) are edited in Python. Decoding other formats, encoding mp3, ogg and flac, and resampling (`speed`, `rate`, or mixing sources with different sample rates) go through ffmpeg. When ffmpeg is missing, only the clips that need it fail.

### `[files]`

A path the recipes use → the file to read instead. The recipes' edits stay as they are:

```toml
[files]
"break" = "hits/break_v2.ogg"
```

### `[params]`

Values recipes refer to as `"$name"`; `"-$name"` is the value negated.

| Param | Default | |
|---|---|---|
| `riser_loop_start` | 10.0 | when the engine swaps Mai Touch Hold Start for the sustain loop (`TOUCH_HOLD_CHARGE_DURATION`); the sustain loop starts there in the riser |
| `riser_loop_length` | 2.0 | the sustain loop's length: one cycle of the riser |
| `riser_crossfade` | 0.5 | the sustain's `loop` crossfade |
| `riser_charge_length` | 10.5 | Mai Touch Hold Start's length: a little past the swap, which happens on a frame boundary |
| `guide_gain`, `slide_gain` | 0.75, 0.5 | the guide and slide clips are louder than the rest |

### `[clips]`

One table per clip: its **recipe**. Any value may be a `"$param"`. Times are in seconds. A clip is built in two stages:

1. **Each source**: the file is decoded, then `trim` (with `loop`), `reverse`, `speed`, `fade`, `gain` and `pan`, in that order.
2. **The clip**: the sources are mixed, each starting at its `at`, and cut at `duration`; then `trim_silence`, `fade`, `gain` and `normalize`, in that order, and the result is encoded in the clip's `format`.

| Clip key | |
|---|---|
| `sources` | a list of [sources](#sources), mixed; a path is short for `{ path = ... }`, and a single path for a list of one |
| `duration` | the clip's length; default until the last source ends. A source still playing then is cut, with a 5 ms fade so it doesn't click |
| `rate` | the sample rate; default the highest of the sources'. The others are resampled |
| `channels` | 1 (mono) or 2 (stereo); default stereo when any source is |
| `trim_silence` | cut the silence before the sound starts: `true` (below -60 dBFS) or a threshold in dBFS. A sound that starts late feels late |
| `fade` | `[in, out]`: fade the clip in over its first `in` seconds and out over its last `out` |
| `curve` | the fades' shape: `"linear"` (default) or `"power"` (sine: keeps the loudness of two different sounds steady while they cross) |
| `gain` | an amplitude factor (`0.5` is -6 dB) |
| `normalize` | scale the clip so its peak is this many dBFS, e.g. `-1.0` |
| `format` | the clip's [format](#formats): `"mp3"`, `"ogg"`, `"flac"` or `"wav"`; `""` (default) uses the pack's |
| `skip` | `true` leaves the clip out |

#### Sources

| Source key | |
|---|---|
| `path` | a file stem or a path; a list is tried in order |
| `trim` | `[start, length]` of the file, read like the skin's `crop`: a negative start counts from the end; a length of 0 reaches the end, and a negative one stops that much short of it. Parts outside the file are silent |
| `loop` | with `trim`: crossfade the trimmed part's last `loop` seconds into the audio just before its start (equal power), so it loops without a seam |
| `reverse` | `true` plays it backwards |
| `speed` | play it this many times as fast, changing its pitch and length together: `1.1` is about 1.7 semitones up |
| `fade`, `curve` | as the clip's, on this source after its speed change |
| `gain` | an amplitude factor |
| `pan` | stereo clips: -1 keeps only the left side, 1 only the right; 0 (default) keeps both as they are |
| `at` | when it starts in the clip; default 0 |

Keys the tool doesn't know are reported and ignored. When a mix goes past full scale, the clipped samples are counted and reported; lower a `gain` or use `normalize`.

The touch hold riser becomes two clips: the charge, and a loop of the cycle after the swap:

```toml
"Mai Touch Hold Start" = { sources = [{ path = "touch_hold_riser", trim = [0, "$riser_charge_length"] }] }
"Mai Touch Hold Sustain" = { sources = [{ path = "touch_hold_riser", trim = ["$riser_loop_start", "$riser_loop_length"], loop = "$riser_crossfade" }] }
```

```toml
[params]
slide_gain = 0.4

[clips."Mai Guide"]
sources = "guide"                     # replaces the default's sources, so "answer" and its gain are gone
trim_silence = true

[clips."Mai Break Critical Hit"]      # the hit, with a shout layered 30 ms later
sources = ["break_tap", { path = "voice/break_shout.ogg", at = 0.03, gain = 0.6 }]
normalize = -1.0

[clips."Mai Count In"]                # the last 0.4 s of the guide, backwards
sources = [{ path = "answer", trim = [-0.4, 0], reverse = true, fade = [0.05, 0] }]

[clips."#HOLD"]                       # a fallback clip, which has no default
sources = [{ path = "hold_loop", trim = [1, 2], loop = 0.25 }]

[clips."Mai Firework"]
skip = true
```

## Particle

Every effect the engine plays (`BaseParticles` in `lib/particle.py`) draws a **rig**: a tree of **nodes**, each a position, rotation and scale animated over time, some with a sprite. The defaults are in [`minimai/tools/defaults/particle.toml`](../minimai/tools/defaults/particle.toml), which uses the same format as a `pack.toml`; the source's `pack.toml` is merged over it. The source is a folder or a zip file of PNG sprites.

The tool turns each sprite's movement into Sonolus particles (see [From rigs to particles](#from-rigs-to-particles)). Units: positions and sizes in skin px (the judgment ring's radius is 480), rotations in degrees counterclockwise, times in seconds from the hit.

### `[effects]`

One table per effect the engine plays. The engine spawns each on a square around the note or sensor and plays it over a fixed time (divided by the Effect Animation Speed option); the hold glow loops while the hold is held.

| Effect | Plays for | Square | Default rig and args |
|---|---|---|---|
| Mai Tap Perfect, Great, Good | 0.42, 0.35, 0.4 s | 400 px | `perfect`, `great`, `good`; `sprite = "tap_perfect"` … |
| Mai Break Perfect, Great, Good | 0.42 s | 400 px | `perfect`; `sprite = "break_perfect"` … |
| Mai Touch Perfect, Great, Good | 0.25 s | 200 px | `touch`; `circle` and `star` colours |
| Mai Hold Perfect, Great, Good, Miss | 0.3 s, looped | 240 px | `hold_glow`; `color`, `loop_copies = 3` |

The tap and break effects also play for stars, hold ends and touch hold ends.

| Key | |
|---|---|
| `rig` | the rig it draws, from [`[rigs]`](#rigs) |
| `args` | values for the rig's params (`"$name"` in the rig); merged key by key, so a config can change one |
| `loop_copies` | looped effects: copies of every particle, this many, evenly spread over the loop, so a 0.24 s ring in a 0.3 s loop with 3 copies starts every 0.1 s |
| `skip` | `true` leaves the effect out |

An effect is left out when one of its sprites is missing (and has no fallback); the engine then falls back to Sonolus' standard effects for it. Parts of a rig after the effect's end are cut.

### `[sprites]`

Sprite id → its **recipe**, made just like a skin sprite's: a `source`, a `canvas`, then `cross_section`, `tint`, `levels` and `scale` (see the skin's [`[sprites]`](#sprites), [`source`](#source), [`canvas`](#canvas), [Operations](#operations) and [Shapes](#shapes)). A path, or a list of paths tried in order, is short for `{ source = ... }`. As in the skin:

- a PNG named exactly after the sprite id (`tap_perfect.png`, anywhere in the source) is used as it is, keeping the default's `skip` and `fallback`;
- a `pack.toml` entry merges into the default recipe key by key, but its `source` replaces the default's whole `source` ([Merging](#merging));
- `[files]` maps a path the recipes use to the file to read instead ([`[files]`](#files));
- `skip = true` leaves the sprite out, and unknown keys are reported.

Particle sprites have no `transform`, and one key of their own: `fallback`, the sprite drawn instead when this one has no image (its file is missing, or it's skipped). Sprites are white or coloured; a node's `color` tints its sprite as it's drawn. The defaults:

| Sprite id (and file) | Drawn by |
|---|---|
| `tap_perfect`, `tap_great`, `tap_good` (`.png`) | Tap, star and hold hits |
| `break_perfect`, `break_great`, `break_good` | Break hits |
| `touch_circle`, `touch_star` | Touch hits |
| `touch_star_hollow` | Touch hits' hollow stars; falls back to `touch_star` |
| `hold_glow` | Held holds and touch holds |

A config can change them, or add sprites for its own rigs:

```toml
[files]
"hold_glow.png" = "fx/ring.png"                     # every recipe reading hold_glow.png reads this instead

[sprites]
spark = "fx/spark.png"
tap_great = ["tap_great.png", "tap_perfect.png"]    # the first one found
tap_perfect = { tint = "#ffd040", scale = 0.5 }     # the default file, tinted, at half size
break_perfect = { source = { path = "fx/sheet.png", crop = [0, 0, 256, 256] } }
dot = { canvas = { size = [32, 32], paint = [{ shape = "circle", radius = 12, fill = true }] } }
```

### `[texture]`, `[build]` and `[params]`

| Key | Default | |
|---|---|---|
| `texture.interpolation` | `true` | smooth the sprites when scaled |
| `texture.padding` | 1 | px of each sprite's edge repeated around it on the texture, so filtering doesn't pick up its neighbours |
| `texture.max_size` | 4096 | the texture's largest side |
| `build.max_segment_turn` | 30 | degrees; a longer turn within one stretch is cut into pieces |
| `build.color_step` | 0.1 | seconds; a changing colour is stepped this often |
| `build.ease_step` | 0.02 | seconds; a stretch whose ease no particle can follow is cut into linear pieces this long |

`[params]` holds values any rig or sprite recipe can use as `"$name"`; `"-$name"` is the value negated. The defaults have none.

### `[rigs]`

`[rigs.<name>]` is a rig's root node. A node is placed at `pos` in its parent's frame (x right, y up); its `rot` and `scale` then turn and scale its sprite and everything under it. Every key is optional:

| Node key | | Default |
|---|---|---|
| `pos` | [track](#tracks) of `[x, y]`, skin px | `[0, 0]` |
| `rot` | track, degrees counterclockwise | 0 |
| `scale` | track, a factor | 1 |
| `sprite` | a sprite id: drawn at the node | none |
| `size` | the sprite's size at scale 1, skin px: a number for a square, or `[width, height]` | 0 |
| `alpha` | track, 0–1 | 1 |
| `color` | track of colours (`"#rrggbb"` or `[r, g, b]`, 0–255): the sprite's tint | `"#ffffff"` |
| `children` | a list of nodes, drawn after (over) this one | |
| `repeat` | `{ count, rot, start, orient }`: `count` copies of the node, the first turned `start` degrees about its parent's origin, each next one `rot` more (default `360 / count`). With `orient = false` the copies keep their angle: only their positions go round | |
| `count` | the node and its children become a group of their own, spawned this many times, each with its own [random values](#random-values) | |
| `rig`, `args` | draws another rig here, under this node, with these args | |
| `params` | a rig's root only: the rig's params and their defaults | |

`"$name"` values are looked up in the args the rig is drawn with, then its `params`, then `[params]`. Each draw of a rig has its own: a rig drawn by several nodes can differ in each.

#### Tracks

A track is a constant (`rot = 30`, `pos = [0, 50]`, `color = "#ffcc00"`), or keys `[[time, value], [time, value, ease], ...]`: the value is held before the first key and after the last, and each key's ease takes it to the next key's value (default `"linear"`).

```toml
scale = [[0, 0, "outBack"], [0.15, 1.2], [0.4, 1.0]]
alpha = [[0.2, 1], [0.4, 0]]                         # full until 0.2 s, then fading out
```

The eases are Sonolus': `"linear"`, `"none"` (holds the value, then jumps at the next key), and `in`, `out`, `inOut` or `outIn` followed by `Sine`, `Quad`, `Cubic`, `Quart`, `Quint`, `Expo`, `Circ`, `Back` or `Elastic` (`"outQuad"`, `"inOutBack"`).

#### Random values

`{ random = [low, high] }` can stand for any number of a track or a size (not for times or colours). It's drawn once per spawn, between `low` and `high`. Each place draws its own value; places with the same `r = 1`–`8` share one draw, each scaled to its own range:

```toml
pos = [{ random = [-20, 20], r = 1 }, 0]
rot = { random = [-15, 15], r = 1 }                  # leans the way it's pushed
```

A particle can only add random values to its values (and, for a random turn, their sine and cosine), not multiply them. So:

- a node with a random rotation and children away from its origin must turn a whole circle (`[0, 360]`, or any range 360 wide);
- a random scale can't scale a random position or size below it;
- a group has 8 random values at most;
- a node with a `count` can't sit under random values (its copies would each draw them again).

The tool checks these and names the node that breaks one.

### From rigs to particles

A particle moves its position, size, rotation and alpha from one value to another along one ease, in one colour. So each sprite becomes a chain of particles, back to back, one for each stretch between the keys of its tracks and its ancestors':

- A stretch where a parent turns more than `max_segment_turn` is cut into pieces, so a sprite circling its parent stays on the circle (each piece moves in a straight line).
- A stretch keeps an ease when each value follows it: a node's eased `scale` scales its sprite's size and its children's offsets along that ease. When a stretch follows no one ease (two different eases at once, an eased turn moving children, or an ease cut short by another track's key), it is cut into `ease_step` pieces, each linear. Keys of eased tracks at the same times keep the particle count low.
- A changing colour is stepped every `color_step`.
- Back-to-back linear pieces that make one straight line are merged, and pieces with no alpha or no size are dropped.

Sonolus Studio can tweak single particles of the result.

### Examples

```toml
[effects."Mai Touch Great"]            # pinker stars; the rig's other args stay
args = { star = "#ff80c0" }

[effects."Mai Hold Miss"]
skip = true

[sprites]
spark = "fx/spark.png"

[effects."Mai Tap Perfect"]            # sparks flying out every way
rig = "sparks"
args = { color = "#ffe080" }

[rigs.sparks]
params = { color = "#ffffff" }
[[rigs.sparks.children]]
count = 8                              # 8 sparks, each with its own direction and size
rot = { random = [0, 360] }
[[rigs.sparks.children.children]]
pos = [[0, [40, 0], "outCubic"], [0.4, [220, 0]]]
sprite = "spark"
size = { random = [24, 48] }
alpha = [[0, 1, "inQuad"], [0.4, 0]]  # keyed with pos, so each spark is one particle
color = "$color"
```
