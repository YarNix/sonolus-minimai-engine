from __future__ import annotations
from typing import cast, assert_never

from sonolus.script.archetype import (
    EntityRef,
    PlayArchetype,
    StandardImport,
    entity_data,
    exported,
    imported,
    entity_memory,
    shared_memory,
)
from sonolus.script.array import Array, Dim
from sonolus.script.bucket import Bucket, Judgment
from sonolus.script.containers import VarArray
from sonolus.script.globals import level_memory
from sonolus.script.interval import Interval
from sonolus.script.runtime import input_offset, offset_adjusted_time, time
from sonolus.script.timing import beat_to_time

from minimai.typing import override_archetype
from minimai.lib import archetype_names, buckets
from minimai.lib.effect import emit_break_slide_end_sfx, emit_firework_sfx, report_note_time, schedule_slide_sfx
from minimai.lib.firework import spawn_firework
from minimai.lib.initialization import init_common
from minimai.lib.slide_ok import spawn_slide_ok
from minimai.lib.scoring import BaseWeight, add_note_to_total, report_score, is_challenge_over
from minimai.lib.game import ArcadeJudgment, Button, apply_button_mirror_option, is_mirror_option_reflection
from minimai.lib.options import Options
from minimai.lib.streams import STREAM_START_TIME, Streams
from minimai.lib.layout import layout_button_firework_center, layout_slide_ok
from minimai.lib.slide import (
    MAX_CHAIN_LENGTH,
    SLIDE_PATH_ALL_HIDDEN,
    SlideBranch,
    SlideChainInfo,
    SlideKind,
    SlideQueueState,
    SlideTrackKind,
    draw_slide,
    get_chain_max_total,
    get_chain_star_rotate_speed,
    get_chain_total_areas,
    get_fade_in_end_time,
    get_conn_slide_kind,
    get_next_slide_index,
    get_segment_beats,
    get_slide_appear_duration,
    get_slide_end_button,
    is_break_slide,
)
from minimai.play import note


