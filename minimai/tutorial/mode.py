from sonolus.script.engine import TutorialMode

from minimai.lib.effect import Effects
from minimai.lib.particle import BaseParticles
from minimai.lib.skin import BaseSkin
from minimai.tutorial.instructions import InstructionIcons, Instructions
from minimai.tutorial.navigate import navigate
from minimai.tutorial.preprocess import preprocess
from minimai.tutorial.update import update

tutorial_mode = TutorialMode(
    skin=BaseSkin,
    effects=Effects,
    particles=BaseParticles,
    instructions=Instructions,
    instruction_icons=InstructionIcons,
    preprocess=preprocess,
    navigate=navigate,
    update=update,
)
