from sonolus.script.instruction import clear_instruction

from minimai.lib.ring import draw_ring
from minimai.tutorial.framework import TutorialState, start_section
from minimai.tutorial.sections import SECTIONS


def next_section():
    start_section((TutorialState.section + 1) % len(SECTIONS))


def previous_section():
    start_section((TutorialState.section - 1) % len(SECTIONS))


def update():
    clear_instruction()
    draw_ring()
    for i, run_section in enumerate(SECTIONS):
        if i == TutorialState.section and run_section():
            next_section()
