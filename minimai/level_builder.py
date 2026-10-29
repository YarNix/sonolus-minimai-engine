from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Iterable

from sonolus.script.archetype import PlayArchetype
from sonolus.script.level import BpmChange

from minimai.lib.game import Button, Sensor
from minimai.lib.hold import HoldKind
from minimai.lib.note import NoteKind
from minimai.lib.slide import SlideKind, SlideTrackKind, get_slide_end_button, get_slide_kind_variant
from minimai.lib.touch import TouchKind
from minimai.lib.touch_hold import TouchHoldKind
from minimai.play import each_line, hold, note, slide, touch, touch_hold, base_input
from minimai import simai
from minimai.simai import SimaiChart, SimaiGroup, SimaiHold, SimaiSegment, SimaiSlideNote, SimaiState, SimaiTap, SimaiTouch

NOTE_ARCHETYPES = {arch.key: arch for arch in note.NOTE_ARCHETYPES}
HOLD_ARCHETYPES = {arch.key: arch for arch in hold.HOLD_ARCHETYPES}
TOUCH_ARCHETYPES = {arch.key: arch for arch in touch.TOUCH_ARCHETYPES}
TOUCH_HOLD_ARCHETYPES = {arch.key: arch for arch in touch_hold.TOUCH_HOLD_ARCHETYPES}
SLIDE_ARCHETYPES = {arch.key: arch for arch in slide.SLIDE_ARCHETYPES if arch.is_scored}

def _build_sensor_neighbors() -> dict[Sensor, tuple[Sensor, ...]]:
    def at(group: str, index: int) -> Sensor:
        button = (index - 1) % 8 + 1
        return Sensor[f"{group}{button}"]

    neighbors: dict[Sensor, tuple[Sensor, ...]] = {Sensor.C: tuple(at("B", i) for i in range(1, 9))}
    for i in range(1, 9):
        neighbors[at("A", i)] = (at("D", i), at("D", i + 1), at("E", i), at("E", i + 1), at("B", i))
        neighbors[at("D", i)] = (at("A", i), at("A", i - 1), at("E", i))
        neighbors[at("E", i)] = (at("D", i), at("A", i), at("A", i - 1), at("B", i), at("B", i - 1))
        neighbors[at("B", i)] = (at("E", i), at("E", i + 1), at("B", i - 1), at("B", i + 1), at("A", i), Sensor.C)
    return neighbors

# A map of Sensor to its nearby neighbour, for touch groups.
SENSOR_NEIGHBORS = _build_sensor_neighbors()


def group_touches(members: Sequence[base_input.TouchBaseInput]):
    """Touches (of one time) in groups of neighbouring sensors, in chart order."""
    sensors: list[Sensor] = []
    for member in members:
        if member.sensor not in sensors:
            sensors.append(member.sensor)
    groups: list[list[base_input.TouchBaseInput]] = []
    while sensors:
        group_sensors = [sensors[0]]
        for current in group_sensors:
            for sensor in sensors:
                if sensor not in group_sensors and sensor in SENSOR_NEIGHBORS[current]:
                    group_sensors.append(sensor)
        sensors = [sensor for sensor in sensors if sensor not in group_sensors]
        groups.append([member for member in members if member.sensor in group_sensors])
    return groups


def build_each_lines(notes: Sequence[base_input.ButtonBaseInput]) -> list[base_input.ButtonBaseInput]:
    """EachLines between neighbouring notes of one beat, skipping pairs on the same button."""
    return [
        each_line.EachLine(left_ref=left.ref(), right_ref=right.ref())
        for left, right in zip(notes, notes[1:])
        if left.button != right.button
    ]


def resolve_touch_groups(touches: Sequence[base_input.TouchBaseInput]):
    """Set the touch group (and the body group of touch holds) on the touches of one beat."""
    for group in group_touches(touches):
        if len(group) > 2:
            leader = group[0].ref()
            for member in group:
                member.group_leader = leader
                member.group_size = len(group)

        holds = [member for member in group if isinstance(member, touch_hold.BaseTouchHold)]
        if len(holds) > 2:
            leader = holds[0].ref()
            for member in holds:
                member.body_group_leader = leader
                member.body_group_size = len(holds)


