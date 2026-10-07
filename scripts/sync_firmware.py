"""Generate firmware/stepper_tracker/connection.h from connection.json (the single source of truth).

scripts/flash.sh runs this before compiling, so normally you only edit connection.json and run flash.sh.
 python3 scripts/sync_firmware.py           # just regenerate the header
 python3 scripts/sync_firmware.py --check   # exit 1 if the header does not match connection.json
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src.connection import SETTINGS, broker_host_for_board  # noqa: E402

wifi, broker, topics = SETTINGS["wifi"], SETTINGS["broker"], SETTINGS["topics"]
axes = SETTINGS.get("axis", "x")  # "x", "y", or "xy" = one pointer that follows whichever mode the tracker runs
host = broker_host_for_board()

header = f"""// GENERATED from connection.json by scripts/sync_firmware.py. Do NOT edit: change connection.json instead.
#pragma once
const char *WIFI_SSID = {json.dumps(wifi["ssid"])};
const char *WIFI_PASSWORD = {json.dumps(wifi["password"])};
const char *BROKER_HOST = {json.dumps(host)};
const uint16_t BROKER_PORT = {int(broker["port"])};
const char *BROKER_USER = {json.dumps(broker["username"])};
const char *BROKER_PASSWORD = {json.dumps(broker["password"])};
const char *TOPIC_COMMAND = {json.dumps(topics[axes[0]]["command"])};
const char *TOPIC_COMMAND_2 = {json.dumps(topics[axes[1]]["command"] if len(axes) > 1 else "")};
const char *TOPIC_STATUS = {json.dumps(topics[axes[0]]["status"])};
"""
out = ROOT / "firmware" / "stepper_tracker" / "connection.h"
if "--check" in sys.argv:
    if not out.exists() or out.read_text() != header:
        sys.exit("connection.h is out of date with connection.json: run scripts/flash.sh (or scripts/sync_firmware.py)")
    print("connection.h matches connection.json")
    sys.exit(0)
out.write_text(header)
print(f"firmware gets: Wi-Fi '{wifi['ssid']}', broker {host}:{broker['port']}, axis {axes}, topics {[topics[a]['command'] for a in axes]}")
if not wifi["password"]:
    print("WARNING: wifi.password is empty in connection.json (fine only for an open network)")
