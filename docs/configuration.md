# Configuration

## Connection settings: one file, set once

Everything about the network lives in **`connection.json`** (project root; gitignored because it holds passwords – copy
`connection.example.json` to create it). Python and the firmware both take their values from it; nothing is set anywhere else.

| Key | Used by | Meaning |
|-----|---------|---------|
| `wifi.ssid` / `wifi.password` | ESP8266 | The 2.4 GHz Wi-Fi the board joins. Must be the same network as the PC |
| `broker.host` | both | `"auto"` = Mosquitto runs on this PC: Python uses localhost and the board gets this PC's current network IP. Or a fixed IP/hostname (another computer, or a broker on the internet) |
| `broker.port` | both | 1883 |
| `broker.username` / `password` | both | Empty for an open broker; set for an internet broker |
| `axis` | ESP8266 | `"x"`, `"y"` or `"xy"` (default): which tracking mode(s) the board listens to |
| `topics.x` / `topics.y` → `command`, `status` | both | MQTT topics per axis. Python picks one with `--x` / `--y` |

**To change anything:** edit `connection.json`, then

```bash
scripts/flash.sh            # regenerates the firmware header from connection.json, compiles and flashes
```

Python needs no step: it reads the file every time it starts. New Wi-Fi, or the PC got a new IP? Edit (or nothing, with `"auto"`) and run `scripts/flash.sh` again.
`firmware/stepper_tracker/connection.h` is generated and must never be edited by hand: it is overwritten on every `scripts/flash.sh`, and the sketch refuses to compile without it.
`python3 scripts/sync_firmware.py` alone regenerates it and prints what the board will get; `python3 scripts/sync_firmware.py --check` tells you whether it is out of date. The firmware has no TLS yet, so an internet broker must accept plain port 1883.

## Other tunable values

Names below are conceptual; the code uses upper-case constants in `src/config.py` and at the top of `stepper_tracker.ino`.

| Group | Key | Default | Meaning |
|-------|-----|---------|---------|
| Camera | `camera_index` | 0 | External camera device |
| Camera | `frame_width/height` | requested 640×480 | Requested only; the real size is read back from the camera |
| Mapping | `dead_zone` | 0.05 | Fraction of half-width treated as centred |
| Mapping | `FULL_SPEED_AT` | 0.8 | Offset (fraction of half-width) already shown as 6 o'clock |
| Mapping | `LEVELS` | 6 | Steps between 12 and the maximum (11…6 / 1…6) |
| Motor | `POINTER_DEGREES_AT_FULL` | 180 | Pointer angle at `normalized` ±1 = 6 o'clock (firmware) |
| Motor | `HOME_AFTER_LOST_MS` | 3000 | Pointer returns to 12 after this long without a tracked face (firmware) |
| Motor | `steps_per_revolution` | 2048 | 28BYJ-48 full-step |
| Motor | `steps_per_degree` | derived | `steps_per_revolution / 360` – never typed in by hand |
| Motor | `min_steps / max_steps` | derived from limits | Mechanical limits |
| Tracker | `lost_timeout` | 24 | Frames without the target before returning to SEARCHING (existing `LockedFaceTracker`) |
| MQTT | `PUBLISH_INTERVAL_S` | 0.2 | Time between commands |
| Tracker | `TRACK_SMOOTHING` | 0.5 | EMA weight of the newest face position |
| Tracker | `VERIFY_EVERY` | 30 | Frames between identity re-checks of the locked face |