DEFAULT_BPM = simai.DEFAULT_BPM
DEFAULT_DIVISION = simai.DEFAULT_DIVISION
UPPER_HALF = (7, 8, 1, 2)

# (star, double, ex, each, break) -> NoteKind
_NOTE_KINDS = {
    (False, False, False, False, False): NoteKind.NORM_TAP,
    (False, False, True, False, False): NoteKind.EX_TAP,
    (False, False, False, True, False): NoteKind.EACH_TAP,
    (False, False, True, True, False): NoteKind.EX_EACH_TAP,
    (False, False, False, False, True): NoteKind.BREAK_TAP,
    (False, False, True, False, True): NoteKind.EX_BREAK_TAP,
    (True, False, False, False, False): NoteKind.NORM_STAR,
    (True, False, True, False, False): NoteKind.EX_STAR,
    (True, False, False, True, False): NoteKind.EACH_STAR,
    (True, False, True, True, False): NoteKind.EX_EACH_STAR,
    (True, False, False, False, True): NoteKind.BREAK_STAR,
    (True, False, True, False, True): NoteKind.EX_BREAK_STAR,
    (True, True, False, False, False): NoteKind.DOUBLE_STAR,
    (True, True, True, False, False): NoteKind.EX_DOUBLE_STAR,
    (True, True, False, True, False): NoteKind.EACH_DOUBLE_STAR,
    (True, True, True, True, False): NoteKind.EX_EACH_DOUBLE_STAR,
    (True, True, False, False, True): NoteKind.BREAK_DOUBLE_STAR,
    (True, True, True, False, True): NoteKind.EX_BREAK_DOUBLE_STAR,
}


def get_note_kind(*, star: bool = False, double: bool = False, ex: bool = False, each: bool = False, brk: bool = False) -> NoteKind:
    """Break overrides each."""
    return _NOTE_KINDS[(star, star and double, ex, each and not brk, brk)]


def get_hold_kind(*, ex: bool = False, each: bool = False, brk: bool = False) -> HoldKind:
    """Break overrides each."""
    if brk:
        return HoldKind.EX_BREAK_HOLD if ex else HoldKind.BREAK_HOLD
    if each:
        return HoldKind.EX_EACH_HOLD if ex else HoldKind.EACH_HOLD
    return HoldKind.EX_HOLD if ex else HoldKind.NORM_HOLD


def get_touch_hold_kind(*, each: bool = False, brk: bool = False) -> TouchHoldKind:
    """Break overrides each."""
    if brk:
        return TouchHoldKind.BREAK_TOUCH_HOLD
    return TouchHoldKind.EACH_TOUCH_HOLD if each else TouchHoldKind.NORM_TOUCH_HOLD


def get_slide_kind(*, each: bool = False, brk: bool = False, wifi: bool = False) -> SlideKind:
    kind = SlideKind.BREAK_SLIDE if brk else SlideKind.EACH_SLIDE if each else SlideKind.NORMAL_SLIDE
    return SlideKind(get_slide_kind_variant(kind, wifi))


def get_slide_head_kind(kind: SlideKind) -> NoteKind:
    match kind:
        case SlideKind.EACH_SLIDE | SlideKind.EACH_WIFI_SLIDE:
            return NoteKind.EACH_STAR
        case SlideKind.BREAK_SLIDE | SlideKind.BREAK_WIFI_SLIDE:
            return NoteKind.BREAK_STAR
        case _:
            return NoteKind.NORM_STAR


@dataclass
class SlideTrackArg:
    track: SlideTrackKind
    mirrored: bool = False
    # Wi-Fi only: (L, R) branches, each a track or a chain. The center continues to the next arg.
    sub_tracks: tuple[SlideTrackArg | Sequence[SlideTrackArg] | None, SlideTrackArg | Sequence[SlideTrackArg] | None] | None = None
    # Beats. Summed along each head-to-final path; the engine splits that total by bar count.
    slide_time: float | None = None
    # Or seconds (fixed time, see LevelBuilder.emit_slides). A chain uses one or the other.
    slide_seconds: float | None = None


