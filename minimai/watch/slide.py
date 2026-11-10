from __future__ import annotations
from math import floor
from typing import cast

from sonolus.script.archetype import (
    EntityRef,
    StandardImport,
    WatchArchetype,
    entity_data,
    imported,
)
from sonolus.script.array import Dim
from sonolus.script.bucket import Bucket, Judgment
from sonolus.script.containers import VarArray
from sonolus.script.interval import clamp, unlerp
from sonolus.script.runtime import is_replay, time
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names, buckets
from minimai.lib.effect import (
    emit_break_slide_end_sfx,
    emit_firework_sfx,
    is_hit,
    report_note_time,
    schedule_slide_sfx,
)
from minimai.lib.game import ArcadeJudgment, Button, apply_button_mirror_option, is_mirror_option_reflection
from minimai.lib.layout import SLIDE_TRACK_POINTS
from minimai.lib.options import Options
from minimai.lib.scoring import BaseWeight, add_note_to_total
from minimai.lib.slide import (
    MAX_CHAIN_LENGTH,
    SLIDE_PATH_ALL_HIDDEN,
    SlideKind,
    SlideTrackKind,
    draw_slide,
    get_chain_max_total,
    get_chain_star_rotate_speed,
    get_chain_start_beat,
    get_conn_slide_kind,
    get_next_slide_index,
    get_path_total_beats,
    get_segment_beats,
    get_slide_appear_duration,
    is_break_slide,
    is_conn_slide_at,
)
from minimai.lib.streams import Streams
from minimai.watch.note import WatchBaseNote


