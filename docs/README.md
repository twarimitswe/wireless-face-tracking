# Wireless Face Tracking – Documentation

A face recognition and tracking system. A camera finds and locks onto a known person, works out how far that
person is from the frame centre, and publishes a normalized movement command over MQTT. An ESP8266 receives the
command and turns a 28BYJ-48 stepper motor so the camera keeps the person centred (X-axis only).

## Documents

| File | Contents |
|------|----------|
| [architecture.md](architecture.md) | The three environments, data flow, separation of concerns |
| [coordinate-mapping.md](coordinate-mapping.md) | Pixels → offset → normalized value, with worked examples |
| [movement-mapping.md](movement-mapping.md) | **The 12 → 11…6 / 1…6 dial:** how distance from centre selects the position |
| [mqtt.md](mqtt.md) | Topics, message format, QoS, broker setup |
| [python-vision.md](python-vision.md) | Environment 1: modules and responsibilities |
| [firmware.md](firmware.md) | Environment 3: ESP8266 + 28BYJ-48, steps and degrees |
| [configuration.md](configuration.md) | Every configurable value, in one place |
| [setup.md](setup.md) | Step-by-step commands: Mosquitto, Paho, running, flashing |
| [deployment.md](deployment.md) | Single-PC setup and moving to separate machines |

## Rules the design follows

- **KISS / DRY** – one source of truth for every constant and every conversion.
- **Separation of concerns** – vision never touches the motor; MQTT code knows nothing about faces; the firmware knows nothing about faces.
- **Only MQTT connects the environments** – so each can move to another machine by changing the broker address.
- **No unit mixing** – pixels, normalized values, dial positions, degrees and steps are converted explicitly, one stage at a time.

## Status

Implemented in this project (Python in `src/`, firmware in `firmware/stepper_tracker/`).
The Python side and MQTT publishing were tested against the local broker. The firmware compiles for `esp8266:esp8266:nodemcuv2` (not yet flashed or run on hardware), and the
tuning values (`DEGREES_PER_LEVEL`, `LIMIT_DEGREES`, dead zone) are starting points.
