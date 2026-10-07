#!/bin/sh
# Try each coil order: the motor should turn ~45 deg one way, then back the other way, smoothly.
# Watch the pointer and note which order does BOTH. Stop the tracker first.
# Usage: scripts/motor_test.sh [broker-host]
H="${1:-127.0.0.1}"
pub() { mosquitto_pub -h "$H" -t tracker/x/command -m "$1"; }
pub '{"step_us":3000}'
for order in 0 1 2; do
  pub "{\"coils\":$order}"
  echo "== coil order $order: turning FORWARD (+512 steps)"; pub '{"jog":512}'; sleep 5
  echo "== coil order $order: turning BACK (-512 steps)";    pub '{"jog":-512}'; sleep 5
done
echo "Done. Use the order that turned both ways smoothly, e.g. mosquitto_pub -t tracker/x/command -m '{\"coils\":1}'"
