import json
import time

import paho.mqtt.client as mqtt

from .config import BROKER_HOST, BROKER_PASSWORD, BROKER_PORT, BROKER_USERNAME, TOPICS


class CommandPublisher:
    """The only module that talks MQTT. Reconnects on its own if the broker is down or restarts."""

    def __init__(self, axis: str = "x"):
        self.topic = TOPICS[axis]["command"]
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if BROKER_USERNAME:
            self.client.username_pw_set(BROKER_USERNAME, BROKER_PASSWORD)
        self.client.connect_async(BROKER_HOST, BROKER_PORT)
        self.client.loop_start()

    def send(self, normalized: float, locked: bool):
        payload = {"normalized": round(normalized, 3), "locked": locked}
        self.client.publish(self.topic, json.dumps(payload, separators=(",", ":")))

    def home(self):
        """Tell the motor to drive back to its center (12:00). Waits briefly for the connection."""
        deadline = time.monotonic() + 3
        while not self.client.is_connected() and time.monotonic() < deadline:
            time.sleep(0.05)
        self.client.publish(self.topic, '{"home":true}').wait_for_publish(1)

    def close(self):
        self.client.loop_stop()
        self.client.disconnect()