class BaseSlide(PlayArchetype):
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
    head_note_ref: EntityRef[note.BaseNote] = imported(name="headNote")
    prev_slide_ref: EntityRef[BaseSlide] = imported(name="prevSlide")
    firework: bool = imported(default=False)

    kind: SlideKind = entity_data()
    start_time: float = entity_data()
    target_time: float = entity_data()

    # Segment specific info
    segment_start_beat: float = entity_data()
    segment_duration: float = entity_data()

    # Chain data
    chain_start_beat: float = entity_data()
    chain_end_beat: float = entity_data()
    chain_depth: int = entity_data()
    chain_total_areas: int = entity_data()

    # Computed variant
    is_wifi: bool = entity_data()
    parent_is_wifi: bool = entity_data()
    next_indices: Array[int, Dim[3]] = entity_data()

    input_interval: Interval = shared_memory()
    unadjusted_input_interval: Interval = shared_memory()
    is_checkable: bool = shared_memory()
    judge_queue: SlideQueueState = shared_memory()

    judgment: ArcadeJudgment = entity_memory()
    is_judgment_reported: bool = entity_memory()
    despawn_time: float = entity_memory()
    recorded_path_hidden: int = entity_memory()

    # When the judgment was made, and what it was. NONE if never judged.
    judged_time: float = exported(name="judgedTime")
    arcade_judgment: ArcadeJudgment = exported(name="arcadeJudgment")
    # When the end effects played, after the judgment.
    effect_time: float = exported(name="effectTime")

    @classmethod
    def score_weight(cls) -> float:
        return BaseWeight.SLIDE

    @property
    def segment_slide_time(self) -> float:
        """The "start" time of this segment. The star begins traversing the track."""
        return beat_to_time(self.segment_start_beat)

    @property
    def segment_end_time(self) -> float:
        """The "arrive" time of this segment. The star finished traversing the track."""
        return beat_to_time(self.segment_start_beat + self.segment_duration)

    @property
    def chain_end_time(self) -> float:
        """The arrive time of the latest final slide reachable from this segment."""
        return beat_to_time(self.chain_end_beat)

    @property
    def chain_start_time(self) -> float:
        return beat_to_time(self.chain_start_beat)

    @property
    def is_judged(self) -> bool:
        return self.judgment != ArcadeJudgment.NONE

    @property
    def is_chain_head(self) -> bool:
        return self.prev_slide_ref.index <= 0

    @property
    def is_chain_final(self) -> bool:
        # Final slides are the scored archetypes; ConnSlide/ConnWifiSlide are unscored.
        return self.is_scored

    @property
    def chain_info(self) -> SlideChainInfo:
        return SlideChainInfo(
            is_part=not self.is_chain_head or not self.is_chain_final,
            is_head=self.is_chain_head,
            is_final=self.is_chain_final,
            total_areas=self.chain_total_areas,
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
            prev_index = BaseSlide.at(prev_index).prev_slide_ref.index
            depth += 1
        head = BaseSlide.at(head_index)
        head_start_beat = head.beat + head.wait_duration

        self.segment_start_beat = head_start_beat + preceding_beats
        self.segment_duration = get_segment_beats(self.index)
        self.chain_depth = depth
        self.chain_start_beat = head_start_beat
        self.chain_end_beat = head_start_beat + get_chain_max_total(self.index)
        self.chain_total_areas = get_chain_total_areas(head_index)


    def spawn_order(self) -> float:
        return self.start_time

    def should_spawn(self) -> bool:
        return time() >= self.start_time or is_challenge_over()

    def preprocess(self):
        init_common()
        # A reflected slide is the same track from the mirrored button, reflected the other way.
        self.start_button = apply_button_mirror_option(self.start_button)
        if is_mirror_option_reflection():
            self.is_mirrored = not self.is_mirrored
        self.kind = self.resolve_kind()
        if self.is_scored:
            self.result.bucket = buckets.get_slide_bucket(self.kind)
        self.is_wifi = BaseWifiSlide.is_at(self.index)
        self.parent_is_wifi = self.prev_slide_ref.index > 0 and BaseWifiSlide.is_at(self.prev_slide_ref.index)
        self.next_indices = Array(
            get_next_slide_index(self.index, SlideBranch.BRANCH_C),
            get_next_slide_index(self.index, SlideBranch.BRANCH_L),
            get_next_slide_index(self.index, SlideBranch.BRANCH_R),
        )
        self.target_time = beat_to_time(self.beat)
        self.start_time = self.target_time - get_slide_appear_duration(self.speed)
        self.resolve_chain()

        window = self.input_window
        self.input_interval = window + input_offset()
        self.unadjusted_input_interval = window

        if self.head_note_ref.index > 0:
            self.head_note_ref.get().slide_rotate_speed = get_chain_star_rotate_speed(
                self.index, self.segment_start_beat
            )

        if self.is_chain_head:
            report_note_time(self.target_time)
        if self.is_scored:
            add_note_to_total(self.score_weight(), is_break_slide(self.kind))

    def initialize(self):
        Streams.slide_path_hidden[self.index][STREAM_START_TIME] = 0
        if is_challenge_over():
            return
        # The slide sound when the star starts moving; auto SFX: the break end on arrival.
        if self.is_chain_head:
            schedule_slide_sfx(is_break_slide(self.kind), self.chain_start_time)
        if self.is_scored:
            if is_break_slide(self.kind):
                emit_break_slide_end_sfx(ArcadeJudgment.CRITICAL_PERFECT, self.segment_end_time, scheduled=True)
            self.emit_arrive_sfx(ArcadeJudgment.CRITICAL_PERFECT, self.segment_end_time, scheduled=True)

    def update_sequential(self):
        if self.despawn:
            return
        if is_challenge_over():
            self.despawn = True
            return
        if self.is_judged and not self.is_judgment_reported:
            # Judged in update_parallel
            # Report score here in sequential callback
            self.is_judgment_reported = True
            report_score(self.score_weight(), is_break_slide(self.kind), self.judgment)
        if (time() in self.input_interval
            and not self.judge_queues_finished
            and not self.is_judged):
            if not SlideMemory.active_slide_inputs.is_full():
                SlideMemory.active_slide_inputs.append(self.ref().with_archetype(BaseSlide))

    def update_parallel(self):
        if self.despawn:
            return
        if self.is_chain_final:
            self.update_final()
        else:
            self.update_connection()
        if self.despawn:
            return
        path_hidden = self.path_hidden_count if not self.is_judged else SLIDE_PATH_ALL_HIDDEN
        if path_hidden != self.recorded_path_hidden:
            Streams.slide_path_hidden[self.index][offset_adjusted_time()] = path_hidden
            self.recorded_path_hidden = path_hidden
        draw_slide(
            self.kind,
            self.track,
            self.start_button,
            self.is_mirrored,
            path_hidden,
            self.start_time,
            self.target_time,
            self.segment_slide_time,
            self.segment_end_time,
            self.is_chain_head,
            self.is_chain_final,
            self.chain_depth,
        )

    def terminate(self):
        if self.is_chain_final and self.is_judged:
            self.effect_time = offset_adjusted_time()
            self.play_end_effects()

    def update_final(self):
        """
        Update parallel for the final segment of the slide
        
        Only the final segment can handle judgment
        """
        if self.is_judged:
            if time() >= self.despawn_time:
                self.emit_arrive_sfx(self.judgment, time(), scheduled=False)
                self.despawn = True
            return
        if time() > self.input_interval.end:
            self.handle_miss()
            return
        if self.judge_queues_finished:
            self.handle_finished()

    def update_connection(self):
        """
        Update parallel for the connection segment of the slide
        
        Ending propagates from the final slide back to its parents:
        a non-final part ends once every part continuing from it has ended.
        """
        all_next_ended = all(next_index <= 0 or BaseSlide.at(next_index, check=False).is_despawned for next_index in self.next_indices)
        if all_next_ended or time() > self.input_interval.end:
            self.despawn = True

    def get_despawn_wait_duration(self, actual_time: float) -> float:
        if actual_time < self.chain_start_time:
            # very early
            return (self.chain_start_time - actual_time) / 2
        if actual_time - self.judgment_time >= 36 / 60:
            # very late Good
            return 0.05
        # remaining star travel (travel × judgment const)
        return self.segment_end_time - self.judgment_time

    def check_judge_queues(self) -> bool:
        return False # Stub for override

    @property
    def judge_queues_finished(self) -> bool:
        return self.queue_remaining == 0

    @property
    def queue_remaining(self) -> int:
        return 0 # Stub for override

    @property
    def parent_total_remaining(self) -> int:
        if self.parent_is_wifi:
            return BaseWifiSlide.at(self.prev_slide_ref.index, check=False).total_remaining
        else:
            return BaseSlide.at(self.prev_slide_ref.index, check=False).queue_remaining

    @property
    def path_hidden_count(self) -> int:
        return 0 # Stub for override

    def force_finish(self): ... # Stub for override

    def parent_force_finish(self):
        if self.parent_is_wifi:
            BaseWifiSlide.at(self.prev_slide_ref.index, check=False).force_finish()
        else:
            BaseSlide.at(self.prev_slide_ref.index).force_finish()

    @property
    def input_window(self) -> Interval:
        input_end = self.segment_end_time + 36 / 60
        if not self.is_chain_final:
            input_end = self.chain_end_time + 36 / 60
        return Interval(get_fade_in_end_time(self.target_time), input_end)

    ## Judgment (final slides only)

    @property
    def judgment_time(self) -> float:
        """Expected timing of the final judgment area for this slide."""
        return buckets.slide_judgment_time(self.track, self.segment_slide_time, self.segment_end_time)

    @property
    def judgment_window(self) -> buckets.ArcadeWindow:
        return buckets.slide_judgment_window(
            self.track, self.target_time, self.segment_slide_time, self.segment_end_time
        )

    def handle_finished(self):
        if self.despawn or not self.is_scored:
            return
        self.judge(time())

    def judge(self, actual_time: float):
        if self.is_judged:
            return

        judgment = self.judgment_window.judge(actual_time, self.judgment_time)
        if not Options.strict_slide_judgment and judgment <= ArcadeJudgment.LOW_PERFECT:
            # Slide perfect judgment always round up
            judgment = ArcadeJudgment.CRITICAL_PERFECT
        error = self.judgment_window.good.clamp(actual_time - self.judgment_time)
        self.result.judgment = buckets.arcade_judgement_to_normal(judgment)
        self.result.accuracy = error
        if self.result.bucket.id != -1:
            self.result.bucket_value = self.judgment_window.normalize_error(error)
        self.judgment = judgment
        self.export_judgment()
        self.despawn_time = time() + self.get_despawn_wait_duration(actual_time)
        if is_break_slide(self.kind):
            emit_break_slide_end_sfx(judgment, actual_time, scheduled=False)

    def emit_arrive_sfx(self, judgment: ArcadeJudgment, at: float, scheduled: bool):
        emit_firework_sfx(self.firework, judgment, at, scheduled)

    def play_end_effects(self):
        # A Wi-Fi's track ends at its center.
        end_button = get_slide_end_button(self.track, self.start_button, self.is_mirrored)
        spawn_firework(self.firework, self.judgment, layout_button_firework_center(end_button), time())
        spawn_slide_ok(
            self.judgment,
            self.result.accuracy,
            layout_slide_ok(self.track, self.start_button, self.is_mirrored, end_button),
            self.target_time,
            self.index,
            time(),
        )

    def handle_miss(self):
        if self.queue_remaining == 1:
            self.result.judgment = Judgment.GOOD
            self.result.accuracy = self.judgment_window.good.end
            if self.result.bucket.id != -1:
                self.result.bucket_value = self.judgment_window.normalize_error(self.result.accuracy)
            self.judgment = ArcadeJudgment.GOOD
        else:
            self.result.judgment = Judgment.MISS
            self.result.accuracy = 0
            self.result.bucket = Bucket(-1)
            self.judgment = ArcadeJudgment.MISS
        self.export_judgment()
        # Despawns (with the arrive SFX) in the next update_parallel, after the score is reported.
        self.despawn_time = time()

    def export_judgment(self):
        self.judged_time = offset_adjusted_time()
        self.arcade_judgment = self.judgment


def is_single_entity(slide: BaseSlide) -> bool:
    return not slide.is_wifi

class BaseSingleSlide(BaseSlide):
    @override_archetype(is_single_entity)
    def check_judge_queues(self) -> bool:
        return self.judge_queue.check_queue(
            self.track,
            self.start_button,
            self.is_mirrored,
            self.is_chain_final,
            self.chain_info,
        )

    @override_archetype(is_single_entity)
    @property
    def queue_remaining(self) -> int:
        return self.judge_queue.get_remaining_area(self.track)

    @override_archetype(is_single_entity)
    @property
    def path_hidden_count(self) -> int:
        return self.judge_queue.get_path_hidden_count(self.track)

    @override_archetype(is_single_entity)
    def force_finish(self):
        self.judge_queue.force_finish(self.track)


def is_wifi_entity(slide: BaseSlide) -> bool:
    return slide.is_wifi

class BaseWifiSlide(BaseSlide):
    """Wi-Fi slide. The inherited ``judge_queue`` is the centre (FAN_C) queue."""

    judge_queue_l: SlideQueueState = shared_memory()
    judge_queue_r: SlideQueueState = shared_memory()

    @override_archetype(is_wifi_entity)
    def check_judge_queues(self) -> bool:
        chain = self.chain_info
        triggered_l = self.judge_queue_l.check_queue(
            SlideTrackKind.FAN_L,
            self.start_button,
            self.is_mirrored,
            self.next_indices[SlideBranch.BRANCH_L] <= 0,
            chain,
        )
        triggered_c = self.judge_queue.check_queue(
            SlideTrackKind.FAN_C,
            self.start_button,
            self.is_mirrored,
            self.next_indices[SlideBranch.BRANCH_C] <= 0,
            chain,
        )
        triggered_r = self.judge_queue_r.check_queue(
            SlideTrackKind.FAN_R,
            self.start_button,
            self.is_mirrored,
            self.next_indices[SlideBranch.BRANCH_R] <= 0,
            chain,
        )
        return triggered_l or triggered_c or triggered_r

    def get_branch_remaining(self, branch: SlideBranch) -> int:
        match branch:
            case SlideBranch.BRANCH_C:
                return self.judge_queue.get_remaining_area(SlideTrackKind.FAN_C)
            case SlideBranch.BRANCH_L:
                return self.judge_queue_l.get_remaining_area(SlideTrackKind.FAN_L)
            case SlideBranch.BRANCH_R:
                return self.judge_queue_r.get_remaining_area(SlideTrackKind.FAN_R)
            case _:
                assert_never(branch)
                return 0

    @property
    def total_remaining(self) -> int:
        return sum(self.get_branch_remaining(branch) for branch in SlideBranch)

    @override_archetype(is_wifi_entity)
    @property
    def queue_remaining(self) -> int:
        return max(self.get_branch_remaining(branch) for branch in SlideBranch)

    @override_archetype(is_wifi_entity)
    @property
    def path_hidden_count(self) -> int:
        # The rendered Wi-Fi path is shared; it follows the slowest branch.
        remaining_c = self.get_branch_remaining(SlideBranch.BRANCH_C)
        remaining_l = self.get_branch_remaining(SlideBranch.BRANCH_L)
        remaining_r = self.get_branch_remaining(SlideBranch.BRANCH_R)
        hidden = min(
            self.judge_queue.get_path_hidden_count(SlideTrackKind.FAN_C),
            self.judge_queue_l.get_path_hidden_count(SlideTrackKind.FAN_L),
            self.judge_queue_r.get_path_hidden_count(SlideTrackKind.FAN_R),
        )
        if remaining_c == 0 and remaining_l == 0 and remaining_r == 0:
            hidden = SLIDE_PATH_ALL_HIDDEN
        elif remaining_c == 0 and remaining_l <= 1 and remaining_r <= 1:
            hidden = max(hidden, 9)
        return hidden

    @override_archetype(is_wifi_entity)
    def force_finish(self):
        self.judge_queue.force_finish(SlideTrackKind.FAN_C)
        self.judge_queue_l.force_finish(SlideTrackKind.FAN_L)
        self.judge_queue_r.force_finish(SlideTrackKind.FAN_R)

class ConnSlide(BaseSingleSlide):
    """Unscored head/middle segment of a connection chain. Its kind (colour) comes from the
    chain's final slide."""

    name = archetype_names.CONN_SLIDE_NOTE
    next_slide_ref: EntityRef[BaseSlide] = imported(name="nextSlide")

    def resolve_kind(self) -> SlideKind:
        return get_conn_slide_kind(self.index, False)


class ConnWifiSlide(BaseWifiSlide):
    """Unscored head/middle Wi-Fi of a connection chain. Each branch may continue into
    another slide; a branch that does not continue is never judged."""

    name = archetype_names.CONN_WIFI_SLIDE_NOTE
    next_slide_ref: EntityRef[BaseSlide] = imported(name="nextSlide")
    next_slide_l_ref: EntityRef[BaseSlide] = imported(name="nextSlideL")
    next_slide_r_ref: EntityRef[BaseSlide] = imported(name="nextSlideR")

    def resolve_kind(self) -> SlideKind:
        return get_conn_slide_kind(self.index, True)


@level_memory
class SlideMemory:
    active_slide_inputs: VarArray[EntityRef[BaseSlide], Dim[64]]


NormalSlideNote = BaseSingleSlide.derive(archetype_names.NORMAL_SLIDE_NOTE, is_scored=True, key=SlideKind.NORMAL_SLIDE)
BreakSlideNote = BaseSingleSlide.derive(archetype_names.BREAK_SLIDE_NOTE, is_scored=True, key=SlideKind.BREAK_SLIDE)
EachSlideNote = BaseSingleSlide.derive(archetype_names.EACH_SLIDE_NOTE, is_scored=True, key=SlideKind.EACH_SLIDE)
NormalWifiSlideNote = BaseWifiSlide.derive(archetype_names.NORMAL_WIFI_SLIDE_NOTE, is_scored=True, key=SlideKind.WIFI_SLIDE)
BreakWifiSlideNote = BaseWifiSlide.derive(archetype_names.BREAK_WIFI_SLIDE_NOTE, is_scored=True, key=SlideKind.BREAK_WIFI_SLIDE)
EachWifiSlideNote = BaseWifiSlide.derive(archetype_names.EACH_WIFI_SLIDE_NOTE, is_scored=True, key=SlideKind.EACH_WIFI_SLIDE)

SLIDE_ARCHETYPES = (
    NormalSlideNote,
    BreakSlideNote,
    EachSlideNote,
    NormalWifiSlideNote,
    BreakWifiSlideNote,
    EachWifiSlideNote,
    ConnSlide,
    ConnWifiSlide,
)