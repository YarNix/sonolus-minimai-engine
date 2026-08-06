from enum import IntEnum

from sonolus.script.options import options, select_option, slider_option, toggle_option
from sonolus.script.text import StandardText

@options
class Options:
    speed: float = slider_option(
        name=StandardText.SPEED,
        standard=True,
        advanced=True,
        default=1,
        min=0.5,
        max=2,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    tap_speed: float = slider_option(
        name="Tap Speed",
        scope="Maimai",
        default=6,
        min=1,
        max=11,
        step=0.05,
    )
    touch_speed: float = slider_option(
        name="Touch Speed",
        scope="Maimai",
        default=6,
        min=1,
        max=11,
        step=0.05,
    )
    ring_size: float = slider_option(
        name="Ring Size",
        scope="Maimai",
        default=0.9,
        min=0.1,
        max=1.2,
        step=0.01,
    )
    ring_offset: float = slider_option(
        name="Ring Offset",
        scope="Maimai",
        default=0,
        min=-1,
        max=1,
        step=0.05,
    )
    button_size: float = slider_option(
        name="Button Size",
        description="How much should the button hitbox extend from the ring. Scale with ring size.",
        scope="Maimai",
        default=0.35,
        min=0.1,
        max=0.5,
        step=0.05,
    )
    button_angle: float = slider_option(
        name="Button Angle",
        description="How many degree does the button hitbox cover the ring.",
        scope="Maimai",
        default=40,
        min=10,
        max=45,
        step=1,
    )
    note_scale: float = slider_option(
        name="Note Scale",
        description="Visually scale the size of tap and star notes",
        scope="Maimai",
        default=1,
        min=0.1,
        max=5,
        step=0.05,
    )

