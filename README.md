# Minimai Sonolus Engine

A maimai-style engine for [Sonolus](https://sonolus.com), with charts written in simai.

## Quick Dev Setup

Python 3.13 or newer is required.

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
2. Run `uv sync`, or `uv sync --extra tools` for the pack tools and for the chart folders' audio conversion and backgrounds.
3. Activate the [virtual environment](https://docs.astral.sh/uv/pip/environments/#using-a-virtual-environment) uv made in `.venv`.
4. Run `sonolus-py dev minimai.project`.
5. Connect Sonolus to the address it prints.

## Custom Resources

A pack gives the engine sprites, clips and effects by these names. Where one is missing, the engine uses its fallback (`->`) or skips it. The pack tools build packs from config ([docs/packs.md](docs/packs.md)).

- `{A, B}`: one name for each of `A` and `B`, e.g. `Mai {Normal, Each} Note` is `Mai Normal Note` and `Mai Each Note`.
- `{1..4}`: one name for each number.
- `Light` / `Dark` pairs: the light sprite pulses over the dark one.

### Skin Sprites

#### Stage

| Role | Sprite |
|---|---|
| Judgment ring | `Mai Ring` |
| Sensor outline (Sensor Alpha) | `Mai Sensor Outline` |
| Guide lines | `Mai {Normal, Each, Break, Star} Line` |
| Each ring lines | `Mai Each Ring Line {1..4}` |

#### Taps and Stars

| Note | Normal / Each | Break |
|---|---|---|
| Tap | `Mai {Normal, Each} Note` | `Mai Break Note {Light, Dark}` |
| Star | `Mai {Normal, Each} Star` | `Mai Break Star {Light, Dark}` |
| Double star | `Mai Double Star`, `Mai Each Double Star` | `Mai Break Double Star {Light, Dark}` |
| EX outline | `Mai {Normal, Each} {Note, Star} Ex Outline`, `Mai {Double Star, Each Double Star} Ex Outline` | `Mai Break {Note, Star, Double Star} Ex Outline` |

#### Holds

`<Part>` is `Head`, `Body` or `Tail`.

| Hold | Sprites |
|---|---|
| Normal | `Mai Hold Note <Part>`, held: `Mai Hold Note <Part> On {Light, Dark}` |
| Each | `Mai Each Hold Note <Part>`, held: `Mai Each Hold Note <Part> On {Light, Dark}` |
| Break | `Mai Break Hold Note <Part> {Light, Dark}`, held: `Mai Break Hold Note <Part> On {Light, Dark}` |
| Released (any) | `Mai Hold Note <Part> Off` |
| EX outline | `Mai {Hold, Each Hold, Break Hold} Note <Part> Ex Outline` |
| End point | `Mai {Hold, Each Hold, Break Hold} Note End Point` |

#### Touches and Touch Holds

| Role | Sprite |
|---|---|
| Touch fan | `Mai {Normal, Each} Touch Fan`, `Mai Break Touch Fan {Light, Dark}` |
| Touch center | `Mai {Normal, Each, Break} Touch Point` |
| Touches at one sensor | `Mai {Normal, Each, Break} Touch {2, 3} Overlap Border` |
| Just border | `Mai Touch Just Border` |
| Touch hold fan | `Mai Normal Touch Hold Fan {1..4}` |
| Touch hold border | `Mai Touch Hold Border {On, Off}`, `Mai Touch Hold Border {On, Off} Bar {1..4}` |
| Touch feedback | `Mai Touch Feedback {Ring, Petal}` |

#### Slides

| Role | Sprite |
|---|---|
| Path | `Mai Slide Path`, `Mai Each Slide Path`, `Mai Break Slide Path {Light, Dark}` |
| Wi-Fi path | `Mai {Wifi, Each Wifi, Break Wifi} Slide Path {1..11}` |
| Slide OK | `Mai Slide OK <State> <Grade>` |

`<State>` is `Curve R`, `Straight R`, `Wifi Up`, `Curve L`, `Straight L` or `Wifi Down`. `<Grade>` is `Critical Perfect`, `Just Perfect`, `{Fast, Late} {Perfect, Great, Good}` or `Too Late`.

#### Judgments

| Role | Sprite |
|---|---|
| Judgment | `Mai Judge {Critical Perfect, Perfect, Great, Good, Miss}` |
| Shine | `Mai Judge {Critical Perfect, Perfect} Shine` |
| Fast / Late | `Mai Judge {Fast, Late}`, `Mai Judge {Perfect, Great, Good} {Fast, Late}` |

#### Fireworks

| Role | Sprite |
|---|---|
| Rays | `Mai Firework Ray {1..12}` |
| Ball | `Mai Firework {Ball, Ball Pale}` |
| Sparkles | `Mai Firework Sparkle` |

#### Center Counter

`Mai Counter <Display> <Glyph>` -> `Mai Counter <Colour> <Glyph>`, and `Mai Counter {High, Mid, Low, Ended} Life Ring`. The displays, their colours and the glyphs are in [Center counter sprites](docs/packs.md#center-counter-sprites).

#### Preview

| Role | Sprite |
|---|---|
| Sensor groups | `Mai Preview Label {B, C, D, E}` |
| Slide shapes | `Mai Preview Shape {Line, Circle R, Circle L, Center, P, Q, PP, QQ, S, Z, Reflect, Wifi}` |
| Firework, each line | `Mai Preview Firework`, `Mai Preview Each Line` |

### Effect Clips

| Clip | Fallback |
|---|---|
| `Mai {Perfect, Great, Good} Hit` | `#PERFECT`, `#GREAT`, `#GOOD` |
| `Mai Ex Hit` | `#PERFECT_ALTERNATIVE` |
| `Mai Break Hit` | `#GREAT_ALTERNATIVE` |
| `Mai Break Critical` | |
| `Mai Break Critical Hit` | `Mai Break Hit` + `Mai Break Critical` |
| `Mai Touch Hit` | `#GOOD_ALTERNATIVE` |
| `Mai Firework` | |
| `Mai Touch Hold Start` | |
| `Mai Touch Hold Sustain` | `#HOLD` |
| `Mai Slide`, `Mai Break Slide` | |
| `Mai Break Slide End` | |
| `Mai Break Slide End Critical` | `Mai Break Slide End` + `Mai Break Critical` |
| `Mai Guide`, `Mai Count In` | |

### Particle Effects

| Effect | Fallback |
|---|---|
| `Mai Tap {Perfect, Great, Good}` | `#NOTE_CIRCULAR_TAP_{YELLOW, RED, GREEN}` |
| `Mai Break {Perfect, Great, Good}` | `#NOTE_CIRCULAR_ALTERNATIVE_{YELLOW, RED, GREEN}` |
| `Mai Touch {Perfect, Great, Good}` | `#NOTE_CIRCULAR_TAP_{YELLOW, RED, GREEN}` |
| `Mai Hold {Perfect, Great, Good, Miss}` | `#NOTE_CIRCULAR_HOLD_{YELLOW, RED, GREEN, NEUTRAL}` |

## Docs

| Doc | |
|---|---|
| [docs/simai.md](docs/simai.md) | The simai notation Minimai reads, with its extensions |
| [docs/level_data.md](docs/level_data.md) | The level data format: archetypes, fields and slide tracks |
| [resources/levels/README.md](resources/levels/README.md) | Chart folders built into levels: files, metadata, audio and backgrounds |
| [docs/packs.md](docs/packs.md) | The skin, effect and particle pack configs (`python main.py skin\|effect\|particle\|all`) |
| [docs/arts.md](docs/arts.md) | `art`: skin sprites drawn from shapes |
| [docs/font_render.md](docs/font_render.md) | `font_render`: skin sprites drawn from text |

`python main.py --help` lists the pack tool commands, and `python main.py clean` removes their caches and drawn sprites.
