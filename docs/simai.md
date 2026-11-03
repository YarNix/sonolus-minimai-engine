# simai notation in Minimai

Whitespace (spaces, tabs, line breaks) is ignored everywhere.

## Timing

| Syntax | Meaning |
|---|---|
| `,` | One time unit. Notes before a comma are placed at the current time; the comma moves time forward. |
| `(120)` | Set the BPM. |
| `{8}` | Each comma is an 8th note (`4 / 8` beats). Default `{4}`. |
| `{#0.25}` | Each comma is 0.25 seconds (at the current BPM). |
| `E` | End of chart; the rest is ignored. |

Text after the last comma is placed but doesn't move time forward.

```
(120){4}1,2,3,4,{8}5,6,7,8,
```

## Notes

| Syntax | Note |
|---|---|
| `1` .. `8` | Tap on a button. |
| `1b` | Break. |
| `1x` | EX. Combines with `b` in any order: `1bx`. |
| `1$` | Star-shaped tap, no spin. |
| `1$$` | Star-shaped tap, spinning. |
| `5h[2:1]` | Hold. `5h` without a length is a zero-length hold. Combines with `b` and `x`. |
| `B1`, `D4`, `E8` | Touch. `C`, `C1`, `C2` are all the center. |
| `Cb` | Break touch. |
| `Cf` | Touch with a firework. On other notes see [Fireworks](#fireworks-extension-note_fireworks). |
| `Ch[4:3]` | Touch hold. `Ch` without a length is a zero-length touch hold. Combines with `b` and `f`. |

### Together

| Syntax | Meaning |
|---|---|
| `1/5` | Notes at the same time. |
| `15` | Short form for plain taps. |
| `` 1`2 `` | Pseudo-each: `2` is placed 1 ms after `1`, and isn't an each. |

EACH colouring:

* Taps, holds, touches and slide heads are each when more than one of them is at the same time.
* Slides are each when more than one slide track is at the same time.
* Break overrides each.

## Lengths

Used by holds and slides.

| Syntax | Length | Slide wait |
|---|---|---|
| `[8:3]` | 3 eighth notes | 1 beat |
| `[160#8:3]` | 3 eighth notes at BPM 160 | 1 beat at BPM 160 |
| `[#1.5]` | 1.5 seconds | 1 beat |
| `[160#1.5]` | 1.5 seconds | 1 beat at BPM 160 |
| `[3##1.5]` | 1.5 seconds | 3 seconds |
| `[3##8:3]` | 3 eighth notes | 3 seconds |
| `[3##160#8:3]` | 3 eighth notes at BPM 160 | 3 seconds |


## Slides

```
<start>[head options]<shape><end>[length][b][f]
```

### Shapes

| Shape | Track |
|---|---|
| `1-5` | Straight line. End must be at least 2 buttons away. |
| `1>4`, `1<6` | Arc along the ring. `>` goes right as seen at the top: clockwise from buttons 7, 8, 1, 2, counter-clockwise from 3–6. `<` is the opposite. |
| `1^4` | The shorter arc. End can't be the start or the opposite button. |
| `1v4` | Through the center. End can't be the opposite button. |
| `1p4`, `1q4` | Curve around the center: `p` counter-clockwise, `q` clockwise. |
| `1pp4`, `1qq4` | Large curve passing the center; `qq` is the mirror of `pp`. |
| `1s5`, `1z5` | Zig-zag to the opposite button; `z` is mirrored. |
| `1V75` | Two lines turning at button 7 (or 3); the turn must be 2 buttons from the start. |
| `1w5` | Wi-Fi to the opposite button. |

### Head options

| Syntax | Meaning |
|---|---|
| `1-5[4:1]` | Star head. |
| `1b-5[4:1]` | Break star head (the slide itself isn't break). |
| `1x-5[4:1]` | EX star head. |
| `1@-5[4:1]` | Tap head instead of a star. |
| `1?-5[4:1]`, `1!-5[4:1]` | No head. `!` is treated like `?`. |
| `1-5[4:1]b` | Break slide. `b` may also go before the length. |

### Same head

`*` adds tracks that share the head. The star becomes a double star, and only the first track has a head:

```
1-4[4:3]*-6[8:5]
```

### Chains

Shapes can be chained; each segment starts where the previous one ends:

```
1-4q7-2[1:2]
1-4[2:1]q7[2:1]-2[1:1]
```

Lengths are summed along the chain, and the star travels the whole chain at a constant speed (split by bar count). Giving only the last length or every length gives the same result when they add up to the same total. `b` anywhere in the chain makes the whole slide break.

## Wi-Fi branches (extension `wifi_multi_chain`)

A Wi-Fi has three ends: center (start + 4), left (start + 5) and right (start + 3). For `1w5` those are 5, 6 and 4. A chain continues from the center as usual. `~` adds up to two branches continuing from the left and right ends:

```
<start>w<end>[center chain] [~[side]<branch chain>] [~[side]<branch chain>]
```

* Without a side button, a branch takes the Wi-Fi's first unused side: left, then right.
* A side button right after `~` picks the side by its end button. It's always a digit, and a track never starts with one, so it can't be misread.
* An empty `~` (or `~<side>` with nothing after it) skips that side.
* A branch chain starts at its side's end button and follows the normal chain rules. It may contain another Wi-Fi (see [Nesting](#nesting)).
* A branch with no length gets whatever the center chain has left after the Wi-Fi, so both paths end together. Otherwise its lengths are added to the lengths up to and including the Wi-Fi.
* `b` in any branch makes the whole slide break.
* Segments after a Wi-Fi start once the Wi-Fi has at most one area left across all three of its stars. Touching one of them finishes the whole Wi-Fi.

| Example | Meaning |
|---|---|
| `1w5-1[2:1]` | Wi-Fi 1→5, then straight 5→1. |
| `1w5-1[2:1]~^1` | …and the left branch arcs 6→1. |
| `1w5-1[2:1]~^1~^1` | …and both branches arc to 1. |
| `1w5-1[2:1]~4^1` | Right branch only, picked by its end button 4. |
| `1w5-1[2:1]~6^1` | Left branch only, picked by its end button 6. |
| `1w5-1[2:1]~~^1` | Left skipped, right branch arcs 4→1. |
| `1w5-1[2:1]~4^1~^1` | Right picked first; the plain `~` takes the unused left. |
| `1w5[2:1]-1[2:1]~^1[1:1]` | Center path 4 beats, left path 2 + 4 = 6 beats. |

### Nesting

Branches go to Wi-Fi through a stack:

1. The Wi-Fi of the main chain are pushed in written order, so the last one is on top.
2. Each `~` goes to the Wi-Fi on top. A Wi-Fi is popped once both of its sides are used.
3. A `~` with a side button first pops every Wi-Fi that doesn't have that end button, so it reaches the nearest Wi-Fi that does.
4. A branch containing a Wi-Fi pushes it, so the following `~` go to that inner Wi-Fi first.

| Example | Meaning |
|---|---|
| `1w5w1[4:1]~6^1` | `5w1` has no end 6 and is popped; the branch is the left side of `1w5`. |
| `1w5w1[4:1]~~~^1` | The same, by skipping both sides of `5w1`. |
| `1w5-1[2:1]~^1w5~-1` | Left branch `^1w5`; the next `~` goes to that inner Wi-Fi, so its left branch is `-1`. |
| `1w5-1[2:1]~^1w5~~~-1` | The inner Wi-Fi's sides are skipped, so `-1` is the outer Wi-Fi's right branch. |

When two Wi-Fi on the stack share an end button (`~^1w5` above starts at 1 again), a side button picks the one on top. Skip the inner Wi-Fi's sides to reach the outer one.

### Notes

* A Wi-Fi with branches but no center continuation still has its center star, which holds back the branches, but the center isn't judged on its own. Only the slides at the end of each path are judged, one judgment per path.

## Fireworks (extension `note_fireworks`)

`f` adds a firework to taps, holds and slides, the way it does to touches. It goes where `b` goes.

| Example | Firework |
|---|---|
| `1f`, `1$f` | Tap, star. |
| `1hf[4:1]`, `1h[4:1]f` | Hold, when it ends. |
| `1f-5[4:1]` | Slide head. |
| `1-5[4:1]f` | Slide end, when the star arrives. |
| `1-5[4:1]f*-3[4:1]` | Each `*` track has its own: only the `-5` end. |
| `1-3-5[4:1]f` | A chain: after its last segment only. |

Wi-Fi:

* `f` right after a Wi-Fi's end (and length), before its center chain or the first `~`, puts a firework on every path's end after it. A Wi-Fi that is the last segment has one firework, at its center end.
* Otherwise each path declares its own, after its last segment.

| Example | Firework |
|---|---|
| `1w5[4:1]f` | The center end. |
| `1w5f-1[2:1]~^1~^1` | Every path's end. |
| `1w5-1[2:1]f~^1~^1` | The center path's end only. |
| `1w5-1[2:1]~^1f~^1` | The left path's end only. |

A headless slide with a head `f` (`1?f-5[4:1]`) is an error.

## Extensions

Extensions must be declared in `maidata.txt`, or `LevelBuilder.parse_maidata` rejects them. `&feat_ext` is a comma-separated list:

```
&title=Example
&feat_ext=wifi_multi_chain,note_fireworks
&inote_5=(120){4}
1w5-1[2:1]~^1f,
E
```
