from __future__ import annotations

import re
from dataclasses import dataclass, field

DEFAULT_BPM = 120
DEFAULT_DIVISION = 4
PSEUDO_EACH_SECONDS = 0.001

# Two-character shapes first.
SLIDE_SHAPES = ("pp", "qq", "-", "^", "<", ">", "v", "p", "q", "s", "z", "V", "w")

# Extensions, declared in maidata with ``&feat_ext=<name>[,<name>...]``.
EXT_WIFI_MULTI_CHAIN = "wifi_multi_chain"
ALL_EXTENSIONS = frozenset({EXT_WIFI_MULTI_CHAIN})
EXTENSIONS_KEY = "feat_ext"
WIFI_BRANCH_CHAR = "~"


def get_wifi_ends(start: int) -> tuple[int, int]:
    """(L, R) end buttons of a Wi-Fi; the center ends at start + 4."""
    return (start + 4) % 8 + 1, (start + 2) % 8 + 1


## Chart data

@dataclass
class SimaiState:
    """Timing state; a chart can continue from where another left off."""

    beat: float = 0
    bpm: float | None = None
    division: float = DEFAULT_DIVISION
    comma_seconds: float | None = None
    last_advance: float = 0

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

    def advance(self):
        self.last_advance = self.comma_beats
        self.beat += self.last_advance


@dataclass
class SimaiLength:
    beats: float
    wait: float | None  # beats; None = default (1 beat)


@dataclass
class SimaiSegment:
    shape: str
    start: int
    end: int
    turn: int | None = None  # ``V`` only
    length: SimaiLength | None = None
    # Wi-Fi only: (L, R) chains continuing from its side ends. The center continues to the next segment.
    branches: tuple[list[SimaiSegment] | None, list[SimaiSegment] | None] = (None, None)


@dataclass
class SimaiSlide:
    """One ``*`` track."""

    segments: list[SimaiSegment]
    wait: float  # beats
    brk: bool


@dataclass
class SimaiTap:
    button: int
    brk: bool = False
    ex: bool = False
    star: bool = False
    star_rotate: bool = False


@dataclass
class SimaiHold:
    button: int
    brk: bool = False
    ex: bool = False
    length: SimaiLength | None = None


@dataclass
class SimaiTouch:
    sensor: str  # A1 .. E8, C
    brk: bool = False
    firework: bool = False
    hold: bool = False
    length: SimaiLength | None = None


@dataclass
class SimaiSlideNote:
    button: int
    brk: bool = False  # head only
    ex: bool = False  # head only
    tap_head: bool = False
    headless: bool = False
    slides: list[SimaiSlide] = field(default_factory=list)


SimaiNote = SimaiTap | SimaiHold | SimaiTouch | SimaiSlideNote


@dataclass
class SimaiGroup:
    """Notes joined by ``/`` (or a short form)."""

    beat: float
    notes: list[SimaiNote]


@dataclass
class SimaiBpmChange:
    beat: float
    bpm: float


@dataclass
class SimaiChart:
    events: list[SimaiBpmChange | SimaiGroup] = field(default_factory=list)
    state: SimaiState = field(default_factory=SimaiState)  # after the last comma
    maidata: dict[str, str] = field(default_factory=dict)


## maidata


def read_maidata(text: str) -> dict[str, str]:
    """``&key=value`` entries; a value continues on following lines until the next ``&`` line."""
    entries: dict[str, str] = {}
    key = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("&"):
            key, _, value = line[1:].partition("=")
            entries[key] = value
        elif key is not None:
            entries[key] += "\n" + line
    return entries


def get_extensions(maidata: dict[str, str]) -> frozenset[str]:
    names = {name.strip() for name in maidata.get(EXTENSIONS_KEY, "").split(",") if name.strip()}
    unknown = names - ALL_EXTENSIONS
    if unknown:
        raise ValueError(f"Unknown Minimai extensions: {sorted(unknown)}")
    return frozenset(names)


def parse_maidata(text: str, chart: int | str, *, state: SimaiState | None = None) -> SimaiChart:
    """Parse ``&inote_<chart>`` with the extensions the file declares; ``maidata`` holds all entries."""
    maidata = read_maidata(text)
    key = f"inote_{chart}"
    if key not in maidata:
        raise ValueError(f"maidata has no {key}")
    result = parse_simai(maidata[key], state=state, extensions=get_extensions(maidata))
    result.maidata = maidata
    return result


## Lines / Slots / Groups


