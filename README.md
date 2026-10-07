# wireless-face-tracking

A camera finds and locks onto one enrolled person, works out how far they are from the centre of the picture, and sends that
over MQTT to an ESP8266. The ESP8266 turns a 28BYJ-48 stepper motor that carries a clock-style pointer:

```text
12 = person centred   ·   1…6 = right of centre   ·   11…6 = left of centre   (6 = furthest)
```

The farther the person is from the centre, the farther the pointer moves from 12. It works on either axis.

| Mode | Person moves | Pointer shows |
|------|--------------|---------------|
| `--x` (default) | left of centre / right of centre | 11…6 / 1…6 |
| `--y` | above centre / below centre | 11…6 / 1…6 |

## How it fits together

```text
Camera → detect → recognise → lock → offset → hour ──MQTT──▶ Mosquitto ──MQTT──▶ ESP8266 → 28BYJ-48 pointer
        └──────────────── Python (this PC) ────────────────┘   (broker)            └──── firmware ────┘
```

Python and the board only talk through MQTT, so the three parts can run on different machines. Python never drives the motor,
and the firmware knows nothing about faces. Details: [docs/architecture.md](docs/architecture.md).

## Layout

| Path | What it is |
|------|------------|
| `src/` | Python: camera, detection, recognition, tracker, axis mapping, MQTT publisher, preview (`main.py` is the entry point) |
| `firmware/stepper_tracker/` | The ESP8266 sketch |
| `connection.json` | **The one place for Wi-Fi, broker and topics** (gitignored; copy `connection.example.json`) |
| `scripts/` | `flash.sh` (apply settings and flash), `sync_firmware.py`, `motor_test.sh` |
| `docs/` | Full documentation, start at [docs/README.md](docs/README.md) |

## Quick start

You need Mosquitto, [uv](https://docs.astral.sh/uv/), `arduino-cli`, an ESP8266 board with a ULN2003 + 28BYJ-48, and a USB camera.

```bash
# 1. Broker that the board can reach over Wi-Fi (one-off)
echo -e "listener 1883 0.0.0.0\nallow_anonymous true" | sudo tee /etc/mosquitto/conf.d/lan.conf
sudo systemctl restart mosquitto

# 2. Settings: copy the template and set wifi.ssid / wifi.password (2.4 GHz network, same one as this PC)
cp connection.example.json connection.json

# 3. Python
uv sync
uv run python -m src.enroll                 # enrol yourself with the camera you will track with

# 4. Firmware (also installs the ESP8266 core and PubSubClient the first time, see docs/setup.md)
scripts/flash.sh                            # turns connection.json into the firmware header, compiles, flashes

# 5. Track
uv run python -m src.main --target NAME             # horizontal
uv run python -m src.main --target NAME --y         # vertical
```

Preview keys: `f` fullscreen, `m` small window, `q` quit. Other flags: `--fullscreen`, `--no-preview`, `--debug`, `--camera N`.
The pointer goes back to 12 when tracking starts, when you quit, and 3 s after the face is lost.

`models/` needs two model files that are too large for git: `embedder_arcface.onnx` (ArcFace, e.g. InsightFace `w600k_r50`) and
`face_landmarker.task` (MediaPipe FaceLandmarker). Put them in `models/`.

## One source of truth for the network

Edit **only `connection.json`**. Python reads it directly; `scripts/flash.sh` regenerates the firmware's `connection.h` from it before every
build (never edit that file). With `"broker.host": "auto"`, Python uses localhost and the board is given this PC's current network IP, so a changed IP
only needs a re-flash. See [docs/configuration.md](docs/configuration.md).

## Wiring

| ULN2003 | ESP8266 |
|---------|---------|
| IN1 / IN2 / IN3 / IN4 | D1 / D2 / D3 / D4 |
| − | GND |
| + | 5 V (power the driver from its own 5 V supply, grounds joined) |

## When it does not move

| Symptom | Likely cause |
|---------|--------------|
| Motor never moves, status not `online` | The board is not on the broker: same Wi-Fi as the PC? `scripts/flash.sh` after changing `connection.json`; `MQTT failed rc=-2` in the board's serial log means the broker is unreachable |
| Board keeps disconnecting from USB / `Wi-Fi: network not found` | Weak 5 V supply: power the driver separately, use a short good cable |
| Only vibrates | Step rate too fast or a weak supply: `mosquitto_pub -t tracker/x/command -m '{"step_us":4000}'` |
| Cannot reverse | Coil order: run `scripts/motor_test.sh`, then `{"coils":N}` |
| Pointer goes the wrong way | `MOTOR_DIRECTION` in the sketch |
| Tracker prints `locked:false` forever | No face seen: whole face in frame, right camera (not the built-in one; a busy camera is reported in the log), enrolled with the same camera |
| Pointer was left off 12 | Calibrate once with `{"jog":N}` then `{"zero":true}`: the position is then remembered in flash |

More in [docs/firmware.md](docs/firmware.md) and [docs/setup.md](docs/setup.md).

## Privacy

`data/` (the face database and enrolment photos) is biometric data and is gitignored. `connection.json` and the generated header hold your Wi-Fi password and are gitignored too.
