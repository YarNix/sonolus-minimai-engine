from sonolus.script.instruction import Instruction

from minimai.lib.game import Button, Sensor
from minimai.lib.hold import HoldKind
from minimai.lib.note import NoteKind
from minimai.lib.particle import destroy_hold_glow
from minimai.lib.slide import SlideKind, SlideTrackKind
from minimai.lib.touch import TouchKind
from minimai.lib.touch_hold import TouchHoldKind
from minimai.tutorial.framework import TutorialState, get_section_beat
from minimai.tutorial.instructions import Instructions
from minimai.tutorial.notes import run_each_line, run_hold, run_slide, run_tap, run_touch, run_touch_hold

type Message = tuple[int | float, int | float, Instruction]
# (kind, button, beat, indicated): indicated notes get the sensor highlight and the hand.
type TapNote = tuple[NoteKind, Button, int | float, bool]
# (button, button, beat)
type EachLine = tuple[Button, Button, int | float]
# (kind, button, beat, end beat, indicated)
type HoldNote = tuple[HoldKind, Button, int | float, int | float, bool]
# (kind, track, start button, mirrored, star beat, slide start beat, slide end beat, indicated)
type SlideNote = tuple[SlideKind, SlideTrackKind, Button, bool, int | float, int | float, int | float, bool]
# (kind, sensor, beat, indicated)
type TouchNote = tuple[TouchKind, Sensor, int | float, bool]
# (kind, sensor, beat, end beat, firework, indicated)
type TouchHoldNote = tuple[TouchHoldKind, Sensor, int | float, int | float, bool, bool]


# Each section: its messages (start beat, end beat, instruction), its notes, and the beat it ends on.
# The showcase notes come under the messages, with indicators; the replay repeats them after the last message.

INTRO_MESSAGES: tuple[Message, ...] = ((0, 4, Instructions.intro),)
INTRO_END = 4

TAP_MESSAGES: tuple[Message, ...] = (
    (0, 6, Instructions.tap_title),
    (6, 22, Instructions.tap_how),
    (22, 30, Instructions.tap_kinds),
    (30, 38, Instructions.tap_timing),
)
TAP_NOTES: tuple[TapNote, ...] = (
    (NoteKind.NORM_TAP, 2, 12, True),
    (NoteKind.NORM_TAP, 2, 20, True),
    (NoteKind.EX_TAP, 2, 28, True),
    (NoteKind.BREAK_TAP, 2, 36, True),
    # Replay
    (NoteKind.NORM_TAP, 2, 44, False),
    (NoteKind.EX_TAP, 2, 52, False),
    (NoteKind.BREAK_TAP, 2, 60, False),
)
TAP_END = 64

EACH_MESSAGES: tuple[Message, ...] = (
    (0, 8, Instructions.each_same_time),
    (8, 18, Instructions.each_hands),
)
EACH_NOTES: tuple[TapNote, ...] = (
    (NoteKind.EACH_TAP, 2, 14, True),
    (NoteKind.EACH_TAP, 8, 14, True),
    # Replay
    (NoteKind.EACH_TAP, 2, 24, False),
    (NoteKind.EACH_TAP, 8, 24, False),
    (NoteKind.EACH_TAP, 2, 32, False),
    (NoteKind.EACH_TAP, 8, 32, False),
)
EACH_LINES: tuple[EachLine, ...] = (
    (2, 8, 14),
    (2, 8, 24),
    (2, 8, 32),
)
EACH_END = 36

HOLD_MESSAGES: tuple[Message, ...] = (
    (0, 6, Instructions.hold_title),
    (6, 18, Instructions.hold_how),
)
HOLD_NOTES: tuple[HoldNote, ...] = (
    (HoldKind.NORM_HOLD, 2, 12, 16, True),
    # Replay
    (HoldKind.NORM_HOLD, 2, 24, 28, False),
    (HoldKind.NORM_HOLD, 2, 32, 36, False),
)
HOLD_END = 40

