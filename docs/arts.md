# art

Draws the skin sprites made of shapes into a folder, each where the skin's default recipe reads it (`CounterSkins/counter_high_life_ring.png`, `FireworkSkins/firework_ray_1.png`, …), so the folder can be a skin's source as it is, or be merged into one ([packs.md](packs.md)). Sprites drawn from text come from [font_render](font_render.md). The files it writes are listed in the folder's `.drawn.json`, so `python main.py clean --drawn` removes them and leaves the folder's other files.

```
python -m minimai.tools.art <folder> [--config C] [--scale S] [--only ART ...]
```

It needs the `tools` extra (`uv sync --extra tools`). How the sprites look is a config: the defaults in [`art.toml`](../minimai/tools/defaults/art.toml), with `--config` merged over them, key by key, so a config lists only what it changes:

```toml
[life_ring.states."High Life"]
color = [120, 220, 40]          # a lime ring and heart

[firework]
dot_spacing = 10                # finer halftone dots
```

## Common settings

| Key | Default | |
|---|---|---|
| `scale` | 1.0 | texture px per skin px, for every art; `--scale` overrides it |
| `supersample` | 4 | each sprite is drawn this many times bigger, then scaled down, for smooth edges |
| `<art>.skip` | | `true` leaves that art out; `--only life_ring firework` draws only those |

Sizes are in skin px, so a sprite is `size × scale` texture px. The engine draws each sprite at its size in `lib/layout.py`, whatever its texture size: a bigger size only adds detail. Where the layout fixes a size (`life_ring.size`, `firework.ray_size`), the defaults match it and the tool checks them; a config that changes one gets a warning, since the engine stretches the sprite back to its layout size.

Colours are `[r, g, b]` (or `[r, g, b, a]` where said) in 0–255.

## life_ring

`Mai Counter High Life Ring`, `Mid Life`, `Low Life` and `Ended Life`: the life counter's backdrop, drawn behind its number. From the center out:

1. a dark disc (`backdrop`), to `ring_inner`;
2. a band from `ring_inner` to `ring_outer`, edged inside and out by rims in the deep shade of the state's colour;
3. between the rims, 16 marks of 22.5°, alternating the state's colour (centered on the 8 buttons) and `mark_light`, split by dividers in the deep shade;
4. a light strip just inside the outer rim, over the marks;
5. a heart (if the state has one), its center `heart_drop` below the counter's.

The whole sprite's colours are then multiplied by `brightness` (its alpha is kept).

| Key | Default | Unit | |
|---|---|---|---|
| `size` | 276 | skin px | the sprite's side (`COUNTER_LIFE_SIZE`) |
| `ring_inner`, `ring_outer` | 93, 135 | skin px from the center | the band's inner and outer edges |
| `ring_rim` | 6.0 | skin px | each rim's width |
| `light_strip` | 7.0 | skin px | the light strip's width, inside the outer rim |
| `mark_gap` | 5.0 | skin px | the dividers' width |
| `mark_light` | `[240, 236, 238]` | colour | the light marks and the strip |
| `deep_shade` | 0.75 | factor | the rims and dividers: the state's colour times itself (`c × c / 255`), times this. Green stays a dark green, yellow turns orange |
| `backdrop` | `[8, 4, 4, 220]` | colour with alpha | the disc inside the band |
| `brightness` | 0.68 | factor | every colour of the finished sprite |
| `states` | see below | | by state name: its `color` and `heart_width` |
| `heart_drop` | 8 | skin px | how far below the counter's center the heart's box is centered |

`states` has one table per life state; a state left out of a config keeps its default:

| State | `color` | `heart_width` |
|---|---|---|
| `"High Life"` | `[64, 196, 92]` | 147 skin px |
| `"Mid Life"` | `[250, 208, 40]` | 115 skin px |
| `"Low Life"` | `[228, 92, 78]` | 73 skin px |
| `"Ended Life"` | `[146, 154, 170]` | none |

`heart_width` is the heart's width; 0, or none, draws no heart.

The heart is a gradient of the state's colour, top to bottom, with a rim and a light bevel round its edge. The rim and bevel are measured in parts of the way from the heart's edge (0) to its middle (1).

| Key | Default | Unit | |
|---|---|---|---|
| `heart_warm` | `[255, 236, 80]` | colour | what the top is warmed toward |
| `heart_top_warmth` | 0.3 | 0–1 | how far the top's colour moves toward `heart_warm` |
| `heart_bottom_depth` | 0.6 | 0–1 | how far the bottom's colour moves toward the deep shade |
| `heart_shade` | 0.82 | factor | both ends of the gradient, times this |
| `heart_alpha` | 255 | 0–255 | the heart's opacity |
| `heart_rim` | 0.06 | part of the way in | a rim in the deep shade, from the edge to here |
| `heart_bevel` | 0.16 | part of the way in | a light bevel from the edge to here… |
| `heart_bevel_fade` | 0.08 | part of the way in | …fading out over this much more (0: ending sharply) |
| `heart_bevel_light` | 0.15 | 0–1 | how far the bevel moves toward white |

