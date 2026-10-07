# Setup Guide

Commands assume Debian/Kali. Run them from the project root unless noted. In a normal terminal type commands as shown; a leading `!` is only for the Claude Code prompt (in a shell it negates the exit status and breaks `&&` chains).

## 1. Install Mosquitto (the broker)

```bash
sudo apt install mosquitto mosquitto-clients
```

## 2. Let the ESP8266 connect over Wi-Fi

By default Mosquitto only accepts connections from the PC itself.

```bash
echo -e "listener 1883 0.0.0.0\nallow_anonymous true" | sudo tee /etc/mosquitto/conf.d/lan.conf
sudo systemctl enable --now mosquitto
sudo systemctl restart mosquitto
hostname -I          # note the PC's LAN IP; it goes into the firmware
```

`allow_anonymous true` is for development only. With `ufw`, also run `sudo ufw allow 1883`.

## 3. Check the broker with two terminals

```bash
# terminal A
mosquitto_sub -h 127.0.0.1 -t 'tracker/#' -v
# terminal B
mosquitto_pub -h 127.0.0.1 -t tracker/x/command -m '{"normalized":-0.5,"locked":true}'
```

The message must appear in terminal A.

## 3b. Connection settings

Copy `connection.example.json` to `connection.json` and fill in `wifi` (see [configuration.md](configuration.md)). This one file is the only place you set the network; Python and the firmware both read it.

## 4. Install Paho and the Python packages with uv

```bash
uv sync              # installs paho-mqtt, opencv, mediapipe, onnxruntime
```

Python takes the broker from `connection.json` (`"auto"` = localhost on this PC).

## 5. Run the face tracker

```bash
uv run python -m src.enroll                                   # enroll a person first (SPACE capture, s save, q quit)
uv run python -m src.main --target twarimitswe                # horizontal tracking (--x is the default)
uv run python -m src.main --target twarimitswe --y            # vertical tracking (the default `"xy"` board follows both modes)
uv run python -m src.main --target twarimitswe --fullscreen   # f = fullscreen, m = small window, q = quit
```

Terminal A from step 3 should show `{"normalized":...,"locked":...}` about five times a second. `q` quits the preview.
The `--y` mode publishes to `tracker/y/command`, so subscribe to that topic instead.

## 6. Flash the ESP8266

Set `wifi.ssid` and `wifi.password` in `connection.json` (the broker stays `"auto"` = this PC). Then one command compiles and flashes:

```bash
scripts/flash.sh            # or: scripts/flash.sh /dev/ttyUSB1
```

It regenerates the firmware header from `connection.json` first. The individual steps are:

```bash
arduino-cli core install esp8266:esp8266 --additional-urls https://arduino.esp8266.com/stable/package_esp8266com_index.json
arduino-cli lib install PubSubClient
arduino-cli board list                        # find the port, e.g. /dev/ttyUSB0
python3 scripts/sync_firmware.py              # connection.json -> firmware header
arduino-cli compile --fqbn esp8266:esp8266:nodemcuv2 firmware/stepper_tracker
arduino-cli upload  --fqbn esp8266:esp8266:nodemcuv2 -p /dev/ttyUSB0 firmware/stepper_tracker
sudo usermod -aG dialout $USER                # only if upload says permission denied; then log out and in
```

To re-flash after changing `connection.json` (new Wi-Fi, new PC IP): `scripts/flash.sh`.

Wiring is in [firmware.md](firmware.md).

## 7. Test the motor without the camera

```bash
mosquitto_pub -t tracker/x/command -m '{"normalized":-1.0,"locked":true}'   # turns left by 12°
mosquitto_pub -t tracker/x/command -m '{"normalized":0.5,"locked":true}'    # turns right by 6°
mosquitto_sub -t tracker/x/status -v                                        # online / offline
```

If the motor turns the wrong way, set `MOTOR_DIRECTION` to `-1` in the firmware and re-flash.