def parse_simai(text: str, *, state: SimaiState | None = None, extensions: frozenset[str] = ALL_EXTENSIONS) -> SimaiChart:
    """``(bpm)``, ``{div}``, ``{#sec}``, notes separated by ``,``; stops at ``E``."""
    chart = SimaiChart(state=SimaiState() if state is None else state)
    text = re.sub(r"\|\|[^\n]*", "", text)
    text = re.sub(r"\s+", "", text)
    end = re.search(r"E(?![1-8])", text)
    if end is not None:
        text = text[: end.start()]
    slots = text.split(",")
    # The text after the last comma is a slot without its closing comma.
    for index, slot in enumerate(slots):
        parse_slot(chart, slot, index < len(slots) - 1, extensions)
    return chart


def parse_slot(chart: SimaiChart, slot: str, closed: bool, extensions: frozenset[str] = ALL_EXTENSIONS):
    state = chart.state
    while True:
        match = re.match(r"^\((\d+(?:\.\d+)?)\)|^\{(#)?(\d+(?:\.\d+)?)\}", slot)
        if match is None:
            break
        if match.group(1) is not None:
            state.bpm = float(match.group(1))
            chart.events.append(SimaiBpmChange(state.beat, state.bpm))
        elif match.group(2):
            state.comma_seconds = float(match.group(3))
        else:
            state.division = float(match.group(3))
            state.comma_seconds = None
        slot = slot[match.end():]
    if slot:
        pseudo_offset = state.seconds_to_beats(PSEUDO_EACH_SECONDS)
        for order, group in enumerate(slot.split("`")):
            chart.events.append(parse_group(group, state.beat + order * pseudo_offset, state, extensions))
    if closed:
        state.advance()


def parse_group(group: str, beat: float, state: SimaiState, extensions: frozenset[str] = ALL_EXTENSIONS) -> SimaiGroup:
    tokens = [token for token in group.split("/") if token]
    if len(tokens) == 1 and re.fullmatch(r"[1-8]{2,}", tokens[0]):
        tokens = list(tokens[0])
    return SimaiGroup(beat, [parse_note(token, state, extensions) for token in tokens])


## Notes


def parse_length(text: str, state: SimaiState) -> SimaiLength:
    """``[...]`` body."""
    wait = None
    if "##" in text:
        wait_text, text = text.split("##", 1)
        wait = state.seconds_to_beats(float(wait_text))
    bpm = None
    if "#" in text:
        bpm_text, text = text.split("#", 1)
        if not bpm_text:
            return SimaiLength(state.seconds_to_beats(float(text)), wait)
        bpm = float(bpm_text)
        if wait is None:
            wait = state.current_bpm / bpm
    if ":" in text:
        divider, count = text.split(":")
        beats = 4 / float(divider) * float(count)
        if bpm is not None:
            beats = beats * state.current_bpm / bpm
        return SimaiLength(beats, wait)
    if bpm is not None or wait is not None:
        return SimaiLength(state.seconds_to_beats(float(text)), wait)
    raise ValueError(f"Invalid length [{text}]")


def parse_note(token: str, state: SimaiState, extensions: frozenset[str] = ALL_EXTENSIONS) -> SimaiNote:
    if token[0] in "ABCDE":
        match = re.fullmatch(r"([ABDE][1-8]|C[12]?)([bfhx]*)(?:\[([^\]]*)\])?([bfhx]*)", token)
        if match is None:
            raise ValueError(f"Invalid touch {token!r}")
        flags = match.group(2) + match.group(4)
        length = parse_length(match.group(3), state) if match.group(3) is not None else None
        return SimaiTouch(
            "C" if match.group(1).startswith("C") else match.group(1),
            brk="b" in flags,
            firework="f" in flags,
            hold="h" in flags,
            length=length,
        )

    match = re.match(r"([1-8])([bx@?!$]*)", token)
    if match is None:
        raise ValueError(f"Invalid note {token!r}")
    button = int(match.group(1))
    flags = match.group(2)
    rest = token[match.end():]

    if rest.startswith("h"):
        hold = re.fullmatch(r"h([bx]*)(?:\[([^\]]*)\])?([bx]*)", rest)
        if hold is None:
            raise ValueError(f"Invalid hold {token!r}")
        flags += hold.group(1) + hold.group(3)
        length = parse_length(hold.group(2), state) if hold.group(2) is not None else None
        return SimaiHold(button, brk="b" in flags, ex="x" in flags, length=length)
    if not rest or re.fullmatch(r"[bx$]*", rest):
        flags += rest
        dollars = flags.count("$")
        return SimaiTap(button, brk="b" in flags, ex="x" in flags, star=dollars > 0, star_rotate=dollars > 1)

    return SimaiSlideNote(
        button,
        brk="b" in flags,
        ex="x" in flags,
        tap_head="@" in flags,
        headless="?" in flags or "!" in flags,
        slides=[parse_slide(button, track_text, state, extensions) for track_text in rest.split("*")],
    )