def mirror_key(key: int) -> int:
    return (-key + 1) % 8 + 1


def relative_button(start: int, end: int) -> int:
    return (end - start) % 8 + 1


def get_simai_track(shape: str, start: int, end: int, turn: int | None = None) -> tuple[SlideTrackKind, bool]:
    """simai slide shape -> (track, mirrored)."""
    rel = relative_button(start, end)

    def pick(prefix: str, key: int, mirrored: bool) -> tuple[SlideTrackKind, bool]:
        return SlideTrackKind[f"{prefix}_{key}"], mirrored

    match shape:
        case "-":
            if rel < 3 or rel > 7:
                raise ValueError(f"Invalid '-' slide {start}-{end}")
            return pick("LINE", rel, False) if rel <= 5 else pick("LINE", mirror_key(rel), True)
        case ">":
            return pick("CIRCLE", rel, False) if start in UPPER_HALF else pick("CIRCLE", mirror_key(rel), True)
        case "<":
            return pick("CIRCLE", rel, False) if start not in UPPER_HALF else pick("CIRCLE", mirror_key(rel), True)
        case "^":
            if rel in (1, 5):
                raise ValueError(f"Invalid '^' slide {start}^{end}")
            return pick("CIRCLE", rel, False) if rel < 5 else pick("CIRCLE", mirror_key(rel), True)
        case "v":
            if rel == 5:
                raise ValueError(f"Invalid 'v' slide {start}v{end}")
            return pick("CENTER", rel, False) if rel < 5 else pick("CENTER", mirror_key(rel), True)
        case "pp":
            return pick("LOOP_OUT", rel, False)
        case "qq":
            return pick("LOOP_OUT", mirror_key(rel), True)
        case "p":
            return pick("LOOP_IN", rel, False)
        case "q":
            return pick("LOOP_IN", mirror_key(rel), True)
        case "s" | "z":
            if rel != 5:
                raise ValueError(f"Invalid '{shape}' slide {start}{shape}{end}")
            return SlideTrackKind.ZIG_ZAG, shape == "z"
        case "w":
            if rel != 5:
                raise ValueError(f"Invalid 'w' slide {start}w{end}")
            return SlideTrackKind.FAN, False
        case "V":
            turn_rel = relative_button(start, turn)
            if turn_rel == 7 and 2 <= rel <= 5:
                return pick("REFLECT", rel, False)
            if turn_rel == 3 and rel >= 5:
                return pick("REFLECT", mirror_key(rel), True)
            raise ValueError(f"Invalid 'V' slide {start}V{turn}{end}")
    raise ValueError(f"Unknown slide shape {shape!r}")


def get_simai_track_args(segments: Sequence[SimaiSegment]) -> list[SlideTrackArg]:
    args = []
    for segment in segments:
        track, mirrored = get_simai_track(segment.shape, segment.start, segment.end, segment.turn)
        arg = SlideTrackArg(track, mirrored, slide_seconds=segment.length.seconds if segment.length else None)
        if any(segment.branches):
            arg.sub_tracks = tuple(get_simai_track_args(b) if b else None for b in segment.branches)
        args.append(arg)
    return args


def _uses_seconds(args: Sequence[SlideTrackArg]) -> bool:
    for arg in args:
        if arg.slide_seconds is not None:
            return True
        for sub in arg.sub_tracks or ():
            if _uses_seconds(_as_chain(sub)):
                return True
    return False


