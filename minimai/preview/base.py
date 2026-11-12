from sonolus.script.archetype import PreviewArchetype, StandardImport, entity_data, imported

from minimai.lib.game import Button


class PreviewButtonBase(PreviewArchetype):
    """Taps, stars and holds: what an each line reads from its notes."""
    button: Button = imported(default=1)
    firework: bool = imported(default=False)
    beat: StandardImport.BEAT

    target_time: float = entity_data()
