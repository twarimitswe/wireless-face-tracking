# MQTT

## Topics (configurable in `connection.json`, one pair per axis)

| Purpose | Default topic | Direction |
|---------|---------------|-----------|
| X (horizontal) command | `tracker/x/command` | Python `--x` → ESP8266 |
| X status | `tracker/x/status` | ESP8266 → anyone |
| Y (vertical) command | `tracker/y/command` | Python `--y` → ESP8266 |
| Y status | `tracker/y/status` | ESP8266 → anyone |

Each axis has its own topics, so the two modes never mix. `axis` in `connection.json` selects which topics the firmware subscribes to: `"x"`, `"y"`, or `"xy"` (default) for one pointer
that follows whichever mode the tracker runs. Use `"x"` / `"y"` for two separate boards.

## Command payload (JSON, compact – no spaces, the firmware parses it as text)

```json
{"normalized":-0.5,"locked":true}
```

| Field | Meaning |
|-------|---------|
| `normalized` | The hour to show: 0 = 12 o'clock, ±1/6 … ±1 = 1…6 (right) or 11…6 (left) |
| `locked` | `false` when the target is lost; the firmware ignores the command and holds still |

Other commands: `{"home":true}` (pointer to 12; sent by the tracker on start and exit), and for calibration `{"jog":N}` (turn N steps) and `{"zero":true}` (this position is 12). See movement-mapping.md.

Only normalized data crosses MQTT – no pixels, dial positions, steps or degrees. The firmware does no mapping; it only converts the value to steps.
The dead zone and the hour are applied in Python, so `normalized` is one of 0, ±1/6 … ±1 (see movement-mapping.md).

## Delivery

- QoS 0 is enough: commands are sent continuously, a lost one is replaced by the next.
- Do **not** retain commands – a reconnecting ESP8266 must not replay an old movement.
- Python publishes at a fixed interval (`publish_interval_s`, 0.2 s), including `normalized: 0` when centred. The pointer is absolute, so repeated messages just repeat the same target.
- The firmware sets a retained Last Will on the status topic (`online` / `offline`).

## Broker

Mosquitto listens on port 1883 by default. To accept the ESP8266 from the network, the listener must not be bound to localhost only:

```text
listener 1883
allow_anonymous true      # development only; use a password file in production
```

Broker host and port are configuration in both the Python app and the firmware.
