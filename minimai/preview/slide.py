from __future__ import annotations

from typing import assert_never, cast

from sonolus.script.archetype import EntityRef, PreviewArchetype, StandardImport, entity_data, imported
from sonolus.script.interval import lerp
from sonolus.script.quad import Quad
from sonolus.script.record import Record
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names
from minimai.lib.game import Button, apply_button_mirror_option, is_mirror_option_reflection
from minimai.lib.skin import BaseSkin
from minimai.lib.slide import (
    MAX_CHAIN_LENGTH,
    SlideKind,
    SlideTrackKind,
    get_chain_start_beat,
    get_conn_slide_kind,
    get_path_total_beats,
    get_segment_beats,
    get_slide_end_button,
    is_wifi_conn_slide_at,
    is_wifi_slide,
    slide_at,
    wifi_conn_slide_at,
)
from minimai.preview.layout import (
    SLIDE_BAR_SPACING,
    SLIDE_WAIT_ALPHA_END,
    SLIDE_WAIT_ALPHA_START,
    SLIDE_WAIT_END_GAP,
    SLIDE_WAIT_SCALE,
    SlideTrackPoints,
    build_slide_track,
    build_wait_track,
    clip_to_column,
    get_button_lane,
    get_piece_fraction,
    get_slide_track_length,
    layout_shape_label,
    layout_slide_bar,
    report_end_time,
    report_judgment_beat,
    time_to_col,
)
from minimai.preview.note import PreviewBaseNote, draw_firework

Z_SLIDE = 1.5
Z_SHAPE_LABEL = 1.6

UPPER_HALF = (7, 8, 1, 2)


class ShapeLabel:
    """Indexes into ``BaseSkin.preview_shape_labels`` (PREVIEW_SHAPE_LABELS)."""
    LINE = 0
    CIRCLE_R = 1
    CIRCLE_L = 2
    CENTER = 3
    P = 4
    Q = 5
    PP = 6
    QQ = 7
    S = 8
    Z = 9
    REFLECT = 10
    WIFI = 11


class PreviewBaseSlide(PreviewArchetype):
    beat: StandardImport.BEAT
    track: SlideTrackKind = imported()
    start_button: Button = imported(name="button", default=1)
    is_mirrored: bool = imported(name="isMirrored")
    # In beats. Only the chain head's wait is used
    wait_duration: float = imported(name="waitDuration")
    # In beats. Summed along the path from the chain head to a final slide.
    slide_duration: float = imported(name="slideDuration")
    # Only meaningful on the chain head (or a standalone slide).
    head_note_ref: EntityRef[PreviewBaseNote] = imported(name="headNote")
    prev_slide_ref: EntityRef[PreviewBaseSlide] = imported(name="prevSlide")
    firework: bool = imported(default=False)

    kind: SlideKind = entity_data()
    target_time: float = entity_data()
    segment_start_beat: float = entity_data()
    segment_duration: float = entity_data()

    def preprocess(self):
        self.kind = self.resolve_kind()
        self.target_time = beat_to_time(self.beat)
        self.start_button = apply_button_mirror_option(self.start_button)
        if is_mirror_option_reflection():
            self.is_mirrored = not self.is_mirrored
        self.resolve_chain()
        self.report()

    def resolve_kind(self) -> SlideKind:
        return cast(SlideKind, self.key)

    def report(self):
        end_beat = get_chain_start_beat(self.index) + get_path_total_beats(self.index)
        report_end_time(beat_to_time(end_beat))
        report_judgment_beat(end_beat)

    def resolve_chain(self):
        """This part's own stretch of the chain's travel, as in play."""
        preceding_beats = 0.0
        prev_index = self.prev_slide_ref.index
        depth = 0
        while prev_index > 0 and depth < MAX_CHAIN_LENGTH:
            preceding_beats += get_segment_beats(prev_index)
            prev_index = slide_at(prev_index).prev_slide_ref.index
            depth += 1
        self.segment_start_beat = get_chain_start_beat(self.index) + preceding_beats
        self.segment_duration = get_segment_beats(self.index)

    def render(self):
        """The wait (chain head only) up the start lane, then this part's travel and its shape label.
        A Wi-Fi draws its center track, and the side tracks a connected slide continues from."""
        lane = get_button_lane(self.start_button)
        start_time = beat_to_time(self.segment_start_beat)
        end_time = beat_to_time(self.segment_start_beat + self.segment_duration)
        if self.prev_slide_ref.index <= 0 and start_time > self.target_time:
            draw_slide_bars(
                self.kind,
                build_wait_track(lane, self.target_time, start_time),
                SlideBarStyle(
                    scale=SLIDE_WAIT_SCALE,
                    alpha_start=SLIDE_WAIT_ALPHA_START,
                    alpha_end=SLIDE_WAIT_ALPHA_END,
                    end_gap=SLIDE_WAIT_END_GAP,
                ),
                (Z_SLIDE, self.target_time),
            )
        travel = SlideBarStyle(scale=1.0, alpha_start=1.0, alpha_end=1.0, end_gap=0.0)
        track = self.track
        if is_wifi_slide(self.kind):
            track = SlideTrackKind.FAN_C
            if is_wifi_conn_slide_at(self.index):
                wifi = wifi_conn_slide_at(self.index)
                if wifi.next_slide_l_ref.index > 0:
                    draw_slide_bars(
                        self.kind,
                        build_slide_track(SlideTrackKind.FAN_L, self.start_button, self.is_mirrored, start_time, end_time),
                        travel,
                        (Z_SLIDE, start_time),
                    )
                if wifi.next_slide_r_ref.index > 0:
                    draw_slide_bars(
                        self.kind,
                        build_slide_track(SlideTrackKind.FAN_R, self.start_button, self.is_mirrored, start_time, end_time),
                        travel,
                        (Z_SLIDE, start_time),
                    )
        draw_slide_bars(
            self.kind,
            build_slide_track(track, self.start_button, self.is_mirrored, start_time, end_time),
            travel,
            (Z_SLIDE, start_time),
        )
        draw_shape_label(get_shape_label(self.track, self.start_button, self.is_mirrored), lane, start_time)
        if self.firework:
            end_button = get_slide_end_button(track, self.start_button, self.is_mirrored)
            draw_firework(get_button_lane(end_button), end_time)


