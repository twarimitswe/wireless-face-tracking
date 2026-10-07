# Environment 1 – Python Computer Vision

Location: `src/` in this project (a self-contained copy of the detection/recognition code plus the new MQTT modules).

```text
config.py         all constants (models, broker, topic, publish interval, dead zone, dial levels)
camera.py         camera auto-detection (prefers a plugged-in USB camera)
haar_5pt.py       face detection + 5 landmark points
recognize.py      ArcFace embedding + database matching
tracker.py        LockedFaceTracker: identity lock + coordinate mapping (error_x = (cx − W/2) / (W/2))
movement.py       raw offset → dead-zoned, hour command (+ dial label 12 / 11…6 / 1…6 for display)
publisher.py      Paho MQTT client – the only module that imports paho
axis.py           x or y: which image offset drives the pointer (`--x` default, `--y`)
overlay.py        zone lines 11…6 / 12 / 1…6 (vertical lines for x, horizontal for y), dead zone, face marker
preview.py        the preview window: f fullscreen, m small/normal, q quit
main.py           entry point: camera → tracker → movement → publisher
```

`models/` are symlinks to the model files of the older `face-recognition` project; `data/db/` is a copy of its face database. Enroll with `uv run python -m src.enroll` (uses the external camera).

## Run

```text
uv run python -m src.main --target "SomeEnrolledName"          # horizontal (--x, default)
uv run python -m src.main --target "SomeEnrolledName" --y      # vertical
# extras: --fullscreen, --no-preview (headless), --debug, --camera N
```

## Loop

```text
face, signal = tracker.update(frame)            # locked person or (None, None)
command, dial = to_command(signal.error_x if signal else 0)
every PUBLISH_INTERVAL_S: publisher.send(command, locked=face is not None)
```

## Start and stop

On start and on exit `main.py` publishes `{"home":true}`, so tracking always begins at 12. 12 is the motor's power-up position (or the last `zero`), see calibration in movement-mapping.md.

## Losing the face

When the face disappears `main.py` publishes `locked:false`; the firmware returns the pointer to 12 after 3 s.

## Rules

- Explicit imports only, no `from x import *`.
- Frame width/height always come from the frame itself, never from constants.
- `movement.py` is a pure function and easy to unit-test.
- Nothing here imports anything about the ESP8266 or the motor.
- The publisher reconnects on its own if the broker is down or restarts.

## Preview window

The camera is opened at `CAMERA_RESOLUTION` (HD by default) and detection runs on a smaller copy (`PROCESS_WIDTH`), so the preview is sharp while tracking stays fast. The window keeps the image's aspect ratio at any size (no stretching), and the lines and numbers scale with the frame height.

`f` toggles fullscreen (or start with `--fullscreen`), `m` toggles a small window, `q` quits. Minimizing uses your window manager's own
button; the tracking loop and MQTT keep running whether the window is visible or not. `--no-preview` runs without any window.