## each_line

`Mai Preview Each Line`: the preview's line joining notes hit together. A horizontal band in one colour, solid across its middle and fading to clear at its top and bottom edges. It's the same all along, so the engine can stretch it to any length.

| Key | Default | Unit | |
|---|---|---|---|
| `size` | `[16, 16]` | skin px | the texture's width and height; the engine stretches it, so this only sets its resolution |
| `color` | `[255, 222, 64]` | colour | the band |
| `core` | 0.5 | part of the height | the solid middle; from its edges, the alpha falls straight to 0 at the band's edges |

## firework

`Mai Firework Ray 1`–`12`, `Mai Firework Ball Pale` and `Mai Preview Firework`.

**The rays.** Each is a wedge, its tip at the bottom middle of the sprite (the firework's center) and its wide end at the top. Ray *n* has the hue (*n* − 1) × 30°: ray 1 red, ray 5 green, ray 9 blue. A ray is a dark shade of its hue, with halftone dots of the full colour. The dots start as points partway along it and grow until they merge into a solid bright end. Along its length (0 at the tip, 1 at the end), the ray fades in from the tip and out at the end.

| Key | Default | Unit | |
|---|---|---|---|
| `ray_size` | `[88, 552]` | skin px | the ray sprite's width and height (`FIREWORK_RAY_SIZE`) |
| `saturation`, `value` | 0.8, 0.92 | 0–1 | the full colour, in HSV |
| `dark_value` | 0.45 | factor | the dark shade: the full colour's value times this |
| `fade_in_end` | 0.15 | along the ray | fully opaque from here (a smooth fade in from the tip) |
| `fade_out_start` | 0.88 | along the ray | fading out from here to the end |
| `dots_start` | 0.3 | along the ray | where the dots start, as points |
| `dots_merged` | 0.82 | along the ray | where they have grown to touch; solid colour from here on |
| `dot_spacing` | 13 | skin px | between dots, in a staggered grid |
| `dot_merged_radius` | 0.62 | × `dot_spacing` | a dot's radius where they merge |

**The pale ball** (`pale_ball`): a soft round glow, full from the middle to a tenth of its radius, then fading smoothly to clear at its edge.

| Key | Default | Unit | |
|---|---|---|---|
| `pale_ball.size` | 512 | skin px | its side |
| `pale_ball.color` | `[255, 238, 246]` | colour | a white-pink |
| `pale_ball.alpha` | 0.9 | 0–1 | its opacity in the middle |

**The preview's halo** (`preview`): all twelve rays in one square, as the preview shows them behind a note. Ray 1 points up, the rest follow every 30° clockwise. Each is a plain wedge aimed at the center, in a single paler colour: no dark shade, dots or fading. A disc in the middle is left clear, so the halo doesn't show through the note.

| Key | Default | Unit | |
|---|---|---|---|
| `preview.size` | 128 | skin px | its side |
| `preview.hole` | 0.5 | part of the radius | the clear disc in the middle |
| `preview.ray_width` | 0.2 | part of the radius | each ray's width at the edge |
| `preview.saturation`, `preview.value` | 0.6, 0.95 | 0–1 | the rays' colours, in HSV |

## touch_feedback

`Mai Touch Feedback Ring` and `Mai Touch Feedback Petal`, both white: the engine draws them as they are, fading them out.

**The ring** is a disc whose alpha follows its distance from the center (0 at the center, 1 at its edge). It is faint in the middle and grows toward a thin bright rim at 0.9 (`TOUCH_FEEDBACK_RING_RIM`, fixed by the layout), with a little glow past it. In the middle the alpha is `gradient_base`, rising to `gradient_base + gradient_rise` at the rim along `(distance / 0.9) ^ gradient_power`. The rim is a soft line of full alpha, `rim_width` wide; past it, a glow of 0.3 alpha fades out over `glow_width`.

| Key | Default | Unit | |
|---|---|---|---|
| `size` | 256 | skin px | the ring's side; the petal is `size / 4` wide and `size / 2` tall |
| `gradient_base` | 0.15 | alpha, 0–1 | in the middle |
| `gradient_rise` | 0.4 | alpha, 0–1 | added by the time it reaches the rim |
| `gradient_power` | 2.5 | | how late the rise comes: 1 is even, higher keeps the middle faint longer |
| `rim_width` | 0.018 | part of the half size | the rim's softness (a Gaussian's width) |
| `glow_width` | 0.04 | part of the half size | how far the glow past the rim fades |

**The petal** is a droplet pointing up (out from the feedback's center), with soft edges. It's an ellipse made wider at its inner (bottom) end and narrower at its outer end.

| Key | Default | Unit | |
|---|---|---|---|
| `petal_taper` | 0.3 | | how much wider the inner end is, and narrower the outer; 0 is a plain ellipse |
