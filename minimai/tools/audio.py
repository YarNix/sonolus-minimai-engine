"""Audio steps shared by the tools: decoding, trimming, fading, mixing and writing clips.

PCM wav is read and edited in plain Python. Other formats and resampling go through the ffmpeg that
imageio-ffmpeg ships (``uv sync --extra tools``), imported only when a step needs it.
"""

from __future__ import annotations

import io
import math
import subprocess
import sys
import tempfile
import wave
from array import array
from dataclasses import dataclass
from pathlib import Path

# A clip cut short by its duration fades out over this long, so the cut doesn't click.
CUTOFF_FADE = 0.005
# The output formats, with their ffmpeg encoder arguments.
ENCODERS = {
    "mp3": ["-codec:a", "libmp3lame", "-q:a", "2"],
    "ogg": ["-codec:a", "libvorbis", "-q:a", "6"],
    "flac": ["-codec:a", "flac"],
    "wav": ["-codec:a", "pcm_s16le"],
}


@dataclass
class Audio:
    rate: int
    # One array per channel, samples in -1..1.
    channels: list[array]

    @property
    def frames(self) -> int:
        return len(self.channels[0])

    def with_channels(self, channels: list[array]) -> Audio:
        return Audio(self.rate, channels)


def to_frames(audio: Audio, time: float) -> int:
    return round(float(time) * audio.rate)


# ==== ffmpeg ======================================================================================


def has_ffmpeg() -> bool:
    try:
        import imageio_ffmpeg  # noqa: F401
    except ImportError:
        return False
    return True


def ffmpeg_exe(reason: str) -> str:
    """The ffmpeg executable, or a ValueError saying that ``reason`` needs it."""
    try:
        import imageio_ffmpeg
    except ImportError as error:
        raise ValueError(f"{reason} needs imageio-ffmpeg (uv sync --extra tools)") from error
    return imageio_ffmpeg.get_ffmpeg_exe()


def run_ffmpeg(exe: str, source: Path, target: Path, args: list[str]):
    subprocess.run([exe, "-y", "-loglevel", "error", "-i", str(source), *args, str(target)], check=True)


def ffmpeg_bytes(data: bytes, args: list[str], suffix: str, reason: str) -> bytes:
    """``data`` (any format ffmpeg reads) through ffmpeg ``args``. The output is a file, not a pipe, so
    encoders can write their headers (an mp3's encoder delay, for gapless playback)."""
    exe = ffmpeg_exe(reason)
    with tempfile.TemporaryDirectory() as folder:
        source, target = Path(folder) / "source", Path(folder) / f"target.{suffix}"
        source.write_bytes(data)
        run_ffmpeg(exe, source, target, [*args, "-vn"])
        return target.read_bytes()


def through_ffmpeg(data: bytes, args: list[str], reason: str) -> Audio:
    """``data`` through ffmpeg ``args``, read back as 32-bit PCM."""
    audio = read_wav(ffmpeg_bytes(data, [*args, "-codec:a", "pcm_s32le", "-f", "wav"], "wav", reason))
    if audio is None:
        raise ValueError("ffmpeg wrote no PCM wav")
    return audio


def convert(data: bytes, format: str, reason: str) -> bytes:
    """``data`` (any format ffmpeg reads) in ``format`` (a key of ``ENCODERS``)."""
    return ffmpeg_bytes(data, [*ENCODERS[format], "-f", format], format, reason)


# ==== Reading and writing =========================================================================