def get_shape_label(track: SlideTrackKind, button: Button, is_mirrored: bool) -> int:
    """The simai shape for a track as drawn: the inverse of the level builder's shape → track. "^" comes
    out as ">" or "<"."""
    result = ShapeLabel.WIFI
    if SlideTrackKind.CIRCLE_1 <= track <= SlideTrackKind.CIRCLE_8:
        # An unmirrored circle runs clockwise: ">" from the upper half, "<" from the lower.
        upper = button in UPPER_HALF
        result = ShapeLabel.CIRCLE_L
        if upper != is_mirrored:
            result = ShapeLabel.CIRCLE_R
    elif SlideTrackKind.LINE_3 <= track <= SlideTrackKind.LINE_5:
        result = ShapeLabel.LINE
    elif SlideTrackKind.CENTER_1 <= track <= SlideTrackKind.CENTER_4:
        result = ShapeLabel.CENTER
    elif SlideTrackKind.LOOP_IN_1 <= track <= SlideTrackKind.LOOP_IN_8:
        result = ShapeLabel.Q if is_mirrored else ShapeLabel.P
    elif SlideTrackKind.LOOP_OUT_1 <= track <= SlideTrackKind.LOOP_OUT_8:
        result = ShapeLabel.QQ if is_mirrored else ShapeLabel.PP
    elif SlideTrackKind.REFLECT_2 <= track <= SlideTrackKind.REFLECT_5:
        result = ShapeLabel.REFLECT
    elif track == SlideTrackKind.ZIG_ZAG:
        result = ShapeLabel.Z if is_mirrored else ShapeLabel.S
    return result


def draw_shape_label(label: int, lane: float, time: float):
    BaseSkin.preview_shape_labels[label].draw(layout_shape_label(lane, time), z=(Z_SHAPE_LABEL, time))


class SlideBarStyle(Record):
    scale: float
    # Alpha from the first slide bar to the last, eased out (quad) over the track's time.
    alpha_start: float
    alpha_end: float
    # Leave out slide bars closer than this many spacings to the track's end.
    end_gap: float