class WatchBaseSlide(WatchArchetype):
    beat: StandardImport.BEAT
    track: SlideTrackKind = imported()
    start_button: Button = imported(name="button", default=1)
    is_mirrored: bool = imported(name="isMirrored")
    # In beats. Only the chain head's wait is used
    wait_duration: float = imported(name="waitDuration")
    # In beats. Summed along the path from the chain head to a final slide; that total is
    # split across the path's segments by bar count.
    slide_duration: float = imported(name="slideDuration")
    speed: float = imported(default=1)
    # Only meaningful on the chain head (or a standalone slide).
    head_note_ref: EntityRef[WatchBaseNote] = imported(name="headNote")
    prev_slide_ref: EntityRef[WatchBaseSlide] = imported(name="prevSlide")
    firework: bool = imported(default=False)

    # From the replay (final slides). Without one, a critical perfect when the star clears the
    # last area, and the end effects on arrival.
    judged_time: float = imported(name="judgedTime")
    arcade_judgment: ArcadeJudgment = imported(name="arcadeJudgment")
    effect_time: float = imported(name="effectTime")
    standard_judgment: StandardImport.JUDGMENT
    accuracy: StandardImport.ACCURACY

    kind: SlideKind = entity_data()
    start_time: float = entity_data()
    target_time: float = entity_data()
    segment_start_beat: float = entity_data()
    segment_duration: float = entity_data()
    chain_start_beat: float = entity_data()
    exit_time: float = entity_data()

    @classmethod
    def score_weight(cls) -> float:
        return BaseWeight.SLIDE

    @property
    def segment_slide_time(self) -> float:
        return beat_to_time(self.segment_start_beat)

    @property
    def segment_end_time(self) -> float:
        return beat_to_time(self.segment_start_beat + self.segment_duration)

    @property
    def is_chain_head(self) -> bool:
        return self.prev_slide_ref.index <= 0

    @property
    def judgment_time(self) -> float:
        return buckets.slide_judgment_time(self.track, self.segment_slide_time, self.segment_end_time)

    @property
    def judgment_window(self) -> buckets.ArcadeWindow:
        return buckets.slide_judgment_window(
            self.track, self.target_time, self.segment_slide_time, self.segment_end_time
        )

    def resolve_kind(self) -> SlideKind:
        return cast(SlideKind, self.key)

    def resolve_chain(self):
        preceding_beats = 0.0
        depth = 0
        head_index = self.index
        prev_index = self.prev_slide_ref.index
        while prev_index > 0 and depth < MAX_CHAIN_LENGTH:
            preceding_beats += get_segment_beats(prev_index)
            head_index = prev_index
            prev_index = WatchBaseSlide.at(prev_index, check=False).prev_slide_ref.index
            depth += 1
        head = WatchBaseSlide.at(head_index, check=False)
        head_start_beat = head.beat + head.wait_duration

        self.segment_start_beat = head_start_beat + preceding_beats
        self.segment_duration = get_segment_beats(self.index)
        self.chain_start_beat = head_start_beat

    def preprocess(self):
        self.start_button = apply_button_mirror_option(self.start_button)
        if is_mirror_option_reflection():
            self.is_mirrored = not self.is_mirrored
        self.kind = self.resolve_kind()
        self.target_time = beat_to_time(self.beat)
        self.start_time = self.target_time - get_slide_appear_duration(self.speed)
        self.resolve_chain()

        if self.head_note_ref.index > 0:
            self.head_note_ref.get().slide_rotate_speed = get_chain_star_rotate_speed(
                self.index, self.segment_start_beat
            )
        if self.is_chain_head:
            report_note_time(self.target_time)
            schedule_slide_sfx(is_break_slide(self.kind), beat_to_time(self.chain_start_beat))

        if not self.is_scored:
            self.exit_time = get_conn_exit_time(self.index)
            return
        add_note_to_total(self.score_weight(), is_break_slide(self.kind))
        self.result.bucket = buckets.get_slide_bucket(self.kind)
        self.result.target_time = self.judgment_time
        if not is_replay():
            self.arcade_judgment = ArcadeJudgment.CRITICAL_PERFECT
            self.judged_time = self.judgment_time
            self.effect_time = self.segment_end_time
            self.standard_judgment = Judgment.PERFECT
        if not is_hit(self.arcade_judgment):
            self.result.bucket = Bucket(-1)
        elif self.result.bucket.id != -1:
            self.result.bucket_value = self.judgment_window.normalize_error(self.accuracy)
        self.exit_time = get_final_exit_time(self.index)

        if self.arcade_judgment == ArcadeJudgment.NONE:
            return
        if Options.auto_sfx:
            self.emit_end_sfx(ArcadeJudgment.CRITICAL_PERFECT, self.segment_end_time, self.segment_end_time)
        else:
            self.emit_end_sfx(self.arcade_judgment, self.judged_time, self.effect_time)

    def spawn_time(self) -> float:
        return self.start_time

    def despawn_time(self) -> float:
        return self.exit_time

    def update_parallel(self):
        draw_slide(
            self.kind,
            self.track,
            self.start_button,
            self.is_mirrored,
            self.path_hidden,
            self.start_time,
            self.target_time,
            self.segment_slide_time,
            self.segment_end_time,
            self.is_chain_head,
            self.is_scored,
        )

    @property
    def path_hidden(self) -> int:
        result = 0
        if is_replay():
            result = Streams.slide_path_hidden[self.index].get_previous_inclusive(time())
        elif self.is_scored and time() >= self.judged_time:
            result = SLIDE_PATH_ALL_HIDDEN
        else:
            # Gone where the star has been.
            count = len(SLIDE_TRACK_POINTS[self.track])
            progress = unlerp(self.segment_slide_time, self.segment_end_time, time())
            result = clamp(floor(progress * (count + 1)), 0, count)
        return result

    def emit_end_sfx(self, judgment: ArcadeJudgment, judged_at: float, arrive_at: float):
        if is_break_slide(self.kind):
            emit_break_slide_end_sfx(judgment, judged_at, scheduled=True)
        emit_firework_sfx(self.firework, judgment, arrive_at, scheduled=True)


class WatchBaseWifiSlide(WatchBaseSlide):
    pass


