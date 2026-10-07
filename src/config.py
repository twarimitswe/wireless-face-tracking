"""Single source of truth for the pipeline.

Connection settings live in connection.json; the firmware gets them via scripts/sync_firmware.py.
Dial semantics must match firmware/stepper_tracker/stepper_tracker.ino.
"""

from .connection import ROOT, SETTINGS, broker_host_for_pc

# ---- Models / data ----
EMBEDDER_MODEL = ROOT / "models" / "embedder_arcface.onnx"
FACE_DB = ROOT / "data" / "db" / "face_db.npz"
MATCH_THRESHOLD = 0.34
MIN_FACE_SIZE = (70, 70)
CAMERA_RESOLUTION = (1280, 720)  # requested from the camera (MJPG); the real size is read back, nothing assumes it
PROCESS_WIDTH = 640  # detection runs on a copy at most this wide (speed); drawing uses the full frame
MIRROR_CAMERA = True  # flip frames left-right (like a mirror) before detection, enrollment and drawing

# ---- Tracking ----
TRACK_SMOOTHING = 0.5  # EMA weight of the newest face position (higher = less lag, more jitter)
VERIFY_EVERY = 30  # frames between ArcFace re-checks of the locked face (each one can drop the lock)

# ---- MQTT (edit connection.json, not this file) ----
BROKER_HOST = broker_host_for_pc()
BROKER_PORT = SETTINGS["broker"]["port"]
BROKER_USERNAME = SETTINGS["broker"]["username"]
BROKER_PASSWORD = SETTINGS["broker"]["password"]
TOPICS = SETTINGS["topics"]  # {"x": {"command", "status"}, "y": {...}}; the --x / --y flag picks one
PUBLISH_INTERVAL_S = 0.2  # seconds between commands

# ---- Mapping: normalized offset -> dial position (same for both axes) ----
DEAD_ZONE = 0.05  # fraction of half the frame (width for x, height for y) treated as centered
FULL_SPEED_AT = 0.8  # offset (fraction of the half-frame) already shown as 6 o'clock
DIAL_CENTER = 12  # centered; left counts down 11..6, right counts up 1..6
LEVELS = 6  # steps between the dial center and the maximum position (6)
