"""Mix 16-bit PCM wav clips into one, all starting together.

Usage: python -m minimai.tools.clip_mix out.wav clip.wav clip.wav [...]
"""

import argparse
import io
import wave
from array import array
from pathlib import Path


def mix_wavs(*clips: bytes) -> bytes:
    """The sum of the clips, as long as the longest, clipped to 16 bits."""
    params = None
    mixed = array("h")
    for data in clips:
        with wave.open(io.BytesIO(data)) as source:
            if source.getsampwidth() != 2:
                raise ValueError("Only 16-bit PCM wav can be mixed")
            if params is None:
                params = source.getparams()
            elif (source.getnchannels(), source.getframerate()) != (params.nchannels, params.framerate):
                raise ValueError("Mixed clips need the same channels and sample rate")
            samples = array("h", source.readframes(source.getnframes()))
        if len(samples) > len(mixed):
            mixed.extend([0] * (len(samples) - len(mixed)))
        for i, sample in enumerate(samples):
            mixed[i] = max(-32768, min(32767, mixed[i] + sample))
    if params is None:
        raise ValueError("No clips to mix")
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(params.nchannels)
        target.setsampwidth(2)
        target.setframerate(params.framerate)
        target.writeframes(mixed.tobytes())
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description="Mix 16-bit PCM wav clips into one, all starting together.")
    parser.add_argument("out", type=Path)
    parser.add_argument("clips", type=Path, nargs="+")
    args = parser.parse_args()
    args.out.write_bytes(mix_wavs(*(clip.read_bytes() for clip in args.clips)))


if __name__ == "__main__":
    main()
