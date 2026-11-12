from sonolus.script.instruction import Instruction, StandardInstructionIcon, instruction, instruction_icons, instructions


@instructions
class Instructions:
    intro: Instruction = instruction("Hello! I'll show you how to play!")
    tap_title: Instruction = instruction("First, Tap Notes!")
    tap_how: Instruction = instruction("Tap the button when a ring\nreaches the line.")
    tap_kinds: Instruction = instruction("There are a few kinds\nof Tap Notes…")
    tap_timing: Instruction = instruction("…but just hit them\nall in time!")
    each_same_time: Instruction = instruction("Sometimes two notes\ncome at the same time.")
    each_hands: Instruction = instruction("Then hit one\nwith each hand!")
    hold_title: Instruction = instruction("Next, Hold Notes!")
    hold_how: Instruction = instruction("Hold the button while\nthe long ring crosses the line.")
    touch_title: Instruction = instruction("Next, Touch Notes!")
    touch_how: Instruction = instruction("When the shutter closes,\ntouch the screen there!")
    touch_hold_title: Instruction = instruction("Last one: Touch Hold Notes!")
    touch_hold_how: Instruction = instruction("Touch and keep holding\nuntil the note is gone.")
    slide_title: Instruction = instruction("Next, Slide Notes!")
    slide_star: Instruction = instruction("Hit the ★\n like a Tap Note.")
    slide_trace: Instruction = instruction("A beat later, trace\nthe ★ as it moves!")
    slide_remember: Instruction = instruction("Remember: hit the ★,\nthen slide!")


@instruction_icons
class InstructionIcons:
    hand: StandardInstructionIcon.HAND