def draw_slide_bars(kind: SlideKind, path: SlideTrackPoints, style: SlideBarStyle, z: tuple):
    """Slide bars along the track, the first right at its start, then one every spacing, each pointing
    the way the track goes. A jump starts the spacing over."""
    spacing = SLIDE_BAR_SPACING * style.scale
    total = get_slide_track_length(path)
    start_time = path[0].time
    end_time = path[len(path) - 1].time
    walked = 0.0
    next_at = 0.0
    for i in range(1, len(path)):
        if path[i].jump:
            next_at = walked
        else:
            a = path[i - 1]
            b = path[i]
            for col in range(time_to_col(min(a.time, b.time)), time_to_col(max(a.time, b.time)) + 1):
                piece = clip_to_column(a, b, col)
                if piece.inside:
                    piece_start = piece.start
                    piece_end = piece.end
                    length = (piece_end - piece_start).magnitude
                    while next_at <= walked + length and next_at <= total - style.end_gap * spacing + 1e-6:
                        u = 0.0
                        if length > 0:
                            u = (next_at - walked) / length
                        position = piece_start + (piece_end - piece_start) * u
                        progress = 1.0
                        if end_time > start_time:
                            progress = (a.time + (b.time - a.time) * get_piece_fraction(a, b, col, u) - start_time) / (end_time - start_time)
                        alpha = lerp(style.alpha_start, style.alpha_end, progress)
                        draw_slide_bar(kind, layout_slide_bar(position, piece_end - piece_start, style.scale), z, alpha)
                        next_at += spacing
                    walked += length


def draw_slide_bar(kind: SlideKind, layout: Quad, z: tuple, alpha: float):
    match kind:
        case SlideKind.NORMAL_SLIDE | SlideKind.WIFI_SLIDE:
            BaseSkin.slide_path.draw(layout, z=z, a=alpha)
        case SlideKind.EACH_SLIDE | SlideKind.EACH_WIFI_SLIDE:
            BaseSkin.each_slide_path.draw(layout, z=z, a=alpha)
        case SlideKind.BREAK_SLIDE | SlideKind.BREAK_WIFI_SLIDE:
            BaseSkin.break_slide_path.draw(layout, z=z, a=alpha)
        case _:
            assert_never(kind)


class PreviewBaseWifiSlide(PreviewBaseSlide):
    pass


class PreviewConnSlide(PreviewBaseSlide):
    """A head or middle part of a connection chain; the final slides after it report the chain's end."""

    name = archetype_names.CONN_SLIDE_NOTE
    next_slide_ref: EntityRef[PreviewBaseSlide] = imported(name="nextSlide")

    def resolve_kind(self) -> SlideKind:
        return get_conn_slide_kind(self.index, False)

    def report(self):
        pass


class PreviewConnWifiSlide(PreviewBaseWifiSlide):
    name = archetype_names.CONN_WIFI_SLIDE_NOTE
    next_slide_ref: EntityRef[PreviewBaseSlide] = imported(name="nextSlide")
    next_slide_l_ref: EntityRef[PreviewBaseSlide] = imported(name="nextSlideL")
    next_slide_r_ref: EntityRef[PreviewBaseSlide] = imported(name="nextSlideR")

    def resolve_kind(self) -> SlideKind:
        return get_conn_slide_kind(self.index, True)

    def report(self):
        pass


PreviewNormalSlideNote = PreviewBaseSlide.derive(archetype_names.NORMAL_SLIDE_NOTE, is_scored=True, key=SlideKind.NORMAL_SLIDE)
PreviewBreakSlideNote = PreviewBaseSlide.derive(archetype_names.BREAK_SLIDE_NOTE, is_scored=True, key=SlideKind.BREAK_SLIDE)
PreviewEachSlideNote = PreviewBaseSlide.derive(archetype_names.EACH_SLIDE_NOTE, is_scored=True, key=SlideKind.EACH_SLIDE)
PreviewNormalWifiSlideNote = PreviewBaseWifiSlide.derive(archetype_names.NORMAL_WIFI_SLIDE_NOTE, is_scored=True, key=SlideKind.WIFI_SLIDE)
PreviewBreakWifiSlideNote = PreviewBaseWifiSlide.derive(archetype_names.BREAK_WIFI_SLIDE_NOTE, is_scored=True, key=SlideKind.BREAK_WIFI_SLIDE)
PreviewEachWifiSlideNote = PreviewBaseWifiSlide.derive(archetype_names.EACH_WIFI_SLIDE_NOTE, is_scored=True, key=SlideKind.EACH_WIFI_SLIDE)

PREVIEW_SLIDE_ARCHETYPES = (
    PreviewNormalSlideNote,
    PreviewBreakSlideNote,
    PreviewEachSlideNote,
    PreviewNormalWifiSlideNote,
    PreviewBreakWifiSlideNote,
    PreviewEachWifiSlideNote,
    PreviewConnSlide,
    PreviewConnWifiSlide,
)
