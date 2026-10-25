from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Iterable

from sonolus.script.archetype import PlayArchetype
from sonolus.script.level import BpmChange

from minimai.lib.game import Button, Sensor
from minimai.lib.note import NoteKind
from minimai.lib.slide import SlideKind, SlideTrackKind, get_slide_end_button, get_slide_kind_variant
from minimai.lib.touch import TouchKind
from minimai.play import note, slide, touch
from minimai import simai
from minimai.simai import SimaiChart, SimaiGroup, SimaiHold, SimaiSegment, SimaiSlideNote, SimaiState, SimaiTap, SimaiTouch

NOTE_ARCHETYPES = {arch.key: arch for arch in note.NOTE_ARCHETYPES}
TOUCH_ARCHETYPES = {arch.key: arch for arch in touch.TOUCH_ARCHETYPES}
SLIDE_ARCHETYPES = {arch.key: arch for arch in slide.SLIDE_ARCHETYPES if arch.is_scored}

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
        arg = SlideTrackArg(track, mirrored, slide_time=segment.length.beats if segment.length else None)
        if any(segment.branches):
            arg.sub_tracks = tuple(get_simai_track_args(b) if b else None for b in segment.branches)
        args.append(arg)
    return args


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

    def add_hold(self, kind: NoteKind, button: Button, *, speed: float = 1, firework: bool | None = None):
        # TODO: hold archetypes
        self.advance()

    def add_touch_hold(self, kind: TouchKind, *, sensor: Sensor = Sensor.C, speed: float = 1, firework: bool | None = None):
        # TODO: touch hold archetypes
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
        wait_time: float = 1,
        head_kind: NoteKind | None = None,
        headless: bool = False,
        speed: float = 1,
        head_speed: float = 1,
        firework: bool | None = None,
    ):
        """Chained slide. ``total_slide_time`` goes on every final slide (conn slides get 0)
        unless an arg sets its own ``slide_time``."""
        self.emit_slides(
            kind,
            button,
            track_args,
            total_slide_time=total_slide_time,
            wait_time=wait_time,
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
                kind = TouchKind.BREAK_TOUCH if parsed.brk else TouchKind.EACH_TOUCH if each_head else TouchKind.NORM_TOUCH
                if not parsed.hold:  # TODO: touch hold
                    self.emit_touch(kind, Sensor[parsed.sensor], firework=parsed.firework or None, beat=group.beat)
            elif isinstance(parsed, SimaiHold):
                pass  # TODO: hold
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
                        wait_time=track.wait,
                        head_kind=head_kind,
                        headless=parsed.headless or track_index > 0,
                        beat=group.beat,
                    )

    def get_level(self) -> Iterable[PlayArchetype]:
        if not any(isinstance(e, BpmChange) for e in self.entities):
            return [BpmChange(beat=0, bpm=DEFAULT_BPM), *self.entities]
        return list(self.entities)

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
        wait_time: float = 1,
        head_kind: NoteKind | None = None,
        headless: bool = False,
        speed: float = 1,
        head_speed: float = 1,
        firework: bool | None = None,
        beat: float | None = None,
    ):
        self.ensure_bpm()
        if not track_args:
            raise ValueError("A slide needs at least one track")
        beat = self.beat if beat is None else beat

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

            slide_time = arg.slide_time
            if slide_time is None:
                slide_time = 0 if has_next else total_slide_time
            if slide_time is None:
                raise ValueError("A final slide needs slide_time or total_slide_time")
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
                slide_duration=slide_time,
                speed=speed,
            )
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
