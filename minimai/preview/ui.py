from math import degrees

from sonolus.script.runtime import runtime_ui
from sonolus.script.vec import Vec2

from minimai.preview.layout import MENU_SIZE, PROGRESS_H, PreviewLayout, to_screen


def init_preview_ui():
    """Menu at the top right, progress bar along the bottom; laid out in the view."""
    ui = runtime_ui()
    box = PreviewLayout.ui_box
    rotation = degrees(PreviewLayout.view_angle)
    ui.menu.update(
        anchor=to_screen(box.tr),
        pivot=Vec2(1, 1),
        rotation=rotation,
        dimensions=Vec2(MENU_SIZE, MENU_SIZE) * ui.menu_config.scale,
        alpha=ui.menu_config.alpha,
        background=True,
    )
    ui.progress.update(
        anchor=to_screen(box.bl),
        pivot=Vec2(0, 0),
        rotation=rotation,
        dimensions=Vec2(box.w, PROGRESS_H * ui.progress_config.scale),
        alpha=ui.progress_config.alpha,
        background=True,
    )
