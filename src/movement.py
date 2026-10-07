import math

from .config import DEAD_ZONE, DIAL_CENTER, FULL_SPEED_AT, LEVELS


def level_edges() -> list[float]:
    """Normalized offsets where the dial changes hour: the dead-zone edge, then one edge per level."""
    return [DEAD_ZONE + k * (FULL_SPEED_AT - DEAD_ZONE) / LEVELS for k in range(LEVELS + 1)]


def to_command(normalized: float) -> tuple[float, int]:
    """Raw offset (-1 left .. +1 right) -> (normalized command, dial hour).

    The pointer shows how far the face is from the center: 12 when centered (inside the dead zone),
    11..6 to the left, 1..6 to the right. The command is level / LEVELS (0, +-1/6 .. +-1), so the
    firmware turns it into exactly that hour. FULL_SPEED_AT is the offset that already means 6.
    """
    n = max(-1.0, min(1.0, normalized))
    magnitude = min(1.0, (abs(n) - DEAD_ZONE) / (FULL_SPEED_AT - DEAD_ZONE))
    if magnitude <= 0:
        return 0.0, DIAL_CENTER
    level = math.ceil(magnitude * LEVELS)
    return math.copysign(level / LEVELS, n), (DIAL_CENTER - level if n < 0 else level)
