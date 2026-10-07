# Deployment

## Today: everything on one PC

```text
PC
├── Python + camera        → publishes to 127.0.0.1:1883
├── Mosquitto              → listens on all interfaces
└── ESP8266 (over Wi-Fi)   → connects to the PC's LAN IP:1883
```

The ESP8266 cannot use `127.0.0.1`; it needs the PC's LAN address. Python may use either.

## Later: separate machines

```text
Computer A: Python + camera   ── broker.host = <B's IP>
Computer B: Mosquitto
ESP8266:                      ── broker host  = <B's IP>
```

Only `connection.json` changes (`broker.host`, then `scripts/flash.sh` for the board) – no code changes. The same applies to a broker on the internet.

## Checklist

1. Mosquitto listener is not localhost-only and the firewall allows port 1883.
2. `mosquitto_sub -h <broker> -t 'tracker/#' -v` shows commands while Python runs.
3. ESP8266 and broker are on the same network.
4. Test without the camera: `mosquitto_pub -h <broker> -t tracker/x/command -m '{"normalized":-0.5,"locked":true}'`
5. Test the motor without Python this way before connecting the vision side.
