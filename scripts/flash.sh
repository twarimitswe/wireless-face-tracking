#!/bin/sh
# Regenerate the firmware connection header from connection.json, then compile and flash the ESP8266.
# Usage: scripts/flash.sh [serial-port]      (default /dev/ttyUSB0). Stop the tracker first.
set -e
cd "$(dirname "$0")/.."
PORT="${1:-/dev/ttyUSB0}"
python3 scripts/sync_firmware.py
arduino-cli compile --fqbn esp8266:esp8266:nodemcuv2 firmware/stepper_tracker
arduino-cli upload --fqbn esp8266:esp8266:nodemcuv2 -p "$PORT" firmware/stepper_tracker
