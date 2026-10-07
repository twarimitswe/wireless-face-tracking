"""
Lock onto one enrolled person and publish pointer commands over MQTT (x: left/right, y: up/down).
Never touches the motor: the ESP8266 subscribes to the command topic.

Run (from the project root):
 python -m src.main --target "SomeEnrolledName"          # horizontal tracking (default, same as --x)
 python -m src.main --target "SomeEnrolledName" --y      # vertical tracking

Keys:
 f : fullscreen on/off      m : small/normal window      q : quit
"""

import argparse
import logging
import time

import cv2

from .camera import open_camera, pick_camera_index
from .config import (
    CAMERA_RESOLUTION, DEAD_ZONE, EMBEDDER_MODEL, FACE_DB, MATCH_THRESHOLD, MIN_FACE_SIZE, MIRROR_CAMERA,
    PROCESS_WIDTH, PUBLISH_INTERVAL_S, TRACK_SMOOTHING, VERIFY_EVERY,
)
from .axis import offset
from .movement import to_command
from .overlay import draw_face, draw_zones, text_scale
from .preview import Preview
from .publisher import CommandPublisher
from .recognize import ArcFaceEmbedderONNX, FaceDBMatcher, HaarFaceMesh5pt, load_db_npz
from .tracker import LockedFaceTracker


def draw_label(frame, text, color):
    k = text_scale(frame)
    cv2.putText(frame, text, (int(12 * k), int(52 * k)), cv2.FONT_HERSHEY_SIMPLEX, 0.7 * k, (0, 0, 0), round(4 * k), cv2.LINE_AA)
    cv2.putText(frame, text, (int(12 * k), int(52 * k)), cv2.FONT_HERSHEY_SIMPLEX, 0.7 * k, color, round(2 * k), cv2.LINE_AA)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", required=True, help="enrolled identity to lock")
    parser.add_argument("--camera", type=int, default=None, help="cv2 camera index (auto-detected when omitted)")
    parser.add_argument("--debug", action="store_true", help="log every candidate face and its match score")
    axis_flag = parser.add_mutually_exclusive_group()
    axis_flag.add_argument("--x", dest="axis", action="store_const", const="x", help="horizontal tracking (default)")
    axis_flag.add_argument("--y", dest="axis", action="store_const", const="y",
                           help="vertical tracking: up = left-hand hours (11..6), down = right-hand hours (1..6)")
    parser.set_defaults(axis="x")
    parser.add_argument("--fullscreen", action="store_true", help="start the preview fullscreen (toggle with f)")
    parser.add_argument("--no-preview", action="store_true", help="run headless")
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s", datefmt="%H:%M:%S")

    tracker = LockedFaceTracker(
        args.target,
        HaarFaceMesh5pt(min_size=MIN_FACE_SIZE, debug=False),
        ArcFaceEmbedderONNX(model_path=str(EMBEDDER_MODEL), input_size=(112, 112), debug=False),
        FaceDBMatcher(load_db_npz(FACE_DB), dist_thresh=MATCH_THRESHOLD),
        dead_zone=DEAD_ZONE,
        ema_alpha=TRACK_SMOOTHING,
        verify_every=VERIFY_EVERY,
    )
    cap = open_camera(args.camera if args.camera is not None else pick_camera_index(), CAMERA_RESOLUTION)
    if not cap.isOpened():
        raise RuntimeError("Camera not available.")
    publisher = CommandPublisher(args.axis)
    preview = None if args.no_preview else Preview(args.fullscreen)
    publisher.home()  # always start tracking from the center (12:00)
    last_sent = 0.0

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if MIRROR_CAMERA:
                frame = cv2.flip(frame, 1)
            # detect on a smaller copy for speed; offsets are ratios, so they hold for the full frame
            height, width = frame.shape[:2]
            small = frame if width <= PROCESS_WIDTH else cv2.resize(frame, (PROCESS_WIDTH, height * PROCESS_WIDTH // width))
            scale = width / small.shape[1]
            face, signal = tracker.update(small)
            command, dial = to_command(offset(signal, args.axis) if signal else 0.0)

            now = time.monotonic()
            if now - last_sent >= PUBLISH_INTERVAL_S:
                publisher.send(command, locked=face is not None)
                last_sent = now

            if preview:
                draw_zones(frame, dial, args.axis)
                if face is not None:
                    x1, y1, x2, y2 = (int(v * scale) for v in tracker.box(face))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 170, 0), max(2, round(2 * text_scale(frame))))
                    draw_face(frame, tracker.smooth_center * scale, dial, args.axis)
                draw_label(frame, f"{tracker.state.name} [{args.axis}] pointer={dial}",
                           (0, 180, 0) if face is not None else (0, 140, 255))
                if not preview.show(frame):
                    break
    finally:
        publisher.home()
        publisher.close()
        cap.release()
        if preview:
            preview.close()


if __name__ == "__main__":
    main()
