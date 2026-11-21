from math import floor

from sonolus.script.interval import clamp, unlerp, unlerp_clamped
from sonolus.script.runtime import time

from minimai.lib.each_line import draw_each_line
from minimai.lib.effect import (
    Effects,
    emit_ex_sfx,
    emit_firework_sfx,
    emit_hold_end_sfx,
    emit_sfx,
    emit_tap_sfx,
    emit_touch_sfx,
    first_available_effect,
    stop_looped_sfx,
)
from minimai.lib.firework import draw_firework, get_firework_end_time
from minimai.lib.game import (
    ArcadeJudgment,
    Button,
    Sensor,
    apply_button_mirror_option,
    apply_sensor_mirror_option,
    is_mirror_option_reflection,
)
from minimai.lib.layer import LAYER_SLIDE_OK, get_z
from minimai.lib.hold import HoldKind, HoldState, draw_hold, is_break_hold, is_ex_hold
from minimai.lib.judge_text import draw_judge_text, get_judge_text_end_time, get_judge_text_sprites, shows_judge_text
from minimai.lib.layout import (
    SLIDE_TRACK_POINTS,
    JudgeTextLayout,
    build_slide_star_points,
    get_button_angle_horizontal,
    layout_button_judge_text,
    layout_hold_effect,
    layout_ring_pos,
    layout_slide_head,
    layout_slide_ok,
    layout_sensor_firework_center,
    layout_tap_effect,
    layout_touch_effect,
    layout_touch_hold_effect,
    layout_touch_hold_glow,
    layout_touch_hold_judge_text,
    layout_touch_judge_text,
)
from minimai.lib.note import NoteKind, draw_note, get_note_angle, get_tap_appear_duration, is_break, is_ex
from minimai.lib.options import Options
from minimai.lib.particle import spawn_tap_effect, spawn_touch_effect, update_hold_glow
from minimai.lib.slide import (
    SlideKind,
    SlideTrackKind,
    draw_slide,
    get_slide_appear_duration,
    get_slide_end_button,
    get_star_note_kind,
    get_star_rotate_speed,
    is_break_slide,
)
from minimai.lib.slide_ok import draw_slide_ok, get_slide_ok_end_time, get_slide_ok_sprite, shows_slide_ok
from minimai.lib.touch import TouchKind, draw_touch, get_touch_appear_duration, is_break_touch
from minimai.lib.touch_hold import TouchHoldKind, draw_touch_hold, is_break_touch_hold, is_ex_touch_hold
from minimai.tutorial.framework import TutorialState, crossed, get_beat_time
from minimai.tutorial.indicators import (
    draw_button_highlight,
    draw_sensor_highlight,
    paint_button_hand,
    paint_sensor_hand,
    paint_star_hand,
)

# Every tutorial note is hit on time.
JUDGMENT = ArcadeJudgment.CRITICAL_PERFECT


def draw_tutorial_judge_text(layout: JudgeTextLayout, is_break: bool, hit_time: float):
    if hit_time <= time() < get_judge_text_end_time(hit_time) and shows_judge_text(JUDGMENT):
        draw_judge_text(get_judge_text_sprites(JUDGMENT, is_break, 0), layout, hit_time)


def draw_tutorial_firework(sensor: Sensor, hit_time: float, seed: float):
    if Options.note_effect and hit_time <= time() < get_firework_end_time(hit_time):
        draw_firework(layout_sensor_firework_center(sensor), hit_time, seed)


def run_tap(kind: NoteKind, button: Button, beat: float, indicated: bool):
    """A tap hit on ``beat``: drawn until then, then its sound, particles and judge text.
    ``indicated``: with the sensor highlight and the hand."""
    button = apply_button_mirror_option(button)
    target_time = get_beat_time(beat)
    start_time = target_time - get_tap_appear_duration(1)
    if indicated:
        draw_button_highlight(button, start_time, target_time)
        paint_button_hand(button, target_time, target_time)
    if time() < target_time:
        draw_note(kind, button, start_time, target_time, 0)
    if crossed(target_time):
        emit_tap_sfx(is_break(kind), is_ex(kind), JUDGMENT, target_time, scheduled=False)
        spawn_tap_effect(is_break(kind), JUDGMENT, layout_tap_effect(button))
    draw_tutorial_judge_text(layout_button_judge_text(button), is_break(kind), target_time)


