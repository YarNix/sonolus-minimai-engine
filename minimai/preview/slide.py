from __future__ import annotations

from typing import cast

from sonolus.script.archetype import EntityRef, PreviewArchetype, StandardImport, entity_data, imported
from sonolus.script.timing import beat_to_time

from minimai.lib import archetype_names
from minimai.lib.game import Button
from minimai.lib.slide import SlideKind, SlideTrackKind, get_chain_start_beat, get_path_total_beats
from minimai.preview.layout import report_end_time, report_judgment_beat
from minimai.preview.note import PreviewBaseNote


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

    def preprocess(self):
        self.kind = cast(SlideKind, self.key)
        self.target_time = beat_to_time(self.beat)
        end_beat = get_chain_start_beat(self.index) + get_path_total_beats(self.index)
        report_end_time(beat_to_time(end_beat))
        report_judgment_beat(end_beat)


class PreviewBaseWifiSlide(PreviewBaseSlide):
    pass


class PreviewConnSlide(PreviewBaseSlide):
    """A head or middle part of a connection chain; the final slides after it report the chain's end."""

    name = archetype_names.CONN_SLIDE_NOTE
    next_slide_ref: EntityRef[PreviewBaseSlide] = imported(name="nextSlide")

    def preprocess(self):
        self.target_time = beat_to_time(self.beat)


class PreviewConnWifiSlide(PreviewBaseWifiSlide):
    name = archetype_names.CONN_WIFI_SLIDE_NOTE
    next_slide_ref: EntityRef[PreviewBaseSlide] = imported(name="nextSlide")
    next_slide_l_ref: EntityRef[PreviewBaseSlide] = imported(name="nextSlideL")
    next_slide_r_ref: EntityRef[PreviewBaseSlide] = imported(name="nextSlideR")

    def preprocess(self):
        self.target_time = beat_to_time(self.beat)


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