class WatchConnSlide(WatchBaseSlide):
    """Unscored head/middle segment of a connection chain. Its kind (colour) comes from the
    chain's final slide."""

    name = archetype_names.CONN_SLIDE_NOTE
    next_slide_ref: EntityRef[WatchBaseSlide] = imported(name="nextSlide")

    def resolve_kind(self) -> SlideKind:
        return get_conn_slide_kind(self.index, False)


class WatchConnWifiSlide(WatchBaseWifiSlide):
    """Unscored head/middle Wi-Fi of a connection chain."""

    name = archetype_names.CONN_WIFI_SLIDE_NOTE
    next_slide_ref: EntityRef[WatchBaseSlide] = imported(name="nextSlide")
    next_slide_l_ref: EntityRef[WatchBaseSlide] = imported(name="nextSlideL")
    next_slide_r_ref: EntityRef[WatchBaseSlide] = imported(name="nextSlideR")

    def resolve_kind(self) -> SlideKind:
        return get_conn_slide_kind(self.index, True)


def get_final_exit_time(index: int) -> float:
    """When the final slide at ``index`` despawns; from imported data only, so any preprocess order
    works: the end effects, or (not reached in the replay) the end of its input window."""
    slide = WatchBaseSlide.at(index, check=False)
    end_time = beat_to_time(get_chain_start_beat(index) + get_path_total_beats(index))
    result = end_time
    if is_replay():
        result = end_time + 36 / 60
        if slide.arcade_judgment != ArcadeJudgment.NONE:
            result = slide.effect_time
    return result


def get_conn_exit_time(index: int) -> float:
    """A chain part despawns with the last final slide after it, or at the end of its input window."""
    stack = VarArray[int, Dim[16]].new()
    stack.append(index)
    result = 0.0
    steps = 0
    while len(stack) > 0 and steps < MAX_CHAIN_LENGTH:
        current = stack.pop()
        if is_conn_slide_at(current):
            for branch in range(3):
                next_index = get_next_slide_index(current, branch)
                if next_index > 0 and not stack.is_full():
                    stack.append(next_index)
        else:
            result = max(result, get_final_exit_time(current))
        steps += 1
    chain_end_time = beat_to_time(
        get_chain_start_beat(index) + get_chain_max_total(index)
    )
    return min(result, chain_end_time + 36 / 60)


WatchNormalSlideNote = WatchBaseSlide.derive(archetype_names.NORMAL_SLIDE_NOTE, is_scored=True, key=SlideKind.NORMAL_SLIDE)
WatchBreakSlideNote = WatchBaseSlide.derive(archetype_names.BREAK_SLIDE_NOTE, is_scored=True, key=SlideKind.BREAK_SLIDE)
WatchEachSlideNote = WatchBaseSlide.derive(archetype_names.EACH_SLIDE_NOTE, is_scored=True, key=SlideKind.EACH_SLIDE)
WatchNormalWifiSlideNote = WatchBaseWifiSlide.derive(archetype_names.NORMAL_WIFI_SLIDE_NOTE, is_scored=True, key=SlideKind.WIFI_SLIDE)
WatchBreakWifiSlideNote = WatchBaseWifiSlide.derive(archetype_names.BREAK_WIFI_SLIDE_NOTE, is_scored=True, key=SlideKind.BREAK_WIFI_SLIDE)
WatchEachWifiSlideNote = WatchBaseWifiSlide.derive(archetype_names.EACH_WIFI_SLIDE_NOTE, is_scored=True, key=SlideKind.EACH_WIFI_SLIDE)

WATCH_SLIDE_ARCHETYPES = (
    WatchNormalSlideNote,
    WatchBreakSlideNote,
    WatchEachSlideNote,
    WatchNormalWifiSlideNote,
    WatchBreakWifiSlideNote,
    WatchEachWifiSlideNote,
    WatchConnSlide,
    WatchConnWifiSlide,
)
