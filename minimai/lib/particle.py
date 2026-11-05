from sonolus.script.globals import level_data
from sonolus.script.particle import Particle, ParticleHandle, StandardParticle, particle, particles
from sonolus.script.quad import Quad
from sonolus.script.record import Record

from minimai.lib.game import ArcadeJudgment
from minimai.lib.options import Options


@particles
class BaseParticles:
    tap_perfect: Particle = particle("Mai Tap Perfect")
    tap_great: Particle = particle("Mai Tap Great")
    tap_good: Particle = particle("Mai Tap Good")
    break_perfect: Particle = particle("Mai Break Perfect")
    break_great: Particle = particle("Mai Break Great")
    break_good: Particle = particle("Mai Break Good")
    touch_perfect: Particle = particle("Mai Touch Perfect")
    touch_great: Particle = particle("Mai Touch Great")
    touch_good: Particle = particle("Mai Touch Good")
    # Looped while a hold or touch hold is held; by the head's judgment.
    hold_perfect: Particle = particle("Mai Hold Perfect")
    hold_great: Particle = particle("Mai Hold Great")
    hold_good: Particle = particle("Mai Hold Good")
    hold_miss: Particle = particle("Mai Hold Miss")

    # Standard effects, for fallbacks
    circular_tap_yellow: StandardParticle.NOTE_CIRCULAR_TAP_YELLOW
    circular_tap_red: StandardParticle.NOTE_CIRCULAR_TAP_RED
    circular_tap_green: StandardParticle.NOTE_CIRCULAR_TAP_GREEN
    circular_alternative_yellow: StandardParticle.NOTE_CIRCULAR_ALTERNATIVE_YELLOW
    circular_alternative_red: StandardParticle.NOTE_CIRCULAR_ALTERNATIVE_RED
    circular_alternative_green: StandardParticle.NOTE_CIRCULAR_ALTERNATIVE_GREEN
    circular_hold_yellow: StandardParticle.NOTE_CIRCULAR_HOLD_YELLOW
    circular_hold_red: StandardParticle.NOTE_CIRCULAR_HOLD_RED
    circular_hold_green: StandardParticle.NOTE_CIRCULAR_HOLD_GREEN
    circular_hold_neutral: StandardParticle.NOTE_CIRCULAR_HOLD_NEUTRAL


EMPTY_PARTICLE = Particle(-1)

# Effect lengths in seconds, before Effect Animation Speed. The particle pack is built for these.
TAP_PERFECT_DURATION = 0.42
TAP_GREAT_DURATION = 0.35
TAP_GOOD_DURATION = 0.4
TOUCH_DURATION = 0.25
# One loop of the hold glow.
HOLD_DURATION = 0.3


class GradeParticles(Record):
    """An effect per hit grade."""
    perfect: Particle
    great: Particle
    good: Particle

    def get(self, judgment: ArcadeJudgment) -> Particle:
        result = +EMPTY_PARTICLE
        if judgment == ArcadeJudgment.NONE or judgment == ArcadeJudgment.MISS:
            pass
        elif judgment <= ArcadeJudgment.LOW_PERFECT:
            result @= self.perfect
        elif judgment <= ArcadeJudgment.LOW_GREAT:
            result @= self.great
        else:
            result @= self.good
        return result


class HoldParticles(Record):
    perfect: Particle
    great: Particle
    good: Particle
    miss: Particle

    def get(self, judgment: ArcadeJudgment) -> Particle:
        result = +self.miss
        if judgment == ArcadeJudgment.NONE or judgment == ArcadeJudgment.MISS:
            pass
        elif judgment <= ArcadeJudgment.LOW_PERFECT:
            result @= self.perfect
        elif judgment <= ArcadeJudgment.LOW_GREAT:
            result @= self.great
        else:
            result @= self.good
        return result


@level_data
class ActiveParticles:
    tap: GradeParticles
    tap_break: GradeParticles
    touch: GradeParticles
    hold: HoldParticles


def first_available_particle(*args: Particle) -> Particle:
    result = +EMPTY_PARTICLE
    for p in args:
        if p.is_available:
            result @= p
            break
    return result


def init_particles():
    """Picks each effect or its standard fallback once."""
    ActiveParticles.tap = GradeParticles(
        perfect=first_available_particle(BaseParticles.tap_perfect, BaseParticles.circular_tap_yellow),
        great=first_available_particle(BaseParticles.tap_great, BaseParticles.circular_tap_red),
        good=first_available_particle(BaseParticles.tap_good, BaseParticles.circular_tap_green),
    )
    ActiveParticles.tap_break = GradeParticles(
        perfect=first_available_particle(BaseParticles.break_perfect, BaseParticles.circular_alternative_yellow),
        great=first_available_particle(BaseParticles.break_great, BaseParticles.circular_alternative_red),
        good=first_available_particle(BaseParticles.break_good, BaseParticles.circular_alternative_green),
    )
    ActiveParticles.touch = GradeParticles(
        perfect=first_available_particle(BaseParticles.touch_perfect, BaseParticles.circular_tap_yellow),
        great=first_available_particle(BaseParticles.touch_great, BaseParticles.circular_tap_red),
        good=first_available_particle(BaseParticles.touch_good, BaseParticles.circular_tap_green),
    )
    ActiveParticles.hold = HoldParticles(
        perfect=first_available_particle(BaseParticles.hold_perfect, BaseParticles.circular_hold_yellow),
        great=first_available_particle(BaseParticles.hold_great, BaseParticles.circular_hold_red),
        good=first_available_particle(BaseParticles.hold_good, BaseParticles.circular_hold_green),
        miss=first_available_particle(BaseParticles.hold_miss, BaseParticles.circular_hold_neutral),
    )


def spawn_effect(effect: Particle, quad: Quad, duration: float):
    if Options.note_effect and effect.is_available:
        effect.spawn(quad, duration / Options.effect_animation_speed)


def spawn_tap_effect(is_break: bool, judgment: ArcadeJudgment, quad: Quad):
    """Taps, stars, hold ends and touch hold ends; nothing on a miss."""
    duration = TAP_GOOD_DURATION
    if is_break or judgment <= ArcadeJudgment.LOW_PERFECT:
        duration = TAP_PERFECT_DURATION
    elif judgment <= ArcadeJudgment.LOW_GREAT:
        duration = TAP_GREAT_DURATION
    if is_break:
        spawn_effect(ActiveParticles.tap_break.get(judgment), quad, duration)
    else:
        spawn_effect(ActiveParticles.tap.get(judgment), quad, duration)


def spawn_touch_effect(judgment: ArcadeJudgment, quad: Quad):
    spawn_effect(ActiveParticles.touch.get(judgment), quad, TOUCH_DURATION)


def update_hold_glow(handle: ParticleHandle, active: bool, judgment: ArcadeJudgment, quad: Quad):
    """Keeps the looped glow running while ``active``, coloured by ``judgment``."""
    if active and Options.note_effect:
        if handle.id == 0:
            effect = ActiveParticles.hold.get(judgment)
            if effect.is_available:
                handle @= effect.spawn(quad, HOLD_DURATION / Options.effect_animation_speed, loop=True)
    else:
        destroy_hold_glow(handle)


def destroy_hold_glow(handle: ParticleHandle):
    if handle.id != 0:
        handle.destroy()
        handle.id = 0
