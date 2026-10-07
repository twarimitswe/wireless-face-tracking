# Architecture

```text
┌───────────────────────────┐   MQTT   ┌──────────────┐   MQTT   ┌───────────────────────────┐
│ 1. Computer Vision        │ ───────► │ 2. Mosquitto │ ───────► │ 3. Embedded Controller    │
│ Camera → detect →         │ publish  │    broker    │ subscribe│ ESP8266 → 28BYJ-48        │
│ recognize → lock →        │          │              │          │                           │
│ offset → normalize → pub  │          │              │          │                           │
└───────────────────────────┘          └──────────────┘          └───────────────────────────┘
```

## Environment 1 – Computer Vision (Python)
Camera capture, face detection, recognition, target selection, face lock, tracking, offset calculation,
normalization, dial-position selection and publishing via Paho MQTT. It **never drives the motor**.

## Environment 2 – Mosquitto
Only transports messages. Accepts connections, receives commands, delivers them to subscribers. Its address and port are configuration, not code.

## Environment 3 – ESP8266 + 28BYJ-48
Connects to Wi-Fi and the broker, subscribes to the command topic, converts the received command into a direction
and a number of steps, and drives the motor. It knows nothing about faces.

## Processing chain

```text
Face bounding box
   ↓  (centre of box)
face_center_x
   ↓  (− image centre)
offset_x            [pixels]
   ↓  (÷ half frame width, clamp)
normalized          [-1.0 … +1.0]
   ↓  (dead zone + hour)
normalized command  [0, ±1/6 … ±1 = the hour to show]   (dial 12 / 11…6 / 1…6 is its display label)
   ↓  MQTT message {normalized, locked}
pointer angle       [degrees, absolute from 12]
   ↓  (× steps per degree)
steps               [motor steps]
```

Each arrow is a single, explicit conversion that lives in exactly one place.

## Separation of concerns

| Stage | Owns | Must not |
|-------|------|----------|
| Camera | frames, resolution | detect faces |
| Detection / Recognition | boxes, identities | publish or move anything |
| Tracking / Lock | which face is the target | compute steps |
| Coordinate mapping | pixels → normalized | know about the motor |
| Movement calculation | normalized → dead-zoned hour command | know about MQTT |
| MQTT publisher | serialization, topics | contain vision logic |
| Firmware | normalized → steps (no mapping) | know about faces or the dial |
