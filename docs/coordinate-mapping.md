# Coordinate Mapping

All values are computed from the **actual frame size** returned by the camera – never from hard-coded pixels.

```text
W, H        = frame width, height
center_x    = W / 2
center_y    = H / 2
face_center_x = x + w / 2          (from bounding box x, y, w, h)
face_center_y = y + h / 2
offset_x    = face_center_x − center_x
normalized  = clamp(offset_x / center_x, −1.0, +1.0)
```

## Sign convention

| offset_x | normalized | Face is | Camera must turn |
|----------|-----------|---------|------------------|
| < 0 | negative | LEFT of centre | left |
| ≈ 0 (inside dead zone) | 0.0 | CENTERED | not at all |
| > 0 | positive | RIGHT of centre | right |

Image x grows to the right, so the sign of `offset_x` directly gives the direction.
> If the image is mirrored (some webcams), fix it **once** in the camera module, not downstream.

## Worked example (W = 640)

`center_x = 320`

| face_center_x | offset_x | normalized |
|---------------|----------|-----------|
| 320 | 0 | 0.000 |
| 160 | −160 | −0.500 |
| 0 | −320 | −1.000 |
| 480 | +160 | +0.500 |
| 600 | +280 | +0.875 |

Only the horizontal axis drives the motor; `center_y` / `offset_y` are computed for completeness but unused.

## Dead zone

`normalized` whose magnitude is ≤ `dead_zone` is treated as 0.0 so the motor does not jitter.
`dead_zone` is a fraction of half-width (default 0.05 → 16 px at W = 640), so it scales with resolution.
