from sonolus.script import runtime
from sonolus.script.record import Record

LAYER_RING = 0
LAYER_DEBUG_LOW = 2
LAYER_NOTE_LINE = 8
LAYER_EX = 9
LAYER_NOTE = 10
LAYER_TOUCH = 11

class ZIndexes(Record):
    z1: float
    z2: float
    z3: float
    z4: float

    @property
    def tuple(self) -> "tuple[float, float, float, float]":
        return self.z1, self.z2, self.z3, self.z4

def get_z(layer: int, time: float = 0.0, etc: int = 0, *, invert_time: bool = False, ):
    return ZIndexes(
        z1=layer,
        z2=time - runtime.time() if invert_time else runtime.time() - time,
        z3=0.0,
        z4=etc,
    )
