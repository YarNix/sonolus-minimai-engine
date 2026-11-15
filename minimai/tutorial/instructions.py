from sonolus.script.instruction import Instruction, StandardInstructionIcon, instruction_icons

from minimai.localization import localized_instructions


@localized_instructions
class Instructions:
    intro: Instruction
    tap_title: Instruction
    tap_how: Instruction
    tap_kinds: Instruction
    tap_timing: Instruction
    each_same_time: Instruction
    each_hands: Instruction
    hold_title: Instruction
    hold_how: Instruction
    touch_title: Instruction
    touch_how: Instruction
    touch_hold_title: Instruction
    touch_hold_how: Instruction
    slide_title: Instruction
    slide_star: Instruction
    slide_trace: Instruction
    slide_remember: Instruction


@instruction_icons
class InstructionIcons:
    hand: StandardInstructionIcon.HAND
