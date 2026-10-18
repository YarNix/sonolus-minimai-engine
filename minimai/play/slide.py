from __future__ import annotations
from typing import cast

from sonolus.script.globals import level_memory
from sonolus.script.array import Dim
from sonolus.script.containers import VarArray
from sonolus.script.runtime import input_offset, time
from sonolus.script.interval import Interval
from sonolus.script.timing import beat_to_time
from sonolus.script.bucket import Bucket, Judgment
from sonolus.script.archetype import (
    EntityRef,
    PlayArchetype,
    StandardImport,
    entity_data,
    entity_memory,
    shared_memory,
    imported,
)

from minimai.lib import archetype_names, buckets
from minimai.lib.game import Button
from minimai.lib.slide import (
    ActiveSlideJudgeQueue,
    SlideKind,
    SlideTrackKind,
    advance_slide_judge_queue,
    check_slide_judge_queue,
    get_slide_appear_duration,
    draw_slide,
    SLIDE_JUDGMENT_CONST
)
from minimai.play import note

class BaseSlide(PlayArchetype):
    beat: StandardImport.BEAT
    track: SlideTrackKind = imported()
    start_button: Button = imported(name="button", default=1)
    is_mirrored: bool = imported(name="isMirrored")
    wait_duration: float = imported(name="waitDuration")   # in seconds
    slide_duration: float = imported(name="slideDuration")  # in seconds
    speed: float = imported(default=1)
    head_note_ref: EntityRef[note.BaseNote] = imported(name="headNote")
    next_slide_ref: EntityRef[BaseSlide] = imported(name="nextSlide")

    kind: SlideKind = entity_data()
    start_time: float = entity_data()
    target_time: float = entity_data()

    input_interval: Interval = shared_memory()
    unadjusted_input_interval: Interval = shared_memory()

    judged_area_count: int = entity_memory()
    judge_queue: ActiveSlideJudgeQueue = entity_memory()
    path_hidden_count: int = entity_memory()

    @property
    def slide_time(self):
        """The "start" time of the slide. Star faded-in and begins traversing the track."""
        return beat_to_time(self.beat + self.wait_duration)

    @property
    def end_time(self):
        """The "arrive" time of the slide. Star finished traversing the track."""
        return beat_to_time(self.beat + self.wait_duration + self.slide_duration)

    def hide_path(self, value: int):
        self.path_hidden_count = max(self.path_hidden_count, value)

    def spawn_order(self) -> float:
        return self.start_time

    def should_spawn(self) -> bool:
        return time() >= self.start_time

    def preprocess(self):
        self.kind = cast(SlideKind, self.key)
        self.target_time = beat_to_time(self.beat)
        
        self.start_time = self.target_time - get_slide_appear_duration(self.speed)

        good_window = self.judgment_window.good
        self.input_interval = good_window + self.judgment_time + input_offset()
        self.unadjusted_input_interval = good_window + self.judgment_time

    def initialize(self):
        # initalize the judge queue
        advance_slide_judge_queue(
            self.judge_queue,
            self.judged_area_count,
            0,
            self.track,
            self.start_button,
            self.is_mirrored,
        )

    def update_sequential(self):
        if self.despawn:
            return

    def update_parallel(self):
        if self.despawn:
            return
        if not self.is_scored and time() >= self.end_time:
            self.despawn = True
            return
        if time() > self.input_interval.end:
            self.handle_miss()
            return
        if self.is_scored and time() in self.input_interval and not self.judge_queues_finished:
            self.judge_queue_check()
        if self.judge_queues_finished:
            self.handle_finished()
            return

        draw_slide(
            self.kind,
            self.track,
            self.start_button,
            self.is_mirrored,
            self.path_hidden_count,
            self.start_time,
            self.target_time,
            self.slide_time,
            self.end_time,
        )

    @property
    def judgment_time(self) -> float:
        """Expected timing of the final judgment area for this slide."""
        travel_duration = self.end_time - self.slide_time
        remaining_duration = travel_duration * SLIDE_JUDGMENT_CONST[self.track]
        return self.end_time - remaining_duration

    @property
    def judgment_window(self) -> buckets.ArcadeWindow:
        travel_duration = self.end_time - self.slide_time
        remaining_duration = travel_duration * SLIDE_JUDGMENT_CONST[self.track]
        extension = min(remaining_duration / 4, 22 / 60)
        third_perfect = 14 / 60 + extension
        first_perfect = third_perfect / 3
        second_perfect = third_perfect * 2 / 3

        good_start = self.target_time - 0.05 - self.judgment_time
        good_end = self.end_time + 36 / 60 - self.judgment_time

        return buckets.ArcadeWindow(
            critical_perfect=Interval(-first_perfect, first_perfect),
            high_perfect=Interval(-second_perfect, second_perfect),
            low_perfect=Interval(-third_perfect, third_perfect),
            critical_great=Interval(-21 / 60, 21 / 60),
            high_great=Interval(-25 / 60, 25 / 60),
            low_great=Interval(-29 / 60, 29 / 60),
            good=Interval(good_start, good_end),
        )

    def handle_finished(self):
        if self.despawn or not self.is_scored:
            return
        self.judge(time())

    def judge(self, actual_time: float):
        if self.despawn:
            return

        judgment = self.judgment_window.judge(actual_time, self.judgment_time)
        error = self.judgment_window.good.clamp(actual_time - self.judgment_time)
        self.result.judgment = buckets.arcade_judgement_to_normal(judgment)
        self.result.accuracy = error
        if self.result.bucket.id != -1:
            self.result.bucket_value = error * buckets.WINDOW_SCALE
        self.despawn = True


    @property
    def judge_queues_finished(self) -> bool:
        return len(self.judge_queue) == 0

    @property
    def queue_remaining(self) -> int:
        return len(self.judge_queue)

    def judge_queue_check(self):
        self.judged_area_count, path_count = check_slide_judge_queue(
            self.judge_queue,
            self.judged_area_count,
            self.track,
            self.start_button,
            self.is_mirrored,
        )
        self.hide_path(path_count)

    def handle_miss(self):
        if self.queue_remaining == 1:
            self.result.judgment = Judgment.GOOD
            self.result.accuracy = self.judgment_window.good.end
            if self.result.bucket.id != -1:
                self.result.bucket_value = self.result.accuracy * buckets.WINDOW_SCALE
        else:
            self.result.judgment = Judgment.MISS
            self.result.accuracy = 0
            self.result.bucket = Bucket(-1)
        self.despawn = True


