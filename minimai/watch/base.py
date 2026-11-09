from sonolus.script.archetype import WatchArchetype, entity_data, imported

from minimai.lib.game import Button


class WatchButtonBase(WatchArchetype):
    """Taps, stars and holds: what an each line needs from its notes."""
    button: Button = imported(default=1)
    firework: bool = imported(default=False)

    target_time: float = entity_data()
    # When the note appears (each lines appear with it).
    start_time: float = entity_data()
    # Holds stop at the ring; taps and stars keep going when late.
    is_hold: bool = entity_data()
    # When the note despawns.
    exit_time: float = entity_data()
