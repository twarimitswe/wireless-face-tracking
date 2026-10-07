"""Reads connection.json, the single place where the Wi-Fi, broker and topics are set.

Python imports its values from here (via config.py); scripts/sync_firmware.py turns the same file into the firmware header.
broker.host "auto" means "the broker runs on this PC": Python uses localhost, the board gets this PC's current network address.
"""

import json
import socket
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = json.loads((ROOT / "connection.json").read_text())  # copy connection.example.json to create it


def lan_ip() -> str:
    """This PC's address on the network it is connected to now (what a board on the same Wi-Fi must connect to)."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))  # picks the outgoing interface; sends nothing
            return probe.getsockname()[0]
    except OSError as error:
        raise SystemExit(f"Cannot work out this PC's network address ({error}). Connect to the network, or set broker.host in connection.json.")


def broker_host_for_pc() -> str:
    host = SETTINGS["broker"]["host"]
    return "127.0.0.1" if host == "auto" else host


def broker_host_for_board() -> str:
    host = SETTINGS["broker"]["host"]
    return lan_ip() if host == "auto" else host
