# Minimai Flat

A skin, particle and effect pack with nothing but free sources: flat colours, white outlines, no source art. Every skin sprite is drawn by `paint` ([docs/packs.md](../../../docs/packs.md#shapes)), the text by [font_render](../../../docs/font_render.md) and the life rings, firework rays and touch feedback by [art](../../../docs/arts.md). The sounds are CC0 recordings from Freesound, cut and mixed by the effect pack's recipes.

| File | |
|---|---|
| `skin/pack.toml` | the skin's sprites |
| `particle/pack.toml` | the particle pack: taps and breaks burst in two rings of stars and spinning triangles in the grade's colour (breaks with a circle flash), touches in hexagons and triangles |
| `effect/pack.toml` | the effect pack's clips, from the sounds below |
| `font_render.toml` | the judgments, Fast / Late, the Slide OK words, the counter and the preview's labels |
| `art.toml` | the life rings and firework rays without rims, bevels or halftone dots |
| `fonts/` | M PLUS Rounded 1c Black, cut down to Basic Latin |

To build it, draw the text and art into the skin's folder, then pack:

```
uv run python -m minimai.tools.art minimai/resources/flat/skin --config minimai/resources/flat/art.toml
uv run python -m minimai.tools.font_render minimai/resources/flat/skin --config minimai/resources/flat/font_render.toml
uv run python main.py all minimai-flat minimai/resources/flat
```

The drawn folders are left out of git (`skin/.gitignore`), and `python main.py clean --drawn` removes them. The sensor outline is read from `skin/sensor_outline.png`; without it the skin has none.

## Sounds

All from [Freesound](https://freesound.org), under [CC0](https://creativecommons.org/publicdomain/zero/1.0/). WAV originals are stored as FLAC.

| File | Used for | Source |
|---|---|---|
| `effect/tap_glockenspiel.flac` | tap hits (perfect, great, good, EX) | [Glockenspiel_31_b3_04](https://freesound.org/s/348906/) by cabled_mess |
| `effect/tap_triangle.flac` | tap hits, under the glockenspiel | [triangle1](https://freesound.org/s/530022/) by harrymartin694 |
| `effect/break.flac` | break hits | [Coin Pickup SFX 1](https://freesound.org/s/646673/) by SoundDesignForYou |
| `effect/cheer.flac` | critical perfect breaks, fireworks | [Cheer 1 short](https://freesound.org/s/333405/) by jayfrosting |
| `effect/touch.flac` | touch hits | [Claps Snares 002](https://freesound.org/s/667125/) by Mo-reno-lopez |
| `effect/touch_hold_riser.flac` | the touch hold riser | [Uplifter_Sweep_10s_Three-Tones](https://freesound.org/s/349311/) by newagesoup |
| `effect/firework_whistle.flac` | fireworks | [Firework Whistlers](https://freesound.org/s/588199/) by el_boss |
| `effect/firework_crack.flac` | fireworks | [Firecracker Explosion](https://freesound.org/s/609588/) by unfa |
| `effect/slide.flac` | slides, break slides (lower) | [Whoosh Fast Pass-By](https://freesound.org/s/877978/) by Qvantor |
| `effect/guide_claps.mp3` | the guide | [Rap principal](https://freesound.org/s/442108/) by Danielito123 |
| `effect/count_in.flac` | the count-in | [Clock Ticking](https://freesound.org/s/817323/) by CAT-FOX_ALEX |
