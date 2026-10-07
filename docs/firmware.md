# Environment 3 – ESP8266 + 28BYJ-48 (clock pointer)

Arduino `.ino` firmware (`firmware/stepper_tracker/stepper_tracker.ino`, needs the *PubSubClient* library). It knows nothing about faces – only commands.

## Behaviour

0. At power-up restore the saved position from flash and drive the pointer to 12 (before any network work).
1. Connect to Wi-Fi.
2. Connect to the broker (host/port from config) and subscribe to the command topic.
3. Parse the JSON command.
4. Convert the normalized value to degrees, then steps, then clamp to the mechanical limits (no mapping logic).
6. Step the motor without blocking the network loop (`client.loop()` must keep running).
7. Publish `online` on the status topic (retained) and set an `offline` Last Will.

## Conversion (absolute pointer, see movement-mapping.md)

```text
steps  = round(normalized × pointer_degrees_at_full × steps_per_degree) × motor_direction
target = steps                       (absolute from 12; the motor then steps toward it)
```

The sign of `normalized` is the direction; the firmware never sees dial positions.

## 28BYJ-48 facts

| Item | Value |
|------|-------|
| Steps per revolution (full-step) | 2048 |
| Steps per revolution (half-step) | 4096 |
| Steps per degree | half-step 4096 / 360 ≈ 11.378 (used); full-step ≈ 5.689 |
| Driver | ULN2003 board |
| Max speed | ≈ 10–15 RPM – limit step rate, or steps are skipped |

## Wiring

| ULN2003 | ESP8266 |
|---------|---------|
| IN1 | D1 (GPIO5) |
| IN2 | D2 (GPIO4) |
| IN3 | D3 (GPIO0) |
| IN4 | D4 (GPIO2) |
| − | ESP GND |
| + | 5 V (external supply recommended; its GND must join the ESP GND) |

> D3 (GPIO0) and D4 (GPIO2) are boot-strap pins: they must be high at reset. If the ESP8266 fails to boot with the driver attached, unplug IN3/IN4 while resetting, or move them to D5/D6.

## Motor does not turn properly

| Symptom | Try |
|---------|-----|
| Only vibrates | Slower: `{"step_us":4000}`; check the driver `+` is on 5 V (not 3V3) and the grounds are joined |
| Turns one way only / cannot reverse / jiggles | Another winding order: run `scripts/motor_test.sh`, then `{"coils":N}` for the order that works both ways. Make it permanent by changing `coilOrder` in the sketch |
| Wrong left/right | `MOTOR_DIRECTION` = −1 |

## Safety

- `normalized` is clamped to ±1, so the pointer never goes past 6 o'clock (±`POINTER_DEGREES_AT_FULL`).
- Position 0 = 12 o'clock. The step count is saved to flash, so a restart or re-flash returns the pointer to 12 by itself; calibrate with `jog` + `zero` when needed (see movement-mapping.md).
- `locked: false` commands are ignored; after `HOME_AFTER_LOST_MS` without a tracked face the pointer returns to 12.
- `MOTOR_DIRECTION` (±1) flips left/right without rewiring. It must make the camera turn *toward* the face; the wrong sign runs the motor to its limit and it cannot come back.
- `{"home":true}` returns to 12, `{"jog":N}` turns N steps and `{"zero":true}` declares the current position to be 12 (calibration).
- De-energize the coils when idle to avoid heating.