def run_each_line(button_a: Button, button_b: Button, beat: float):
    """The arc between two taps hit together on ``beat``, the shorter way round."""
    a = apply_button_mirror_option(button_a)
    b = apply_button_mirror_option(button_b)
    target_time = get_beat_time(beat)
    if time() >= target_time:
        return
    steps = (b - a + 8) % 8
    start_button = a
    if steps > 4:
        steps = 8 - steps
        start_button = b
    draw_each_line(start_button, steps, target_time - get_tap_appear_duration(1), target_time, False)


def run_hold(kind: HoldKind, button: Button, beat: float, end_beat: float, indicated: bool) -> bool:
    """A hold pressed on ``beat`` and released on ``end_beat``. Returns whether it's held now
    (the section keeps the glow running while one is)."""
    button = apply_button_mirror_option(button)
    target_time = get_beat_time(beat)
    end_time = get_beat_time(end_beat)
    start_time = target_time - get_tap_appear_duration(1)
    now = time()
    held = target_time <= now < end_time
    if indicated:
        draw_button_highlight(button, start_time, end_time)
        paint_button_hand(button, target_time, end_time)
    if now < end_time:
        state = HoldState.DEFAULT
        if held:
            state = HoldState.PRESSED
        draw_hold(kind, button, start_time, target_time, end_time, state)
    if held:
        update_hold_glow(TutorialState.glow, True, JUDGMENT, layout_hold_effect(button))
    if crossed(target_time):
        emit_tap_sfx(is_break_hold(kind), is_ex_hold(kind), JUDGMENT, target_time, scheduled=False)
    if crossed(end_time):
        emit_hold_end_sfx(JUDGMENT, end_time, scheduled=False)
        spawn_tap_effect(is_break_hold(kind), JUDGMENT, layout_tap_effect(button))
    if Options.hold_head_judge:
        draw_tutorial_judge_text(layout_button_judge_text(button), is_break_hold(kind), target_time)
    draw_tutorial_judge_text(layout_button_judge_text(button), is_break_hold(kind), end_time)
    return held


def run_touch(kind: TouchKind, sensor: Sensor, beat: float, indicated: bool):
    """A touch hit on ``beat``, as ``run_tap``."""
    sensor = apply_sensor_mirror_option(sensor)
    target_time = get_beat_time(beat)
    start_time = target_time - get_touch_appear_duration(1)
    if indicated:
        draw_sensor_highlight(sensor, start_time, target_time)
        paint_sensor_hand(sensor, target_time, target_time)
    if time() < target_time:
        draw_touch(kind, sensor, start_time, target_time)
    if crossed(target_time):
        emit_touch_sfx(is_break_touch(kind), JUDGMENT, target_time, scheduled=False)
        spawn_touch_effect(JUDGMENT, layout_touch_effect(sensor))
    draw_tutorial_judge_text(layout_touch_judge_text(sensor), is_break_touch(kind), target_time)


def start_riser():
    """The touch hold charge; the tutorial's touch holds end before it would hand over to the sustain."""
    if Options.touch_sound and TutorialState.riser.id == 0:
        riser = first_available_effect(Effects.touch_hold_start, Effects.touch_hold_sustain, Effects.touch_hold_sustain_fallback)
        if riser.is_available:
            TutorialState.riser @= riser.loop()


