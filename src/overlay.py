import cv2

from .config import DIAL_CENTER, LEVELS
from .movement import level_edges

GRAY, GREEN, YELLOW = (110, 110, 110), (0, 200, 0), (0, 255, 255)


def text_scale(frame) -> float:
    """Drawing size factor: 1.0 at 480 px tall, so lines and numbers look the same at any resolution."""
    return frame.shape[0] / 480


def _text(frame, text, xy, color, size=0.5):
    scale = size * text_scale(frame)
    thick = max(1, round(scale * 2))
    cv2.putText(frame, text, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), thick + 2, cv2.LINE_AA)
    cv2.putText(frame, text, xy, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thick, cv2.LINE_AA)


def draw_zones(frame, active_dial, axis="x"):
    """Center line, dead zone and the dial zones with the active one highlighted.

    x: vertical lines, hours 11..6 on the left and 1..6 on the right, labels on top.
    y: horizontal lines, hours 11..6 above the center and 1..6 below it, labels on the left.
    """
    h, w = frame.shape[:2]
    cx, cy = w // 2, h // 2
    half = cx if axis == "x" else cy
    k = text_scale(frame)
    thick = max(1, round(k))

    def line(pos, color):  # pos: pixels from the center, right (x) or down (y) positive
        if axis == "x":
            cv2.line(frame, (cx + pos, 0), (cx + pos, h), color, thick)
        else:
            cv2.line(frame, (0, cy + pos), (w, cy + pos), color, thick)

    def label(text, pos, color):
        _text(frame, text, (cx + pos - int(8 * k), int(18 * k)) if axis == "x" else (int(8 * k), cy + pos + int(5 * k)), color)

    edges = level_edges()
    line(0, GREEN)
    for side in (-1, 1):
        for i, edge in enumerate(edges):
            line(int(side * edge * half), GREEN if i == 0 else GRAY)
        for level in range(1, LEVELS + 1):
            dial = DIAL_CENTER - level if side < 0 else level
            label(str(dial), int(side * (edges[level - 1] + edges[level]) / 2 * half), YELLOW if dial == active_dial else GRAY)
    label(str(DIAL_CENTER), 0, YELLOW if active_dial == DIAL_CENTER else GREEN)


def draw_face(frame, center, dial, axis="x"):
    """Marker on the face center and a line from the frame center showing the offset along the axis."""
    h, w = frame.shape[:2]
    fx, fy = int(center[0]), int(center[1])
    k = text_scale(frame)
    if axis == "x":
        cv2.line(frame, (w // 2, fy), (fx, fy), YELLOW, max(2, round(2 * k)))
        offset_px = fx - w // 2
    else:
        cv2.line(frame, (fx, h // 2), (fx, fy), YELLOW, max(2, round(2 * k)))
        offset_px = fy - h // 2  # down is positive, like right in x
    cv2.circle(frame, (fx, fy), round(7 * k), YELLOW, -1)
    _text(frame, f"{offset_px:+d}px -> {dial}", (min(fx + int(10 * k), w - int(150 * k)), max(fy - int(12 * k), int(36 * k))), YELLOW)