class TempoMap:
    """Beat <-> time (seconds) from BPM changes, as the engine converts them."""

    def __init__(self, changes: Iterable[tuple[float, float]]):
        points: dict[float, float] = {}
        for beat, bpm in sorted(changes, key=lambda change: change[0]):
            points[beat] = bpm  # the last change at a beat wins
        if not points:
            points[0] = DEFAULT_BPM
        self.beats = sorted(points)
        self.bpms = [points[beat] for beat in self.beats]
        self.times = [0.0]
        for i in range(1, len(self.beats)):
            self.times.append(self.times[-1] + (self.beats[i] - self.beats[i - 1]) * 60 / self.bpms[i - 1])

    def _segment_by_beat(self, beat: float) -> int:
        index = 0
        while index + 1 < len(self.beats) and self.beats[index + 1] <= beat:
            index += 1
        return index

    def _segment_by_time(self, time: float) -> int:
        index = 0
        while index + 1 < len(self.times) and self.times[index + 1] <= time:
            index += 1
        return index

    def beat_to_time(self, beat: float) -> float:
        i = self._segment_by_beat(beat)
        return self.times[i] + (beat - self.beats[i]) * 60 / self.bpms[i]

    def time_to_beat(self, time: float) -> float:
        i = self._segment_by_time(time)
        return self.beats[i] + (time - self.times[i]) * self.bpms[i] / 60


@dataclass
class _PendingHold:
    entity: PlayArchetype
    beat: float
    seconds: float


@dataclass
class _PendingSlide:
    """A chain timed in seconds, resolved to beats once every BPM change is known."""

    beat: float
    wait_beats: float | None
    wait_seconds: float | None
    # (entity, seconds from the star start to the segment start, segment seconds).
    # The offset is None when the durations are in beats and only the wait is in seconds.
    segments: list[tuple[PlayArchetype, float | None, float]] = field(default_factory=list)


def _as_chain(sub: SlideTrackArg | Sequence[SlideTrackArg] | None) -> tuple[SlideTrackArg, ...]:
    if sub is None:
        return ()
    if isinstance(sub, SlideTrackArg):
        return (sub,)
    return tuple(sub)