def run_touch_hold(
    kind: TouchHoldKind, sensor: Sensor, beat: float, end_beat: float, firework: bool, indicated: bool
) -> bool:
    """A touch hold pressed on ``beat`` and released on ``end_beat``, with the riser while held.
    Returns whether it's held now, as ``run_hold``."""
    sensor = apply_sensor_mirror_option(sensor)
    target_time = get_beat_time(beat)
    end_time = get_beat_time(end_beat)
    start_time = target_time - get_touch_appear_duration(1)
    now = time()
    held = target_time <= now < end_time
    is_break = is_break_touch_hold(kind)
    if indicated:
        draw_sensor_highlight(sensor, start_time, end_time)
        paint_sensor_hand(sensor, target_time, end_time)
    if now < end_time:
        state = HoldState.DEFAULT
        if held:
            state = HoldState.PRESSED
        draw_touch_hold(kind, sensor, start_time, target_time, end_time, state)
    if held:
        update_hold_glow(TutorialState.glow, True, JUDGMENT, layout_touch_hold_glow(sensor))
    if crossed(target_time):
        start_riser()
    if crossed(end_time):
        stop_looped_sfx(TutorialState.riser)
        if is_ex_touch_hold(kind):
            emit_ex_sfx(JUDGMENT, end_time, scheduled=False)
        else:
            emit_hold_end_sfx(JUDGMENT, end_time, scheduled=False)
        emit_firework_sfx(firework, JUDGMENT, end_time, scheduled=False)
        spawn_tap_effect(is_break, JUDGMENT, layout_touch_hold_effect(sensor))
    if firework:
        draw_tutorial_firework(sensor, end_time, beat)
    draw_tutorial_judge_text(layout_touch_hold_judge_text(sensor), is_break, end_time)
    return held


def run_slide(
    kind: SlideKind,
    track: SlideTrackKind,
    button: Button,
    is_mirrored: bool,
    beat: float,
    slide_beat: float,
    end_beat: float,
    indicated: bool,
):
    """A star hit on ``beat`` (as ``run_tap``), its slide travelling from ``slide_beat`` to ``end_beat``
    with the slide sound, and the slide OK on arrival. ``indicated``: the hand taps the star and follows it
    (straight slides: it points from the start button to the end button), and the start and end sensors light up."""
    button = apply_button_mirror_option(button)
    if is_mirror_option_reflection():
        is_mirrored = not is_mirrored
    end_button = get_slide_end_button(track, button, is_mirrored)
    target_time = get_beat_time(beat)
    slide_time = get_beat_time(slide_beat)
    end_time = get_beat_time(end_beat)
    star_kind = get_star_note_kind(kind)
    track_points = SLIDE_TRACK_POINTS[track]
    now = time()

    if indicated:
        star_points = build_slide_star_points(track_points, get_slide_end_button(track, 1, False))
        star = layout_slide_head(unlerp_clamped(slide_time, end_time, now), star_points, button, is_mirrored).center
        travel = layout_ring_pos(get_button_angle_horizontal(end_button), 1) - layout_ring_pos(
            get_button_angle_horizontal(button), 1
        )
        draw_button_highlight(button, target_time - get_tap_appear_duration(1), target_time)
        draw_button_highlight(end_button, slide_time, end_time)
        paint_star_hand(button, target_time, slide_time, end_time, travel.angle, star)

    if now < end_time:
        point_count = len(track_points)
        path_hidden = clamp(floor(unlerp(slide_time, end_time, now) * (point_count + 1)), 0, point_count)
        draw_slide(
            kind,
            track,
            button,
            is_mirrored,
            path_hidden,
            target_time - get_slide_appear_duration(1),
            target_time,
            slide_time,
            end_time,
            True,
            True,
            0,
        )
    if now < target_time:
        # The slide's length for the spin: its path points and one more.
        spin = get_star_rotate_speed(len(track_points) + 1, end_time - slide_time)
        draw_note(star_kind, button, target_time - get_tap_appear_duration(1), target_time, get_note_angle(spin))

    if crossed(target_time):
        emit_tap_sfx(is_break(star_kind), is_ex(star_kind), JUDGMENT, target_time, scheduled=False)
        spawn_tap_effect(is_break(star_kind), JUDGMENT, layout_tap_effect(button))
    draw_tutorial_judge_text(layout_button_judge_text(button), is_break(star_kind), target_time)
    if crossed(slide_time) and Options.slide_sound:
        if is_break_slide(kind):
            emit_sfx(Effects.break_slide, slide_time, scheduled=False)
        else:
            emit_sfx(Effects.slide, slide_time, scheduled=False)

    if end_time <= now < get_slide_ok_end_time(end_time) and shows_slide_ok(JUDGMENT):
        layout = layout_slide_ok(track, button, is_mirrored, end_button)
        draw_slide_ok(get_slide_ok_sprite(layout, JUDGMENT, 0), layout.quad, end_time, get_z(LAYER_SLIDE_OK))