def read_wav(data: bytes) -> Audio | None:
    """A PCM wav (8, 16, 24 or 32-bit integer), or None for anything else."""
    try:
        with wave.open(io.BytesIO(data)) as source:
            width, count, rate = source.getsampwidth(), source.getnchannels(), source.getframerate()
            raw = source.readframes(source.getnframes())
    except (wave.Error, EOFError):
        return None
    if width == 1:
        samples, scale, offset = array("B", raw), 1 / 128, 128
    elif width == 2:
        samples, scale, offset = array("h", raw), 1 / 32768, 0
    elif width in (3, 4):
        if width == 3:
            # Each 24-bit sample as the top three bytes of a 32-bit one.
            padded = bytearray(len(raw) // 3 * 4)
            for byte in range(3):
                padded[byte + 1 :: 4] = raw[byte::3]
            raw = bytes(padded)
        samples, scale, offset = array("i", raw), 1 / 2**31, 0
    else:
        return None
    if sys.byteorder == "big" and width > 1:
        samples.byteswap()
    channels = [array("d", ((value - offset) * scale for value in samples[c::count])) for c in range(count)]
    return Audio(rate, channels)


def decode(data: bytes, name: str) -> Audio:
    """A clip in any format: PCM wav directly, the rest through ffmpeg."""
    audio = read_wav(data)
    if audio is not None:
        return audio
    return through_ffmpeg(data, [], f"Decoding {name} (not a PCM wav)")


def clipped(audio: Audio) -> int:
    """How many samples are past full scale, and get clipped when written."""
    return sum(1 for channel in audio.channels for value in channel if not -32768 <= round(value * 32768) <= 32767)


def write_wav(audio: Audio) -> bytes:
    """16-bit wav bytes."""
    count = len(audio.channels)
    samples = array("h", bytes(2 * audio.frames * count))
    for c, channel in enumerate(audio.channels):
        samples[c::count] = array("h", (max(-32768, min(32767, round(value * 32768))) for value in channel))
    if sys.byteorder == "big":
        samples.byteswap()
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(count)
        target.setsampwidth(2)
        target.setframerate(audio.rate)
        target.writeframes(samples.tobytes())
    return output.getvalue()


def encode(audio: Audio, format: str) -> bytes:
    """``audio`` as a file in ``format`` (a key of ``ENCODERS``): wav directly, the rest through ffmpeg."""
    if format == "wav":
        return write_wav(audio)
    return convert(write_wav_32(audio), format, f"Encoding {format}")


def resample(audio: Audio, rate: int, speed: float = 1.0) -> Audio:
    """``audio`` at ``rate`` samples per second, played ``speed`` times as fast (pitch and length change
    together)."""
    if rate == audio.rate and speed == 1:
        return audio
    data = write_wav_32(audio)
    played = max(1, round(audio.rate * speed))
    reason = "Changing the speed" if speed != 1 else f"Resampling {audio.rate} Hz to {rate} Hz"
    return through_ffmpeg(data, ["-af", f"asetrate={played},aresample={rate}"], reason)


def filtered(audio: Audio, *, highpass: float | None = None, lowpass: float | None = None, slope: int = 12) -> Audio:
    """``audio`` high-passed (cut below ``highpass`` Hz) and low-passed (cut above ``lowpass`` Hz), ``slope`` dB
    per octave: a 12 dB per octave filter run ``slope / 12`` times."""
    if slope <= 0 or slope % 12:
        raise ValueError(f"slope must be 12, 24, 36, ..., not {slope}")
    passes = slope // 12
    filters = []
    if highpass:
        filters += [f"highpass=f={float(highpass)}"] * passes
    if lowpass:
        filters += [f"lowpass=f={float(lowpass)}"] * passes
    if not filters:
        return audio
    return through_ffmpeg(write_wav_32(audio), ["-af", ",".join(filters)], "Filtering")


def write_wav_32(audio: Audio) -> bytes:
    """32-bit wav bytes for ffmpeg, so a round trip keeps the precision."""
    count = len(audio.channels)
    samples = array("i", bytes(4 * audio.frames * count))
    for c, channel in enumerate(audio.channels):
        samples[c::count] = array("i", (max(-(2**31), min(2**31 - 1, round(value * 2**31))) for value in channel))
    if sys.byteorder == "big":
        samples.byteswap()
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(count)
        target.setsampwidth(4)
        target.setframerate(audio.rate)
        target.writeframes(samples.tobytes())
    return output.getvalue()


# ==== Steps =======================================================================================


def span(audio: Audio, start: float, length: float) -> tuple[int, int]:
    """``[start, length]`` in seconds as frames (first, end): a negative start counts from the end, and a
    length of 0 or less reaches the end, less its size."""
    first, size = to_frames(audio, start), to_frames(audio, length)
    if first < 0:
        first += audio.frames
    if size <= 0:
        size += audio.frames - first
    if size <= 0:
        raise ValueError(f"trim [{start}, {length}] leaves nothing of a {audio.frames / audio.rate:.3f} s clip")
    return first, first + size


def trim(audio: Audio, start: float, length: float) -> Audio:
    """Frames ``[start, length]`` (see ``span``); parts outside the clip are silent."""
    first, end = span(audio, start, length)
    channels = []
    for channel in audio.channels:
        part = channel[max(first, 0) : max(min(end, audio.frames), 0)]
        before = array("d", bytes(8 * max(0, min(-first, end - first))))
        after = array("d", bytes(8 * (end - first - len(before) - len(part))))
        channels.append(before + part + after)
    return audio.with_channels(channels)


def loop_trim(audio: Audio, start: float, length: float, crossfade: float) -> Audio:
    """``trim``, made to loop without a seam: its last ``crossfade`` seconds fade into the audio leading
    into its start, so the wrap continues into its first sample."""
    first, end = span(audio, start, length)
    fade = to_frames(audio, crossfade)
    if not 0 < fade <= end - first or first - fade < 0 or end > audio.frames:
        raise ValueError(
            f"a {crossfade} s loop crossfade needs that much audio before the trim's start, inside the clip"
        )
    channels = []
    for channel in audio.channels:
        part = channel[first:end]
        tail = end - first - fade
        for i in range(fade):
            # Equal power: the two parts aren't correlated enough for a linear fade to keep the level.
            position = (i + 0.5) / fade * math.pi / 2
            part[tail + i] = part[tail + i] * math.cos(position) + channel[first - fade + i] * math.sin(position)
        channels.append(part)
    return audio.with_channels(channels)


def reverse(audio: Audio) -> Audio:
    channels = []
    for channel in audio.channels:
        part = array("d", channel)
        part.reverse()
        channels.append(part)
    return audio.with_channels(channels)


def fade_gain(t: float, curve: str) -> float:
    """The gain ``t`` (0-1) through a fade in."""
    if curve == "linear":
        return t
    if curve == "power":
        return math.sin(t * math.pi / 2)
    raise ValueError(f"Unknown fade curve {curve!r}")


def fade(audio: Audio, fade_in: float, fade_out: float, curve: str = "linear") -> Audio:
    """Fades over the first ``fade_in`` and the last ``fade_out`` seconds."""
    lead, tail = min(to_frames(audio, fade_in), audio.frames), min(to_frames(audio, fade_out), audio.frames)
    channels = []
    for channel in audio.channels:
        part = array("d", channel)
        for i in range(lead):
            part[i] *= fade_gain((i + 0.5) / lead, curve)
        for i in range(tail):
            part[audio.frames - tail + i] *= fade_gain(1 - (i + 0.5) / tail, curve)
        channels.append(part)
    return audio.with_channels(channels)


def gain(audio: Audio, factor: float) -> Audio:
    if factor == 1:
        return audio
    return audio.with_channels([array("d", (value * factor for value in channel)) for channel in audio.channels])


def to_channels(audio: Audio, count: int, pan: float = 0.0) -> Audio:
    """Mono (``count`` 1: the channels averaged) or stereo (mono copied to both sides), then ``pan``ned
    (stereo only): -1 is the left side only, 1 the right only, 0 both as they are."""
    if count not in (1, 2):
        raise ValueError(f"clips are mono or stereo, not {count} channels")
    channels = audio.channels
    if count == 1 and len(channels) > 1:
        share = 1 / len(channels)
        channels = [array("d", (sum(values) * share for values in zip(*channels)))]
    elif count == 2 and len(channels) == 1:
        channels = [channels[0], array("d", channels[0])]
    elif count == 2:
        channels = channels[:2]
    if count == 2 and pan:
        side, factor = (0, 1 - pan) if pan > 0 else (1, 1 + pan)
        channels = list(channels)
        channels[side] = array("d", (value * factor for value in channels[side]))
    return audio.with_channels(channels)


def mix(parts: list[tuple[Audio, float]], length: float | None = None) -> Audio:
    """The parts summed, each starting ``at`` seconds in. They share a rate and channel count. The mix
    lasts ``length`` seconds (default: until the last part ends); a part still playing then is cut, with a
    short fade."""
    rate, count = parts[0][0].rate, len(parts[0][0].channels)
    starts = [round(at * rate) for _, at in parts]
    natural = max(start + audio.frames for (audio, _), start in zip(parts, starts))
    frames = natural if length is None else round(length * rate)
    channels = [array("d", bytes(8 * frames)) for _ in range(count)]
    for (audio, _), start in zip(parts, starts):
        if start < 0:
            raise ValueError("a source can't start before 0")
        for out, channel in zip(channels, audio.channels):
            for i, value in enumerate(channel[: max(0, frames - start)]):
                out[start + i] += value
    result = Audio(rate, channels)
    if frames < natural:
        result = fade(result, 0, CUTOFF_FADE)
    return result


def peak(audio: Audio) -> float:
    return max((max(max(channel), -min(channel)) for channel in audio.channels if len(channel)), default=0.0)


def trim_silence(audio: Audio, threshold_db: float = -60.0) -> Audio:
    """Without the silence (below ``threshold_db`` dBFS) before the sound starts."""
    threshold = 10 ** (threshold_db / 20)
    for i in range(audio.frames):
        if any(abs(channel[i]) >= threshold for channel in audio.channels):
            return audio.with_channels([channel[i:] for channel in audio.channels])
    return audio


def normalize(audio: Audio, peak_db: float) -> Audio:
    """Scaled so its peak is ``peak_db`` dBFS."""
    highest = peak(audio)
    if highest == 0:
        return audio
    return gain(audio, 10 ** (peak_db / 20) / highest)
