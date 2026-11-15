from enum import IntEnum

from sonolus.script.options import OptionCategory, select_option, slider_option, toggle_option
from sonolus.script.text import StandardText

from minimai.localization import localized_options


@localized_options
class Options:
    gameplay = OptionCategory(title=StandardText.GAMEPLAY)
    graphics = OptionCategory(title=StandardText.GRAPHICS)
    audio = OptionCategory(title=StandardText.AUDIO)
    miscellaneous = OptionCategory(title=StandardText.MISCELLANEOUS)
    challenge = OptionCategory()

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
        values=[StandardText.OFF, "left_right", "up_down", "rotate_180", "diagonal_left", "diagonal_right"],
    )
    orientation: int = select_option(
        name="Orientation",
        scope="Maimai",
        category=gameplay,
        default=0,
        values=["landscape", "landscape_reversed", "portrait", "portrait_reversed"],
    )
    note_radius: float = slider_option(
        name="Note Radius",
        scope="Maimai",
        category=gameplay,
        default=1,
        min=0,
        max=3,
        step=0.01,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    touch_radius: float = slider_option(
        name="Touch Radius",
        scope="Maimai",
        category=gameplay,
        default=1.5,
        min=0,
        max=3,
        step=0.01,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    ring_size: float = slider_option(
        name="Ring Size",
        scope="Maimai",
        category=gameplay,
        default=1,
        min=0.1,
        max=1.5,
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
    button_size: float = slider_option(
        name="Button Size",
        scope="Maimai",
        category=gameplay,
        default=0,
        min=0,
        max=2,
        step=0.05,
    )
    button_angle: float = slider_option(
        name="Button Angle",
        scope="Maimai",
        category=gameplay,
        default=40,
        min=10,
        max=45,
        step=1,
    )
    note_scale: float = slider_option(
        name="Note Scale",
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
        scope="Maimai",
        category=audio,
        default=1,
        values=["good_perfect", "good_critical_perfect", "critical_perfect_only", "perfect_only"],
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
        scope="Maimai",
        category=gameplay,
        standard=True,
        default=False,
    )
    sonolus_judgment: bool = toggle_option(
        name="Sonolus Judgment",
        scope="Maimai",
        category=graphics,
        default=False,
    )
    center_display: int = select_option(
        name="Center Display",
        scope="Maimai",
        category=graphics,
        default=1,
        values=[
            StandardText.OFF,
            "combo",
            "grade_combo",
            "achievement",
            "achievement_from_100",
            "achievement_from_101",
            "dx_score",
            "dx_score_from_max",
            "dx_score_rank",
            "s_border",
            "ss_border",
            "sss_border",
            "sonolus_combo",
        ],
    )
    center_display_opacity: float = slider_option(
        name="Center Display Opacity",
        scope="Maimai",
        category=graphics,
        default=0.7,
        min=0,
        max=1,
        step=0.01,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    judge_text: int = select_option(
        name="Judge Text",
        scope="Maimai",
        category=graphics,
        default=0,
        values=["all", "below_critical_perfect", "below_perfect", "below_great", "miss_only", StandardText.OFF],
    )
    critical_perfect_text: bool = toggle_option(
        name="Show Critical Perfect Text",
        scope="Maimai",
        category=graphics,
        default=False,
    )
    fast_late: int = select_option(
        name="Fast/Late",
        scope="Maimai",
        category=graphics,
        default=3,
        values=["below_critical_perfect", "below_perfect", "below_great", StandardText.OFF],
    )
    fast_late_style: int = select_option(
        name="Fast/Late Style",
        scope="Maimai",
        category=graphics,
        default=0,
        values=["with_judgment", "fast_late_judgment", "fast_late_only"],
    )
    judge_text_distance: float = slider_option(
        name="Judge Text Distance",
        scope="Maimai",
        category=graphics,
        default=1,
        min=0,
        max=1,
        step=0.05,
    )
    slide_ok_order: int = select_option(
        name="Slide OK Order",
        scope="Maimai",
        category=graphics,
        default=0,
        values=["earlier_on_top", "later_on_top"],
    )
    hold_head_judge: bool = toggle_option(
        name="Hold Head Judge Text",
        scope="Maimai",
        category=graphics,
        default=False,
    )
    touch_feedback: int = select_option(
        name="Touch Feedback",
        scope="Maimai",
        category=graphics,
        default=1,
        values=["all", "outer_only", "inner_only", StandardText.OFF],
    )
    show_input: bool = toggle_option(
        name="Show touch input.",
        category=miscellaneous,
        scope="Maimai",
        advanced=True,
        default=False,
    )
    record_input: bool = toggle_option(
        name="Record touch input",
        category=miscellaneous,
        scope="Maimai",
        advanced=True,
        default=False,
    )
    sensor_alpha: float = slider_option(
        name="Sensor Outline Alpha",
        scope="Maimai",
        category=miscellaneous,
        advanced=True,
        default=0,
        min=0,
        max=0.8,
        step=0.05,
        unit=StandardText.PERCENTAGE_UNIT,
    )
    life_challenge: float = slider_option(
        name="Life Challenge",
        scope="Maimai",
        category=challenge,
        standard=True,
        default=0,
        min=0,
        max=999,
        step=1,
    )
    critical_perfect_loss: float = slider_option(
        name="Critical Perfect Loss",
        scope="Maimai",
        category=challenge,
        standard=True,
        default=0,
        min=0,
        max=100,
        step=1,
    )
    perfect_loss: float = slider_option(
        name="Perfect Loss",
        scope="Maimai",
        category=challenge,
        standard=True,
        default=0,
        min=0,
        max=100,
        step=1,
    )
    great_loss: float = slider_option(
        name="Great Loss",
        scope="Maimai",
        category=challenge,
        standard=True,
        default=0,
        min=0,
        max=100,
        step=1,
    )
    good_loss: float = slider_option(
        name="Good Loss",
        scope="Maimai",
        category=challenge,
        standard=True,
        default=0,
        min=0,
        max=100,
        step=1,
    )
    miss_loss: float = slider_option(
        name="Miss Loss",
        scope="Maimai",
        category=challenge,
        standard=True,
        default=0,
        min=0,
        max=100,
        step=1,
    )
    end_at_zero_life: bool = toggle_option(
        name="End at 0 Life",
        scope="Maimai",
        category=challenge,
        standard=True,
        default=True,
    )
