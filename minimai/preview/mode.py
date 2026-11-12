from sonolus.script.engine import PreviewMode

from minimai.lib.skin import BaseSkin
from minimai.preview.bpm_change import PreviewBpmChange
from minimai.preview.each_line import PreviewEachLine
from minimai.preview.hold import PREVIEW_HOLD_ARCHETYPES
from minimai.preview.initialization import PreviewInitialization
from minimai.preview.note import PREVIEW_NOTE_ARCHETYPES
from minimai.preview.slide import PREVIEW_SLIDE_ARCHETYPES
from minimai.preview.touch import PREVIEW_TOUCH_ARCHETYPES
from minimai.preview.touch_hold import PREVIEW_TOUCH_HOLD_ARCHETYPES

preview_mode = PreviewMode(
    archetypes=[
        PreviewInitialization,
        PreviewBpmChange,
        *PREVIEW_NOTE_ARCHETYPES,
        *PREVIEW_HOLD_ARCHETYPES,
        *PREVIEW_TOUCH_ARCHETYPES,
        *PREVIEW_TOUCH_HOLD_ARCHETYPES,
        *PREVIEW_SLIDE_ARCHETYPES,
        PreviewEachLine,
    ],
    skin=BaseSkin,
)