SLIDE_MESSAGES: tuple[Message, ...] = (
    (0, 6, Instructions.slide_title),
    (6, 14, Instructions.slide_star),
    (14, 20, Instructions.slide_trace),
    (20, 28, Instructions.slide_remember),
)
# 2-7 is LINE_4 reflected; 7-2 is LINE_4.
SLIDE_NOTES: tuple[SlideNote, ...] = (
    (SlideKind.NORMAL_SLIDE, SlideTrackKind.LINE_4, 2, True, 12, 13, 17, True),
    (SlideKind.NORMAL_SLIDE, SlideTrackKind.LINE_4, 7, False, 22, 23, 27, True),
    # Replay
    (SlideKind.NORMAL_SLIDE, SlideTrackKind.LINE_4, 2, True, 34, 35, 39, False),
    (SlideKind.NORMAL_SLIDE, SlideTrackKind.LINE_4, 7, False, 44, 45, 49, False),
)
SLIDE_END = 52

TOUCH_MESSAGES: tuple[Message, ...] = (
    (0, 6, Instructions.touch_title),
    (6, 16, Instructions.touch_how),
)
TOUCH_NOTES: tuple[TouchNote, ...] = (
    (TouchKind.NORM_TOUCH, Sensor.C, 13, True),
    # Replay
    (TouchKind.NORM_TOUCH, Sensor.C, 24, False),
    (TouchKind.NORM_TOUCH, Sensor.C, 32, False),
)
TOUCH_END = 36

TOUCH_HOLD_MESSAGES: tuple[Message, ...] = (
    (0, 6, Instructions.touch_hold_title),
    (6, 19, Instructions.touch_hold_how),
)
TOUCH_HOLD_NOTES: tuple[TouchHoldNote, ...] = (
    (TouchHoldKind.NORM_TOUCH_HOLD, Sensor.C, 13, 17, True, True),
    # Replay
    (TouchHoldKind.NORM_TOUCH_HOLD, Sensor.C, 26, 30, True, False),
    (TouchHoldKind.NORM_TOUCH_HOLD, Sensor.C, 38, 42, True, False),
)
TOUCH_HOLD_END = 48


def show_messages(messages: tuple[Message, ...]):
    beat = get_section_beat()
    for start, end, message in messages:
        if start <= beat < end:
            message.show()


def run_taps(notes: tuple[TapNote, ...]):
    for kind, button, beat, indicated in notes:
        run_tap(kind, button, beat, indicated)


def run_intro() -> bool:
    show_messages(INTRO_MESSAGES)
    return get_section_beat() >= INTRO_END


def run_tap_section() -> bool:
    show_messages(TAP_MESSAGES)
    run_taps(TAP_NOTES)
    return get_section_beat() >= TAP_END


def run_each_section() -> bool:
    show_messages(EACH_MESSAGES)
    for button_a, button_b, beat in EACH_LINES:
        run_each_line(button_a, button_b, beat)
    run_taps(EACH_NOTES)
    return get_section_beat() >= EACH_END


def run_hold_section() -> bool:
    show_messages(HOLD_MESSAGES)
    held = False
    for kind, button, beat, end_beat, indicated in HOLD_NOTES:
        if run_hold(kind, button, beat, end_beat, indicated):
            held = True
    if not held:
        destroy_hold_glow(TutorialState.glow)
    return get_section_beat() >= HOLD_END


def run_slide_section() -> bool:
    show_messages(SLIDE_MESSAGES)
    for kind, track, button, is_mirrored, beat, slide_beat, end_beat, indicated in SLIDE_NOTES:
        run_slide(kind, track, button, is_mirrored, beat, slide_beat, end_beat, indicated)
    return get_section_beat() >= SLIDE_END


def run_touch_section() -> bool:
    show_messages(TOUCH_MESSAGES)
    for kind, sensor, beat, indicated in TOUCH_NOTES:
        run_touch(kind, sensor, beat, indicated)
    return get_section_beat() >= TOUCH_END


def run_touch_hold_section() -> bool:
    show_messages(TOUCH_HOLD_MESSAGES)
    held = False
    for kind, sensor, beat, end_beat, firework, indicated in TOUCH_HOLD_NOTES:
        if run_touch_hold(kind, sensor, beat, end_beat, firework, indicated):
            held = True
    if not held:
        destroy_hold_glow(TutorialState.glow)
    return get_section_beat() >= TOUCH_HOLD_END


# Run in order; after the last, back to the first.
SECTIONS = (
    run_intro,
    run_tap_section,
    run_each_section,
    run_hold_section,
    run_slide_section,
    run_touch_section,
    run_touch_hold_section,
)