class BaseWifiSlide(BaseSlide):
    judged_L_area_count: int = entity_memory()
    judge_queue_L: ActiveSlideJudgeQueue = entity_memory()

    judged_R_area_count: int = entity_memory()
    judge_queue_R: ActiveSlideJudgeQueue = entity_memory()

    def initialize(self):
        # FAN is the overall rendered track. Each internal FAN_* track provides
        # an independent sensor/judgment-area sequence.
        advance_slide_judge_queue(
            self.judge_queue,
            self.judged_area_count,
            0,
            SlideTrackKind.FAN_C,
            self.start_button,
            self.is_mirrored,
        )
        advance_slide_judge_queue(
            self.judge_queue_L,
            self.judged_L_area_count,
            0,
            SlideTrackKind.FAN_L,
            self.start_button,
            self.is_mirrored,
        )
        advance_slide_judge_queue(
            self.judge_queue_R,
            self.judged_R_area_count,
            0,
            SlideTrackKind.FAN_R,
            self.start_button,
            self.is_mirrored,
        )

    def judge_queue_check(self):
        # Progress each branch independently; the rendered Wi-Fi path is shared,
        # so its hidden-point count is derived from the slowest remaining queue.

        self.judged_L_area_count, path_count_L = check_slide_judge_queue(
            self.judge_queue_L,
            self.judged_L_area_count,
            SlideTrackKind.FAN_L,
            self.start_button,
            self.is_mirrored,
        )
        self.judged_area_count, path_count_C = check_slide_judge_queue(
            self.judge_queue,
            self.judged_area_count,
            SlideTrackKind.FAN_C,
            self.start_button,
            self.is_mirrored,
        )
        self.judged_R_area_count, path_count_R = check_slide_judge_queue(
            self.judge_queue_R,
            self.judged_R_area_count,
            SlideTrackKind.FAN_R,
            self.start_button,
            self.is_mirrored,
        )

        if self.judge_queues_finished:
            self.hide_path(9)
        elif len(self.judge_queue) == 0 and len(self.judge_queue_L) <= 1 and len(self.judge_queue_R) <= 1:
            self.hide_path(9)
        else:
            self.hide_path(min(path_count_C, path_count_L, path_count_R))

    @property
    def judge_queues_finished(self) -> bool:
        for queue in (self.judge_queue, self.judge_queue_L, self.judge_queue_R):
            if len(queue) != 0:
                return False
        return True

    @property
    def queue_remaining(self) -> int:
        remaining = 0
        for queue in (self.judge_queue, self.judge_queue_L, self.judge_queue_R):
            remaining = max(remaining, len(queue))
        return remaining


NormalSlideNote = BaseSlide.derive(archetype_names.NORMAL_SLIDE_NOTE, is_scored=True, key=SlideKind.NORMAL_SLIDE)
BreakSlideNote = BaseSlide.derive(archetype_names.BREAK_SLIDE_NOTE, is_scored=True, key=SlideKind.BREAK_SLIDE)
EachSlideNote = BaseSlide.derive(archetype_names.EACH_SLIDE_NOTE, is_scored=True, key=SlideKind.EACH_SLIDE)
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
)