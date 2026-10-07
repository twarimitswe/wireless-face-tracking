"""Which direction of the image drives the pointer.

x (default): horizontal. Face left of center -> 11..6, right of center -> 1..6.
y: vertical. Face above center -> 11..6 (left side of the dial), below center -> 1..6 (right side).
Both give a normalized offset in [-1, +1] where positive = right-hand hours.
"""


def offset(signal, axis: str) -> float:
    """Normalized offset of the tracked face along the chosen axis (image y grows downward, so down = +error_y = right-hand hours)."""
    return signal.error_x if axis == "x" else signal.error_y
