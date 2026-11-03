from enum import IntEnum

from sonolus.script.options import OptionCategory, options, select_option, slider_option, toggle_option
from sonolus.script.text import StandardText

@options
class Options:
    gameplay = OptionCategory(title=StandardText.GAMEPLAY)
    graphics = OptionCategory(title=StandardText.GRAPHICS)
    audio = OptionCategory(title=StandardText.AUDIO)
    miscellaneous = OptionCategory(title=StandardText.MISCELLANEOUS)

    speed: float = slider_option(
        name=StandardText.SPEED,
        category=gameplay,
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
        category=gameplay,
        default=6,
        min=1,
        max=11,
        step=0.05,
    )
    touch_speed: float = slider_option(
        name="Touch Speed",
        scope="Maimai",
        category=gameplay,
        default=6,
        min=1,
        max=11,
        step=0.05,
    )
    slide_fade_offset: float = slider_option(
        name="Slide Timing",
        scope="Maimai",
        category=gameplay,
        description="Change the display timing of slide.",
        default=0,
        min=-1000,
        max=1000,
        step=1,
        unit=StandardText.MILLISECOND_UNIT
    )
    mirror: int = select_option(
        name=StandardText.MIRROR,
        scope="Maimai",
        category=gameplay,
        default=0,
        values=["OFF", "⇔", "⇅", "↻", "⇙", "⇘"],
    )
    input_radius_scale: float = slider_option(
        name="Input radius",
        scope="Maimai",
        category=gameplay,
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
        category=gameplay,
        default=0.875,
        min=0.1,
        max=1.2,
        step=0.01,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    ring_offset: float = slider_option(
        name="Ring Y Offset",
        scope="Maimai",
        category=gameplay,
        default=0,
        min=-1,
        max=1,
        step=0.05,
    )
    sensor_alpha: float = slider_option(
        name="Sensor Outline Alpha",
        scope="Maimai",
        category=graphics,
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
        category=gameplay,
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
        category=gameplay,
        default=40,
        min=10,
        max=45,
        step=1,
    )
    note_scale: float = slider_option(
        name="Note Scale",
        description="Visually scale the size of tap and star notes",
        scope="Maimai",
        category=graphics,
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
        category=graphics,
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
        category=graphics,
        default=1,
        min=0.1,
        max=3,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    # Sounds per category;
    guide_sound: bool = toggle_option(
        name="Guide Sound",
        description="A sound at every note timing, plus a count-in.",
        scope="Maimai",
        category=audio,
        default=True,
    )
    tap_sound: bool = toggle_option(
        name="Tap/Hold Sound",
        scope="Maimai",
        category=audio,
        default=True,
    )
    tap_sound_judgment: int = select_option(
        name="Tap/Hold Sound Judgment",
        description="Which judgments make a Tap/Hold sound.",
        scope="Maimai",
        category=audio,
        default=1,
        values=["Good-Perfect", "Good-Critical Perfect", "Critical Perfect only", "Perfect only"],
    )
    break_sound: bool = toggle_option(
        name="Break Sound",
        scope="Maimai",
        category=audio,
        default=True,
    )
    ex_sound: bool = toggle_option(
        name="EX Sound",
        scope="Maimai",
        category=audio,
        default=True,
    )
    slide_sound: bool = toggle_option(
        name="Slide Sound",
        scope="Maimai",
        category=audio,
        default=True,
    )
    touch_sound: bool = toggle_option(
        name="Touch Sound",
        scope="Maimai",
        category=audio,
        default=True,
    )
    misc_sound: bool = toggle_option(
        name="Miscellaneous Sound",
        description="Fireworks.",
        scope="Maimai",
        category=audio,
        default=True,
    )
    auto_sfx: bool = toggle_option(
        name=StandardText.EFFECT_AUTO,
        scope="Maimai",
        category=audio,
        default=False,
    )
    note_effect: bool = toggle_option(
        name=StandardText.NOTE_EFFECT,
        category=graphics,
        default=True,
    )
    effect_size: float = slider_option(
        name=StandardText.NOTE_EFFECT_SIZE,
        scope="Maimai",
        category=graphics,
        default=1,
        min=0.1,
        max=2,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    effect_animation_speed: float = slider_option(
        name="Effect Animation Speed",
        scope="Maimai",
        category=graphics,
        default=1,
        min=0.25,
        max=4,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    strict_slide_judgment: bool = toggle_option(
        name="Strict Slide Judgment",
        description='Divide Slide "Perfect" judgment into Critical and Fast/Late Perfect (affect break slide only)',
        scope="Maimai",
        category=gameplay,
        standard=True,
        default=False,
    )
    sonolus_judgment: bool = toggle_option(
        name="Sonolus Judgment",
        description="Show Sonolus' judgment text instead of the judge text and fast/late at each note.",
        scope="Maimai",
        category=gameplay,
        default=False,
    )
    judge_text: int = select_option(
        name="Judge Text",
        description="Which judgments show their text at the note.",
        scope="Maimai",
        category=graphics,
        default=0,
        values=["All", "Below Critical Perfect", "Below Perfect", "Below Great", "Miss Only", "Off"],
    )
    critical_perfect_text: bool = toggle_option(
        name="Show Critical Perfect Text",
        description="Critical perfects show their own text instead of Perfect.",
        scope="Maimai",
        category=graphics,
        default=False,
    )
    fast_late: int = select_option(
        name="Fast/Late",
        description="Which judgments show fast/late at the note.",
        scope="Maimai",
        category=graphics,
        default=3,
        values=["Below Critical Perfect", "Below Perfect", "Below Great", "Off"],
    )
    fast_late_style: int = select_option(
        name="Fast/Late Style",
        description=(
            "With Judgment: fast/late beside the judge text.\n"
            "Fast/Late Judgment: the judge text in its fast/late version.\n"
            "Fast/Late Only: fast/late without the judge text."
        ),
        scope="Maimai",
        category=graphics,
        default=0,
        values=["With Judgment", "Fast/Late Judgment", "Fast/Late Only"],
    )
    judge_text_distance: float = slider_option(
        name="Judge Text Distance",
        description="Lower moves the judge text toward the center; 0 hides it.",
        scope="Maimai",
        category=graphics,
        default=1,
        min=0,
        max=1,
        step=0.05,
    )
    slide_ok_order: int = select_option(
        name="Slide OK Order",
        description="Which slide OK is on top where they overlap. A worse judgment is always on top.",
        scope="Maimai",
        category=graphics,
        default=0,
        values=["Earlier on Top", "Later on Top"],
    )
    hold_head_judge: bool = toggle_option(
        name="Hold Head Judge Text",
        description="Holds also show the judge text of their head.",
        scope="Maimai",
        category=graphics,
        default=False,
    )
    show_input: bool = toggle_option(
        name="Show touch input.",
        description="Highlight hitbox when triggered by touches",
        category=miscellaneous,
        scope="Maimai",
        advanced=True,
        default=False,
    )