@dataclass
class LevelBuilder:
    beat: float = 0
    bpm: float | None = None
    division: float = DEFAULT_DIVISION
    comma_seconds: float | None = None
    entities: list[PlayArchetype] = field(default_factory=list)
    last_advance: float = 0
    # Lengths given in seconds; resolved to beats in get_level().
    _pending_holds: list[_PendingHold] = field(default_factory=list)
    _pending_slides: list[_PendingSlide] = field(default_factory=list)

    ## Timing

    @property
    def current_bpm(self) -> float:
        return self.bpm if self.bpm is not None else DEFAULT_BPM

    @property
    def comma_beats(self) -> float:
        if self.comma_seconds is not None:
            return self.seconds_to_beats(self.comma_seconds)
        return 4 / self.division

    def seconds_to_beats(self, seconds: float) -> float:
        """At the current BPM."""
        return seconds * self.current_bpm / 60

    def set_bpm(self, bpm: float, *, division: float | None = None):
        self.bpm = bpm
        self.entities.append(BpmChange(beat=self.beat, bpm=bpm))
        if division is not None:
            self.set_division(division)

    def set_division(self, division: float):
        self.division = division
        self.comma_seconds = None

    def set_comma_seconds(self, seconds: float):
        self.comma_seconds = seconds

    def advance(self, beats: float | None = None):
        self.last_advance = self.comma_beats if beats is None else beats
        self.beat += self.last_advance

    def same_line(self):
        self.beat -= self.last_advance
        self.last_advance = 0

    def ensure_bpm(self):
        if self.bpm is None:
            beat = self.beat
            self.beat = 0
            self.set_bpm(DEFAULT_BPM)
            self.beat = beat

    ## Add, then advance one comma

    def add_note(self, kind: NoteKind, button: Button, *, speed: float = 1, firework: bool | None = None):
        self.emit_note(kind, button, speed=speed, firework=firework)
        self.advance()

    def add_star(
        self,
        kind: NoteKind,
        button: Button,
        *,
        rotation_speed: float | None = None,
        speed: float = 1,
        firework: bool | None = None,
    ):
        self.emit_note(kind, button, rotation_speed=rotation_speed, speed=speed, firework=firework)
        self.advance()

    def add_touch(self, kind: TouchKind, sensor: Sensor, *, speed: float = 1, firework: bool | None = None):
        self.emit_touch(kind, sensor, speed=speed, firework=firework)
        self.advance()

    def add_hold(
        self,
        kind: HoldKind,
        button: Button,
        hold_time: float = 0,
        *,
        hold_seconds: float | None = None,
        speed: float = 1,
        firework: bool | None = None,
    ):
        """``hold_time`` in beats, or ``hold_seconds``; 0 = a hold that ends with its head."""
        self.emit_hold(kind, button, hold_time, hold_seconds=hold_seconds, speed=speed, firework=firework)
        self.advance()

    def add_touch_hold(
        self,
        kind: TouchHoldKind,
        sensor: Sensor = Sensor.C,
        hold_time: float = 0,
        *,
        hold_seconds: float | None = None,
        speed: float = 1,
        firework: bool | None = None,
    ):
        """``hold_time`` in beats, or ``hold_seconds``; 0 = a touch hold that ends with its head."""
        self.emit_touch_hold(kind, sensor, hold_time, hold_seconds=hold_seconds, speed=speed, firework=firework)
        self.advance()

    def add_slide(
        self,
        kind: SlideKind,
        track: SlideTrackKind,
        mirrored: bool,
        button: Button,
        slide_time: float,
        *,
        wait_time: float = 1,
        head_kind: NoteKind | None = None,
        speed: float = 1,
        head_speed: float = 1,
        firework: bool | None = None,
    ):
        """Head is a star matching the slide colour (break slide -> break star), or ``head_kind``."""
        self.add_slides(
            kind,
            button,
            SlideTrackArg(track, mirrored),
            total_slide_time=slide_time,
            wait_time=wait_time,
            head_kind=head_kind,
            speed=speed,
            head_speed=head_speed,
            firework=firework,
        )

    def add_slide_headless(
        self,
        kind: SlideKind,
        track: SlideTrackKind,
        mirrored: bool,
        button: Button,
        slide_time: float,
        *,
        wait_time: float = 1,
        speed: float = 1,
        firework: bool | None = None,
    ):
        self.add_slides(
            kind,
            button,
            SlideTrackArg(track, mirrored),
            total_slide_time=slide_time,
            wait_time=wait_time,
            headless=True,
            speed=speed,
            firework=firework,
        )

    def add_slides(
        self,
        kind: SlideKind,
        button: Button,
        *track_args: SlideTrackArg,
        total_slide_time: float | None = None,
        total_slide_seconds: float | None = None,
        wait_time: float = 1,
        wait_seconds: float | None = None,
        head_kind: NoteKind | None = None,
        headless: bool = False,
        speed: float = 1,
        head_speed: float = 1,
        firework: bool | None = None,
    ):
        """Chained slide. ``total_slide_time`` goes on every final slide (conn slides get 0)
        unless an arg sets its own ``slide_time``. The ``*_seconds`` forms are fixed times."""
        self.emit_slides(
            kind,
            button,
            track_args,
            total_slide_time=total_slide_time,
            total_slide_seconds=total_slide_seconds,
            wait_time=wait_time,
            wait_seconds=wait_seconds,
            head_kind=head_kind,
            headless=headless,
            speed=speed,
            head_speed=head_speed,
            firework=firework,
        )
        self.advance()

    ## Simai

    @property
    def simai_state(self) -> SimaiState:
        return SimaiState(self.beat, self.bpm, self.division, self.comma_seconds, self.last_advance)

    def parse_line(self, line: str):
        """Parse simai chart text, continuing from the current timing."""
        self.add_simai(simai.parse_simai(line, state=self.simai_state))

    def parse_maidata(self, text: str, chart: int | str) -> dict[str, str]:
        """Parse ``&inote_<chart>`` of a maidata.txt; returns its ``&key=value`` entries."""
        parsed = simai.parse_maidata(text, chart, state=self.simai_state)
        self.add_simai(parsed)
        return parsed.maidata

    def add_simai(self, chart: SimaiChart):
        """Emit a parsed chart, then continue from its end timing."""
        for event in chart.events:
            if isinstance(event, SimaiGroup):
                self.emit_simai_group(event)
            else:
                self.bpm = event.bpm
                self.entities.append(BpmChange(beat=event.beat, bpm=event.bpm))
        state = chart.state
        self.beat, self.division = state.beat, state.division
        if state.bpm is not None:  # else keep the default BPM emitted for the notes
            self.bpm = state.bpm
        self.comma_seconds, self.last_advance = state.comma_seconds, state.last_advance

    def emit_simai_group(self, group: SimaiGroup):
        """EACH: more than one head (or slide track) in the group; break overrides it."""
        notes = group.notes
        each_head = sum(not (isinstance(n, SimaiSlideNote) and n.headless) for n in notes) > 1
        slide_buttons = [n.button for n in notes if isinstance(n, SimaiSlideNote) for _ in n.slides]
        each_slide = len(slide_buttons) > 1

        for parsed in notes:
            if isinstance(parsed, SimaiTouch):
                if parsed.hold:
                    kind = get_touch_hold_kind(each=each_head, brk=parsed.brk)
                    hold_seconds = parsed.length.seconds if parsed.length else None
                    self.emit_touch_hold(
                        kind, Sensor[parsed.sensor], hold_seconds=hold_seconds,
                        firework=parsed.firework or None, beat=group.beat,
                    )
                else:
                    kind = TouchKind.BREAK_TOUCH if parsed.brk else TouchKind.EACH_TOUCH if each_head else TouchKind.NORM_TOUCH
                    self.emit_touch(kind, Sensor[parsed.sensor], firework=parsed.firework or None, beat=group.beat)
            elif isinstance(parsed, SimaiHold):
                kind = get_hold_kind(ex=parsed.ex, each=each_head, brk=parsed.brk)
                hold_seconds = parsed.length.seconds if parsed.length else None
                self.emit_hold(kind, parsed.button, hold_seconds=hold_seconds, beat=group.beat)
            elif isinstance(parsed, SimaiTap):
                kind = get_note_kind(star=parsed.star, ex=parsed.ex, each=each_head, brk=parsed.brk)
                rotation = None if parsed.star_rotate else (0 if parsed.star else None)
                self.emit_note(kind, parsed.button, rotation_speed=rotation, beat=group.beat)
            else:
                double = slide_buttons.count(parsed.button) > 1
                head_kind = get_note_kind(star=not parsed.tap_head, double=double, ex=parsed.ex, each=each_head, brk=parsed.brk)
                for track_index, track in enumerate(parsed.slides):
                    self.emit_slides(
                        get_slide_kind(each=each_slide, brk=track.brk),
                        parsed.button,
                        get_simai_track_args(track.segments),
                        wait_seconds=track.wait,
                        head_kind=head_kind,
                        headless=parsed.headless or track_index > 0,
                        beat=group.beat,
                    )

    def get_level(self) -> Iterable[PlayArchetype]:
        self.resolve_seconds()
        # Resolve groups
        button_groups, touch_groups = self.group_by_beat()
        each_lines: list[PlayArchetype] = []
        for notes in button_groups:
            each_lines.extend(build_each_lines(notes))
        for touches in touch_groups:
            resolve_touch_groups(touches)
        if not any(isinstance(e, BpmChange) for e in self.entities):
            return [BpmChange(beat=0, bpm=DEFAULT_BPM), *self.entities, *each_lines]
        return [*self.entities, *each_lines]

    def group_by_beat(self) -> tuple[list[list[PlayArchetype]], list[list[PlayArchetype]]]:
        """The taps / holds / star heads, and the touches / touch holds, of each beat, in chart order."""
        buttons: dict[float, list[PlayArchetype]] = {}
        touches: dict[float, list[PlayArchetype]] = {}
        for entity in self.entities:
            if isinstance(entity, (note.BaseNote, hold.BaseHold)):
                buttons.setdefault(entity.beat, []).append(entity)
            elif isinstance(entity, (touch.BaseTouch, touch_hold.BaseTouchHold)):
                touches.setdefault(entity.beat, []).append(entity)
        return list(buttons.values()), list(touches.values())

    def get_tempo_map(self) -> TempoMap:
        return TempoMap((e.beat, e.bpm) for e in self.entities if isinstance(e, BpmChange))

    def resolve_seconds(self):
        """Turn lengths given in seconds into beats on the final tempo map, so a BPM change
        inside a hold or slide doesn't change its duration. Safe to call more than once."""
        tempo = self.get_tempo_map()
        for hold_entry in self._pending_holds:
            end = tempo.time_to_beat(tempo.beat_to_time(hold_entry.beat) + hold_entry.seconds)
            hold_entry.entity.hold_duration = end - hold_entry.beat
        for slide_entry in self._pending_slides:
            if slide_entry.wait_seconds is not None:
                star_start = tempo.beat_to_time(slide_entry.beat) + slide_entry.wait_seconds
            else:
                star_start = tempo.beat_to_time(slide_entry.beat + slide_entry.wait_beats)
            wait_beats = tempo.time_to_beat(star_start) - slide_entry.beat
            for entity, offset, seconds in slide_entry.segments:
                entity.wait_duration = wait_beats
                if offset is not None:
                    entity.slide_duration = (
                        tempo.time_to_beat(star_start + offset + seconds) - tempo.time_to_beat(star_start + offset)
                    )

    ## Emitters (no advance)

    def emit_note(
        self,
        kind: NoteKind,
        button: Button,
        *,
        rotation_speed: float | None = None,
        speed: float = 1,
        firework: bool | None = None,
        beat: float | None = None,
    ):
        self.ensure_bpm()
        entity = NOTE_ARCHETYPES[kind](
            beat=self.beat if beat is None else beat,
            button=button,
            speed=speed,
            import_rotate_speed=rotation_speed or 0,
            has_custom_rotation=rotation_speed is not None,
        )
        self.entities.append(entity)
        return entity

    def emit_hold(
        self,
        kind: HoldKind,
        button: Button,
        hold_time: float = 0,
        *,
        hold_seconds: float | None = None,
        speed: float = 1,
        firework: bool | None = None,
        beat: float | None = None,
    ):
        """``hold_time`` in beats from the head, or ``hold_seconds`` (a fixed time, resolved
        to beats in ``get_level`` so BPM changes inside the hold don't change it)."""
        self.ensure_bpm()
        if hold_time < 0 or (hold_seconds is not None and hold_seconds < 0):
            raise ValueError("Hold time can't be negative")
        beat = self.beat if beat is None else beat
        entity = HOLD_ARCHETYPES[kind](
            beat=beat,
            button=button,
            speed=speed,
            hold_duration=hold_time,
        )
        if hold_seconds is not None:
            self._pending_holds.append(_PendingHold(entity, beat, hold_seconds))
        self.entities.append(entity)
        return entity

    def emit_touch_hold(
        self,
        kind: TouchHoldKind,
        sensor: Sensor = Sensor.C,
        hold_time: float = 0,
        *,
        hold_seconds: float | None = None,
        speed: float = 1,
        firework: bool | None = None,
        beat: float | None = None,
    ):
        """``hold_time`` in beats from the head, or ``hold_seconds`` (a fixed time, resolved
        to beats in ``get_level``)."""
        self.ensure_bpm()
        if hold_time < 0 or (hold_seconds is not None and hold_seconds < 0):
            raise ValueError("Hold time can't be negative")
        beat = self.beat if beat is None else beat
        entity = TOUCH_HOLD_ARCHETYPES[kind](
            beat=beat,
            sensor=sensor,
            speed=speed,
            hold_duration=hold_time,
        )
        if hold_seconds is not None:
            self._pending_holds.append(_PendingHold(entity, beat, hold_seconds))
        self.entities.append(entity)
        return entity

    def emit_touch(
        self,
        kind: TouchKind,
        sensor: Sensor,
        *,
        speed: float = 1,
        firework: bool | None = None,
        beat: float | None = None,
    ):
        self.ensure_bpm()
        entity = TOUCH_ARCHETYPES[kind](beat=self.beat if beat is None else beat, sensor=sensor, speed=speed)
        self.entities.append(entity)
        return entity

    def emit_slides(
        self,
        kind: SlideKind,
        button: Button,
        track_args: Sequence[SlideTrackArg],
        *,
        total_slide_time: float | None = None,
        total_slide_seconds: float | None = None,
        wait_time: float = 1,
        wait_seconds: float | None = None,
        head_kind: NoteKind | None = None,
        headless: bool = False,
        speed: float = 1,
        head_speed: float = 1,
        firework: bool | None = None,
        beat: float | None = None,
    ):
        """Slide durations are in beats (``slide_time`` / ``total_slide_time``) or in seconds
        (``slide_seconds`` / ``total_slide_seconds``), not mixed within a chain. Seconds are a
        fixed time: they are resolved to beats in ``get_level`` on the final tempo map, so a BPM
        change during the slide doesn't change its duration. ``wait_seconds`` does the same for
        the wait (either unit works with either duration unit)."""
        self.ensure_bpm()
        if not track_args:
            raise ValueError("A slide needs at least one track")
        beat = self.beat if beat is None else beat
        use_seconds = total_slide_seconds is not None or _uses_seconds(track_args)
        pending = None
        if use_seconds or wait_seconds is not None:
            pending = _PendingSlide(beat, None if wait_seconds is not None else wait_time, wait_seconds)
            self._pending_slides.append(pending)

        head_note = None
        if not headless:
            head_note = self.emit_note(head_kind or get_slide_head_kind(kind), button, speed=head_speed, beat=beat)

        def build(args: tuple[SlideTrackArg, ...], start: Button, prev, path_time: float):
            arg, rest = args[0], args[1:]
            is_wifi = arg.track == SlideTrackKind.FAN
            if arg.sub_tracks is not None and not is_wifi:
                raise ValueError("Only Wi-Fi tracks can have sub tracks")
            sub_l, sub_r = (_as_chain(sub) for sub in (arg.sub_tracks or (None, None)))
            has_next = bool(rest or sub_l or sub_r)

            if use_seconds:
                if arg.slide_time is not None:
                    raise ValueError("A slide chain can't mix slide_time (beats) and slide_seconds")
                slide_time = arg.slide_seconds
                if slide_time is None:
                    slide_time = 0 if has_next else total_slide_seconds
                if slide_time is None:
                    raise ValueError("A final slide needs slide_seconds or total_slide_seconds")
            else:
                slide_time = arg.slide_time
                if slide_time is None:
                    slide_time = 0 if has_next else total_slide_time
                if slide_time is None:
                    raise ValueError("A final slide needs slide_time or total_slide_time")
            path_start = path_time
            path_time += slide_time
            if not has_next and path_time < 0:
                raise ValueError("Total slide time along a path can't be negative")

            if has_next:
                archetype = slide.ConnWifiSlide if is_wifi else slide.ConnSlide
            else:
                archetype = SLIDE_ARCHETYPES[SlideKind(get_slide_kind_variant(kind, is_wifi))]
            entity = archetype(
                beat=beat,
                track=arg.track,
                start_button=start,
                is_mirrored=arg.mirrored,
                wait_duration=wait_time,
                slide_duration=0 if use_seconds else slide_time,
                speed=speed,
            )
            if pending is not None:
                # Durations in beats (only the wait is in seconds): offset None keeps slide_duration.
                pending.segments.append((entity, path_start if use_seconds else None, slide_time))
            if prev is None and head_note is not None:
                entity.head_note_ref = head_note.ref()
            if prev is not None:
                entity.prev_slide_ref = prev.ref()
            self.entities.append(entity)

            center = SlideTrackKind.FAN_C if is_wifi else arg.track
            if rest:
                entity.next_slide_ref = build(rest, get_slide_end_button(center, start, arg.mirrored), entity, path_time).ref()
            if sub_l:
                entity.next_slide_l_ref = build(sub_l, get_slide_end_button(SlideTrackKind.FAN_L, start, arg.mirrored), entity, path_time).ref()
            if sub_r:
                entity.next_slide_r_ref = build(sub_r, get_slide_end_button(SlideTrackKind.FAN_R, start, arg.mirrored), entity, path_time).ref()
            return entity

        build(tuple(track_args), button, None, 0.0)
