from sonolus.script.interval import unlerp
from sonolus.script.runtime import time

from minimai.lib.game import Button
from minimai.lib.layer import LAYER_NOTE_LINE, get_z
from minimai.lib.layout import get_line_alpha, layout_each_line
from minimai.lib.skin import ActiveSkin


def draw_each_line(
    start_button: Button,
    steps: int,
    start_time: float,
    target_time: float,
    stops_at_ring: bool,
):
    """The arc joining two notes hit together, ``steps`` buttons (1..4) clockwise from
    ``start_button``, at the notes' distance."""
    progress = unlerp(start_time, target_time, time())
    if progress < 0:
        return
    if stops_at_ring:
        progress = min(progress, 1)
    layout = layout_each_line(progress, start_button)
    # Below the tap lines of the same time.
    ActiveSkin.each_ring_line[steps - 1].draw(layout, get_z(LAYER_NOTE_LINE, target_time, -1).tuple, get_line_alpha(progress))
