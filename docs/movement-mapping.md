# Movement Mapping – the 12 → 11…6 / 1…6 dial

The motor position is described like the hours of a clock face seen from the camera:

```text
                12   ← centered (face on the image centre)
        11             1
     10                   2
    9                       3
     8                   4
        7              5
                6   ← maximum movement
```

- **12** – the face is centred: the motor stays where it is.
- **Face LEFT of centre** → counter-clockwise: **11, 10, 9, 8, 7, 6**
- **Face RIGHT of centre** → clockwise: **1, 2, 3, 4, 5, 6**
- The **further** the face is from the centre, the **further** from 12 the dial moves.
  11 (or 1) is the smallest correction; **6 is the maximum**.

> The motor turns a clock-style pointer: 12 = centred, 11…6 = left, 1…6 = right (6 = the furthest).

## Vertical mode (`--y`)

Same pointer and same mapping, driven by the up/down offset instead of left/right:

| Face is | Pointer shows |
|---------|---------------|
| On the horizontal center line | 12 |
| Above it | 11 … 6 (left-hand hours; the farther up, the lower the hour) |
| Below it | 1 … 6 (right-hand hours; the farther down, the higher the hour) |

`offset_y = (face_center_y − H/2) / (H/2)`. Image y grows downward, so the offset is used as is: down = positive = right-hand hours. `src/axis.py` is the only
place that chooses between x and y; the dead zone, hours and firmware are identical. The preview then draws horizontal zone lines
with the hours labelled on the left (11…6 above the centre line, 1…6 below).

## Algorithm

```text
n      = normalized offset in [−1, +1]           (see coordinate-mapping.md)
if |n| ≤ dead_zone:            position = 12
else:
    level = ceil( min(1, (|n| − dead_zone) / (full_speed_at − dead_zone)) × levels )     # 1 … 6
    n < 0 (left):  position = 12 − level         # 11 … 6
    n > 0 (right): position = level              # 1 … 6
```

Each of the 6 levels covers an equal slice of the distance between the dead zone and `full_speed_at`.

### Example (W = 640, dead_zone = 0.05, full_speed_at = 0.8, levels = 6)

| face_center_x | normalized | level | Dial |
|---------------|-----------|-------|------|
| 320 | +0.00 | – | 12 |
| 310 | -0.03 | – (dead zone) | 12 |
| 250 | -0.22 | 2 | 10 |
| 160 | -0.50 | 4 | 8 |
| 0 | -1.00 | 6 | 6 |
| 400 | +0.25 | 2 | 2 |
| 336 | +0.05 | – (dead zone) | 12 |
| 339 | +0.06 | 1 | 1 |
| 480 | +0.50 | 4 | 4 |
| 640 | +1.00 | 6 | 6 |

## From dial position to motor – an absolute pointer

The motor turns a clock-style **pointer**. The pointer shows where the person is relative to the centre, so it is **absolute**:
centred means 12, and it returns to 12 by itself whenever the person comes back to the centre.

Python publishes the hour as a normalized command (`level / 6`: 0, ±1/6 … ±6/6). The firmware only converts it:

```text
angle_deg = normalized × POINTER_DEGREES_AT_FULL           (180° = 6 o'clock)
steps     = round(angle_deg × steps_per_degree) × MOTOR_DIRECTION
target    = steps                                          (absolute, from 12)
```

| Hour shown | 12 | 1 / 11 | 2 / 10 | 3 / 9 | 4 / 8 | 5 / 7 | 6 |
|------------|----|--------|--------|-------|-------|-------|---|
| `normalized` | 0 | ±0.167 | ±0.333 | ±0.5 | ±0.667 | ±0.833 | ±1.0 |
| Pointer angle from 12 | 0° | 30° | 60° | 90° | 120° | 150° | 180° |
| Steps (half-step, 4096/rev) | 0 | ±341 | ±683 | ±1024 | ±1365 | ±1707 | ±2048 |

Face offset to hour: inside the dead zone → 12; otherwise `ceil(min(1, (|offset| − dead_zone) / (FULL_SPEED_AT − dead_zone)) × 6)`.
`FULL_SPEED_AT` (0.8 of the half-width) is the offset that already shows 6, so the extremes are reached before the face leaves the frame.

If no face is tracked for `HOME_AFTER_LOST_MS` (3 s) the pointer returns to 12. The tracker also sends `{"home":true}` on start and on exit.

### Starting at 12 and calibrating

A 28BYJ-48 has no position sensor, so the firmware counts steps from 12 and **remembers the count in flash** (EEPROM). At every power-up, restart or
re-flash it reads the saved position and drives the pointer to 12 straight away, even before Wi-Fi is connected. The position is saved
1 s after the pointer stops (12 immediately, other hours at most every 5 s to limit flash wear).

Calibrate once, and again whenever the pointer is turned by hand or steps are lost (or after the first flash of a new board, which has no saved position):

```bash
mosquitto_pub -t tracker/x/command -m '{"jog":-100}'    # turn by N steps (negative/positive) until the pointer is exactly on 12
mosquitto_pub -t tracker/x/command -m '{"zero":true}'   # declare this position to be 12 (also saved to flash)
```

Stop the tracker before re-flashing: it sends the pointer back to 12 on exit, so the saved position is correct. If the board loses power while the pointer is on another hour, the saved position can be slightly stale.

28BYJ-48: `steps_per_degree = 4096 / 360 ≈ 11.378` (half-step). Step rate is 1.2 ms per step ≈ 73°/s, so 12 → 6 takes about 2.5 s.

## Tuning

`POINTER_DEGREES_AT_FULL` (180), `DEAD_ZONE` (0.05), `FULL_SPEED_AT` (0.8) and `STEP_INTERVAL_US` (1200) are starting values. If the mechanism cannot turn ±180°, lower `POINTER_DEGREES_AT_FULL`. If the pointer turns the wrong way for left/right, set `MOTOR_DIRECTION` to −1.
