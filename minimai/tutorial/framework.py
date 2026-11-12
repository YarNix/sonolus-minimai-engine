from sonolus.script.effect import LoopedEffectHandle
from sonolus.script.globals import level_memory
from sonolus.script.instruction import clear_instruction
from sonolus.script.particle import ParticleHandle
from sonolus.script.runtime import prev_time, time

from minimai.lib.effect import stop_looped_sfx
from minimai.lib.particle import destroy_hold_glow

TUTORIAL_BPM = 120
# Tap Speed and Touch Speed the tutorial plays at, whatever the options say.
TUTORIAL_TAP_SPEED = 1.0
TUTORIAL_TOUCH_SPEED = 1.0
# Touches are drawn this much bigger than the Touch Scale option.
TUTORIAL_TOUCH_SCALE = 1.25


@level_memory
class TutorialState:
    section: int
    section_start: float
    # One at a time: a section's holds don't overlap.
    glow: ParticleHandle
    riser: LoopedEffectHandle


def start_section(section: int):
    """Also stops what a section left running when it's left early."""
    TutorialState.section = section
    TutorialState.section_start = time()
    clear_instruction()
    destroy_hold_glow(TutorialState.glow)
    stop_looped_sfx(TutorialState.riser)


def get_section_beat() -> float:
    return (time() - TutorialState.section_start) * TUTORIAL_BPM / 60


def get_beat_time(beat: float) -> float:
    """The time of a beat of the current section."""
    return TutorialState.section_start + beat * 60 / TUTORIAL_BPM


def crossed(at: float) -> bool:
    """Whether ``at`` was reached this frame."""
    return prev_time() < at <= time()
