from sonolus.script.engine import Engine, EngineData
from sonolus.script.project import Project

from minimai.lib.options import Options
from minimai.lib.ui import ui_config
from minimai.test_level import levels
from minimai.play.mode import play_mode
from minimai.preview.mode import preview_mode
from minimai.tutorial.mode import tutorial_mode
from minimai.watch.mode import watch_mode
from minimai import test_level

engine = Engine(
    name="minimai",
    title="Minimai",
    description="An engine to practice your washing machine skills",
    skin="minimai-default",
    effect="minimai-default",
    particle="minimai-default",
    background="black",
    data=EngineData(
        ui=ui_config,
        options=Options,
        play=play_mode,
        watch=watch_mode,
        preview=preview_mode,
        tutorial=tutorial_mode,
    ),
)

project = Project(
    engine=engine,
    levels=test_level.levels,
)