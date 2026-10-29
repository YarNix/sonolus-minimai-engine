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
    slide_fade_offset: float = slider_option(
        name="Slide Timing",
        scope="Maimai",
        description="Change the display timing of slide.",
        default=0,
        min=-1000,
        max=1000,
        step=1,
        unit=StandardText.MILLISECOND_UNIT
    )
    input_radius_scale: float = slider_option(
        name="Input radius",
        scope="Maimai",
        description="How big the radius of your touches are. Bigger radius cover more sensors but also less accurate!",
        default=1,
        min=0,
        max=3,
        step=0.1,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    # Judgment ring radius, as a fraction of half the screen height.
    ring_size: float = slider_option(
        name="Ring Size",
        scope="Maimai",
        default=0.875,
        min=0.1,
        max=1.2,
        step=0.01,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    ring_offset: float = slider_option(
        name="Ring Y Offset",
        scope="Maimai",
        default=0,
        min=-1,
        max=1,
        step=0.05,
    )
    sensor_alpha: float = slider_option(
        name="Sensor Outline Alpha",
        scope="Maimai",
        advanced=True,
        default=0,
        min=0,
        max=0.8,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    button_size: float = slider_option(
        name="Button Size",
        scope="Maimai",
        description="The distance that the button hitbox extend from the ring edge.",
        default=0,
        min=0,
        max=2,
        step=0.05,
    )
    button_angle: float = slider_option(
        name="Button Angle",
        description="The width of the hitbox.",
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
        max=3,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    touch_scale: float = slider_option(
        name="Touch Scale",
        description="Visually scale the size of touch notes",
        scope="Maimai",
        default=1,
        min=0.1,
        max=3,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    slide_scale: float = slider_option(
        name="Slide Scale",
        description="Visually scale the size of slide paths",
        scope="Maimai",
        default=1,
        min=0.1,
        max=3,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    show_input: bool = toggle_option(
        name="Show touch input.",
        description="Highlight hitbox when triggered by touches",
        scope="Maimai",
        advanced=True,
        default=False,
    )
