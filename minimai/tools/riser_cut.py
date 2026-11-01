"""Split the touch hold riser into a charge clip and a seamless sustain loop.

Sonolus loops whole clips only, so the riser becomes two clips: the charge, which the engine loops
just so it can be cut off and swaps out after ``TOUCH_HOLD_CHARGE_DURATION``, and the sustain,
looped for as long as the touch hold lasts.

The defaults fit the usual 12 s, 48 kHz riser: its rising sweep settles into a 2.000 s repeating
cycle, and a bright layer drops out at 9.0 s, so the first clean cycle is 10.0-12.0 s. The cycle
isn't sample-periodic (noise on top), so the sustain's tail is crossfaded into the audio leading
into the loop start, which makes the wrap continue into the loop's first sample.

Usage: python -m minimai.tools.riser_cut riser.wav out_dir [--loop-start S] [--loop-length S]
       [--crossfade S] [--padding S]
"""

import argparse
import io
import math
import wave
from array import array
from pathlib import Path

from minimai.lib.effect import TOUCH_HOLD_CHARGE_DURATION

RISER_LOOP_LENGTH = 2.0
RISER_CROSSFADE = 0.5
# The engine swaps on a frame boundary, so the charge runs a little past the loop start. Its own
# continuation plays there instead of the charge wrapping back to its loud start.
RISER_PADDING = 0.5


def cut_riser(
    data: bytes,
    *,
    loop_start: float = TOUCH_HOLD_CHARGE_DURATION,
    loop_length: float = RISER_LOOP_LENGTH,
    crossfade: float = RISER_CROSSFADE,
    padding: float = RISER_PADDING,
) -> tuple[bytes, bytes]:
    """A 16-bit PCM wav riser to (charge, sustain) wav bytes. Times are in seconds."""
    with wave.open(io.BytesIO(data)) as source:
        if source.getsampwidth() != 2:
            raise ValueError("The riser must be a 16-bit PCM wav")
        channels = source.getnchannels()
        rate = source.getframerate()
        samples = array("h", source.readframes(source.getnframes()))
    frame_count = len(samples) // channels

    start, length, fade, pad = (round(value * rate) for value in (loop_start, loop_length, crossfade, padding))
    if not 0 < fade <= length or start - fade < 0 or start + length > frame_count:
        raise ValueError(
            f"Loop {loop_start}-{loop_start + loop_length} s with a {crossfade} s crossfade doesn't fit "
            f"the {frame_count / rate:.3f} s riser"
        )

    sustain = samples[start * channels:(start + length) * channels]
    for i in range(fade):
        # Equal power: the two parts aren't correlated enough for a linear fade to keep the level.
        position = (i + 0.5) / fade * math.pi / 2
        fade_in, fade_out = math.sin(position), math.cos(position)
        tail = (length - fade + i) * channels
        lead_in = (start - fade + i) * channels
        for c in range(channels):
            value = sustain[tail + c] * fade_out + samples[lead_in + c] * fade_in
            sustain[tail + c] = max(-32768, min(32767, round(value)))
    charge = samples[:min(start + pad, frame_count) * channels]

    def to_wav(frames: array) -> bytes:
        output = io.BytesIO()
        with wave.open(output, "wb") as target:
            target.setnchannels(channels)
            target.setsampwidth(2)
            target.setframerate(rate)
            target.writeframes(frames.tobytes())
        return output.getvalue()

    return to_wav(charge), to_wav(sustain)


def main():
    parser = argparse.ArgumentParser(description="Split the touch hold riser into charge and sustain clips.")
    parser.add_argument("riser", type=Path)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--loop-start", type=float, default=TOUCH_HOLD_CHARGE_DURATION)
    parser.add_argument("--loop-length", type=float, default=RISER_LOOP_LENGTH)
    parser.add_argument("--crossfade", type=float, default=RISER_CROSSFADE)
    parser.add_argument("--padding", type=float, default=RISER_PADDING)
    args = parser.parse_args()

    charge, sustain = cut_riser(
        args.riser.read_bytes(),
        loop_start=args.loop_start,
        loop_length=args.loop_length,
        crossfade=args.crossfade,
        padding=args.padding,
    )
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "touch_hold_start.wav").write_bytes(charge)
    (args.out_dir / "touch_hold_sustain.wav").write_bytes(sustain)
    print(f"Wrote touch_hold_start.wav and touch_hold_sustain.wav to {args.out_dir}")


if __name__ == "__main__":
    main()
