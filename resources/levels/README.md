# Chart folders

`build_resource_levels` (in `minimai/test_level.py`) turns every folder here into levels when the
project is built:

```
resources/levels/<folder>/
    maidata.txt                required
    track.mp3 | .ogg | .wav    required; .ogg / .wav are converted to mp3
    bg.png | bg.jpg | bg.jpeg  optional, the cover
```

A folder missing `maidata.txt`, the track or any `&inote_N` is skipped with a message.

Every non-empty `&inote_N` becomes a level, named `<folder>`, or `<folder>-<N>` when the folder
has several charts.

| Level | From maidata.txt |
|---|---|
| title | `&title` (the folder name if missing) |
| artists | `&artist` |
| author | `&des_N`, else `&des` |
| rating | `&lv_N`: `13` → 13, `13+` → 13.5, `13.7` → 13.7 |
| description | `&des` |
| tags | `&genre`, `&wholebpm` |
| bgm offset | `&first_N`, else `&first` (seconds into the track where the chart starts) |
| preview | 30 s of the track from `&demo_seek`, fading out over the last 3 s; none without `&demo_seek` |

## Audio

Converting audio (.ogg tracks, previews) needs the optional `imageio-ffmpeg` package (it comes with its own ffmpeg):

```
uv sync --extra tools
```

Without it, folders with a `track.mp3/wav` are built without a preview and the others are skipped,
with a message. Converted audio is kept in `tmp/resource_levels` and reused until the source file
changes.
