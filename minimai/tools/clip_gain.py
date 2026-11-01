"""Scale a 16-bit PCM wav clip's volume.

Usage: python -m minimai.tools.clip_gain clip.wav out.wav GAIN
"""

import argparse
import io
import wave
from array import array
from pathlib import Path


def scale_wav(data: bytes, gain: float) -> bytes:
    """``gain`` times the amplitude (0.5 is -6 dB), clipped to 16 bits."""
    with wave.open(io.BytesIO(data)) as source:
        params = source.getparams()
        if params.sampwidth != 2:
            raise ValueError("Only 16-bit PCM wav can be scaled")
        samples = array("h", source.readframes(params.nframes))
    for i, sample in enumerate(samples):
        samples[i] = max(-32768, min(32767, round(sample * gain)))
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(params.nchannels)
        target.setsampwidth(2)
        target.setframerate(params.framerate)
        target.writeframes(samples.tobytes())
    return output.getvalue()


def main():
    parser = argparse.ArgumentParser(description="Scale a 16-bit PCM wav clip's volume.")
    parser.add_argument("clip", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("gain", type=float, help="amplitude factor; 0.5 is half (-6 dB)")
    args = parser.parse_args()
    args.out.write_bytes(scale_wav(args.clip.read_bytes(), args.gain))


if __name__ == "__main__":
    main()