## Slides


def parse_segments(start: int, text: str, state: SimaiState) -> tuple[list[SimaiSegment], bool]:
    """Shapes, end buttons, optional ``[length]`` and ``b`` per segment; returns (segments, break)."""
    segments: list[SimaiSegment] = []
    brk = False
    pos = 0
    while pos < len(text):
        shape = next((s for s in SLIDE_SHAPES if text.startswith(s, pos)), None)
        if shape is None:
            raise ValueError(f"Invalid slide {text!r}")
        pos += len(shape)
        turn = None
        if shape == "V":
            turn = int(text[pos])
            pos += 1
        end = int(text[pos])
        pos += 1
        segment = SimaiSegment(shape, start, end, turn)
        while pos < len(text) and text[pos] in "b[":
            if text[pos] == "b":
                brk = True
                pos += 1
            else:
                close = text.index("]", pos)
                segment.length = parse_length(text[pos + 1 : close], state)
                pos = close + 1
        segments.append(segment)
        start = end
    return segments, brk


def parse_slide(button: int, text: str, state: SimaiState, extensions: frozenset[str] = ALL_EXTENSIONS) -> SimaiSlide:
    """One ``*`` track: a chain plus optional ``~`` Wi-Fi branches."""
    main_text, *slots = text.split(WIFI_BRANCH_CHAR)
    if slots and EXT_WIFI_MULTI_CHAIN not in extensions:
        raise ValueError(f"'{WIFI_BRANCH_CHAR}' needs the {EXT_WIFI_MULTI_CHAIN} extension: {text!r}")
    main, brk = parse_segments(button, main_text, state)
    if not main:
        raise ValueError(f"Empty slide {text!r}")

    # Slots go to the most recently written Wi-Fi with a free side (a stack); Wi-Fi inside a
    # branch are pushed when that branch is read. A side button pops Wi-Fi without that end.
    stack: list[WifiSlots] = []
    push_wifi_slots(stack, main)
    for slot in slots:
        while stack and stack[-1].is_full:
            stack.pop()
        if slot and slot[0].isdigit():
            while stack and int(slot[0]) not in get_wifi_ends(stack[-1].segment.start):
                stack.pop()
        if not stack:
            raise ValueError(f"No Wi-Fi left for branch '{WIFI_BRANCH_CHAR}{slot}' in {text!r}")
        taken = stack[-1].take(slot, state)
        if taken is not None:
            branch, branch_brk = taken
            brk = brk or branch_brk
            push_wifi_slots(stack, branch)

    waits = [s.length.wait for s in main if s.length is not None and s.length.wait is not None]
    return SimaiSlide(main, waits[0] if waits else 1.0, brk)


@dataclass
class WifiSlots:
    segment: SimaiSegment
    # Default branch length: what the containing chain has left after the Wi-Fi.
    remaining_beats: float
    used: list[bool] = field(default_factory=lambda: [False, False])

    @property
    def is_full(self) -> bool:
        return all(self.used)

    def take(self, slot: str, state: SimaiState) -> tuple[list[SimaiSegment], bool] | None:
        """``[side button](track)(end)...``; without a button, the first unused side (L, then R)."""
        ends = get_wifi_ends(self.segment.start)
        if slot and slot[0].isdigit():
            side = ends.index(int(slot[0]))
            slot = slot[1:]
        else:
            side = self.used.index(False)
        if self.used[side]:
            raise ValueError(f"Wi-Fi branch {'LR'[side]} given twice")
        self.used[side] = True
        if not slot:
            return None
        branch, brk = parse_segments(ends[side], slot, state)
        if all(s.length is None for s in branch):
            branch[-1].length = SimaiLength(self.remaining_beats, None)
        branches = list(self.segment.branches)
        branches[side] = branch
        self.segment.branches = (branches[0], branches[1])
        return branch, brk


def push_wifi_slots(stack: list[WifiSlots], segments: list[SimaiSegment]):
    for index, segment in enumerate(segments):
        if segment.shape == "w":
            remaining = sum(s.length.beats for s in segments[index + 1 :] if s.length is not None)
            stack.append(WifiSlots(segment, remaining))
