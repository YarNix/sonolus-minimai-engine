from sonolus.script.globals import level_data
from sonolus.script.particle import Particle, StandardParticle, particle, particles
from sonolus.script.record import Record

@particles
class BaseParticles:
    pass

EMPTY_PARTICLE = Particle(-1)

@level_data
class ActiveParticles:
    pass

def init_particles():
    pass