/*
 * stepper_tracker.ino
 *
 * ESP8266 + 28BYJ-48 (ULN2003) clock-style pointer driven by face tracking.
 * Subscribes to the MQTT command topic and points at the hour given by the normalized value:
 *   normalized -1 = 6 o'clock to the left, 0 = 12 o'clock, +1 = 6 o'clock to the right
 *   (-0.5 = 9, +1/6 = 1, ...). Absolute: the pointer shows the face position and returns to 12 on its own.
 * Knows nothing about faces or the dial: it only converts normalized -> degrees -> steps.
 *
 * Commands (JSON):
 *   {"normalized":-0.5,"locked":true}   point there (locked:false is ignored; pointer returns to 12 after a while)
 *   {"home":true}                       go to 12
 *   {"jog":-200}                        turn N steps (any sign) to line the pointer up by hand...
 *   {"step_us":3000}                    microseconds per step (bigger = slower, stronger); not saved
 *   {"coils":1}                         try another winding order (0, 1, 2) if the motor vibrates or cannot reverse
 *   {"zero":true}                       ...then declare the current position to be 12 (no sensor: do this once)
 *
 * The position is remembered in flash, so after a restart or re-flash the pointer drives itself to 12 first.
 *
 * Wiring: ULN2003 IN1..IN4 -> D1, D2, D3, D4; driver negative (-) -> ESP GND; driver + -> 5V.
 * Requires the "PubSubClient" library (Library Manager).
 * Connection settings come from connection.h (generated from connection.json).
 */

#include <EEPROM.h>
#include <ESP8266WiFi.h>
#include <PubSubClient.h>

// Wi-Fi, broker and topics come from connection.json (the only place to edit them). Never edit connection.h:
// scripts/flash.sh regenerates it from connection.json every time.
#if !__has_include("connection.h")
#error "connection.h is missing: run scripts/flash.sh (it generates connection.h from connection.json)"
#endif
#include "connection.h"

const float POINTER_DEGREES_AT_FULL = 180.0f; // normalized +-1 = 6 o'clock = 180 deg from 12
const int MOTOR_DIRECTION = 1;                // -1 swaps left/right if the pointer turns the wrong way
const unsigned long HOME_AFTER_LOST_MS = 3000; // no face for this long: pointer returns to 12

const long STEPS_PER_REV = 4096;              // 28BYJ-48 in half-step mode
const float STEPS_PER_DEGREE = STEPS_PER_REV / 360.0f;
unsigned long stepIntervalUs = 2000;          // ~44 deg/s. Too fast = the motor only vibrates. {"step_us":N} changes it live

const int COIL_PINS[4] = {D1, D2, D3, D4};
// Which input drives which winding. If the motor vibrates or cannot reverse, try the other orders: {"coils":1}, {"coils":2}
const uint8_t COIL_ORDERS[3][4] = {{0, 1, 2, 3}, {0, 2, 1, 3}, {0, 1, 3, 2}};
int coilOrder = 0;
const uint8_t HALF_STEP[8][4] = {
    {1, 0, 0, 0}, {1, 1, 0, 0}, {0, 1, 0, 0}, {0, 1, 1, 0},
    {0, 0, 1, 0}, {0, 0, 1, 1}, {0, 0, 0, 1}, {1, 0, 0, 1}};

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

long currentSteps = 0; // 0 = home, where the camera looked at power-up
long targetSteps = 0;
int phase = 0;
unsigned long lastStepUs = 0;
unsigned long lastTrackedMs = 0;
bool tracking = false;
bool coilsOn = false;
long savedSteps = 0;
unsigned long lastMoveMs = 0;
unsigned long lastSaveMs = 0;

const uint32_t POSITION_MAGIC = 0x12C10C4;
const unsigned long SAVE_AFTER_IDLE_MS = 1000;
const unsigned long MIN_SAVE_INTERVAL_MS = 5000;  // limits flash wear while tracking
struct SavedPosition {
  uint32_t magic;
  long steps;
};

void writeCoils(int p) {
  for (int i = 0; i < 4; i++) digitalWrite(COIL_PINS[COIL_ORDERS[coilOrder][i]], HALF_STEP[p][i]);
}

void releaseCoils() {
  for (int i = 0; i < 4; i++) digitalWrite(COIL_PINS[i], LOW);
}

void onMessage(char *topic, byte *payload, unsigned int length) {
  char msg[160];
  length = min(length, (unsigned int)sizeof(msg) - 1);
  memcpy(msg, payload, length);
  msg[length] = '\0';

  if (strstr(msg, "\"home\":true")) {
    targetSteps = 0;
    tracking = false;
    return;
  }
  if (strstr(msg, "\"zero\":true")) { // the pointer is physically at 12 right now
    currentSteps = targetSteps = 0;
    savePosition();
    return;
  }
  const char *coils = strstr(msg, "\"coils\":");
  if (coils) {
    coilOrder = constrain(atoi(coils + strlen("\"coils\":")), 0, 2);
    Serial.printf("coil order %d\n", coilOrder);
    return;
  }
  const char *speed = strstr(msg, "\"step_us\":");
  if (speed) {
    stepIntervalUs = constrain(atol(speed + strlen("\"step_us\":")), 800L, 20000L);
    Serial.printf("step interval %lu us\n", stepIntervalUs);
    return;
  }
  const char *jog = strstr(msg, "\"jog\":");
  if (jog) {
    targetSteps = currentSteps + atol(jog + strlen("\"jog\":"));
    tracking = false;
    return;
  }
  if (strstr(msg, "\"locked\":false")) return; // target lost: loop() returns the pointer to 12 after a while
  const char *field = strstr(msg, "\"normalized\":");
  if (!field) return;

  float normalized = constrain(atof(field + strlen("\"normalized\":")), -1.0f, 1.0f);
  targetSteps = lround(normalized * POINTER_DEGREES_AT_FULL * STEPS_PER_DEGREE) * MOTOR_DIRECTION;
  tracking = true;
  lastTrackedMs = millis();
  Serial.printf("cmd normalized=%.2f target=%ld\n", normalized, targetSteps);
}

void stepMotor() {
  if (currentSteps == targetSteps) {
    if (coilsOn) {
      releaseCoils(); // idle coils only heat the driver
      coilsOn = false;
      Serial.printf("reached %ld\n", currentSteps);
    }
    return;
  }
  coilsOn = true;
  lastMoveMs = millis();
  unsigned long now = micros();
  if (now - lastStepUs < stepIntervalUs) return;
  lastStepUs = now;

  int dir = targetSteps > currentSteps ? 1 : -1;
  phase = (phase + dir + 8) % 8;
  writeCoils(phase);
  currentSteps += dir;
}

// like delay(), but keeps the pointer moving (so it reaches 12 at power-up even with no network)
void waitMs(unsigned long ms) {
  unsigned long start = millis();
  while (millis() - start < ms) {
    stepMotor();
    yield();
  }
}

void savePosition() {
  SavedPosition saved = {POSITION_MAGIC, currentSteps};
  EEPROM.put(0, saved);
  EEPROM.commit();
  savedSteps = currentSteps;
  lastSaveMs = millis();
}

void connectMqtt() {
  while (!mqtt.connected()) {
    if (mqtt.connect("stepper-tracker", BROKER_USER[0] ? BROKER_USER : nullptr, BROKER_USER[0] ? BROKER_PASSWORD : nullptr, TOPIC_STATUS, 0, true, "offline")) {
      mqtt.publish(TOPIC_STATUS, "online", true);
      mqtt.subscribe(TOPIC_COMMAND);
      if (TOPIC_COMMAND_2[0]) mqtt.subscribe(TOPIC_COMMAND_2); // one pointer, either tracking mode
      Serial.println("MQTT connected");
    } else {
      Serial.printf("MQTT failed rc=%d (broker %s:%u)\n", mqtt.state(), BROKER_HOST, BROKER_PORT);
      waitMs(1000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  for (int i = 0; i < 4; i++) pinMode(COIL_PINS[i], OUTPUT);
  releaseCoils();

  EEPROM.begin(sizeof(SavedPosition));
  SavedPosition saved;
  EEPROM.get(0, saved);
  if (saved.magic == POSITION_MAGIC) { // we know where the pointer was left: drive it to 12
    currentSteps = savedSteps = saved.steps;
    Serial.printf("\nRestored position %ld steps, returning to 12\n", currentSteps);
  }
  targetSteps = 0;

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("\nJoining Wi-Fi '%s'", WIFI_SSID);
  int lastStatus = -1;
  while (WiFi.status() != WL_CONNECTED) {
    waitMs(500);
    int status = WiFi.status();
    if (status != lastStatus) { // say why it is not connecting
      lastStatus = status;
      Serial.printf("\n[Wi-Fi status %d: %s]", status,
                    status == WL_NO_SSID_AVAIL ? "network not found (out of range or 5 GHz)"
                    : status == WL_WRONG_PASSWORD ? "wrong password"
                    : status == WL_CONNECT_FAILED ? "connect failed (password or security mismatch)"
                    : status == WL_DISCONNECTED ? "connecting..." : "other");
    }
    Serial.print('.');
  }
  Serial.printf("\nWi-Fi OK, ESP IP %s\n", WiFi.localIP().toString().c_str());

  mqtt.setServer(BROKER_HOST, BROKER_PORT);
  mqtt.setCallback(onMessage);
}

void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();
  if (tracking && millis() - lastTrackedMs > HOME_AFTER_LOST_MS) {
    targetSteps = 0;
    tracking = false;
  }
  stepMotor();
  // remember where the pointer rests (12 immediately, other hours at most every 5 s)
  bool idle = currentSteps == targetSteps && millis() - lastMoveMs > SAVE_AFTER_IDLE_MS;
  if (idle && currentSteps != savedSteps && (currentSteps == 0 || millis() - lastSaveMs > MIN_SAVE_INTERVAL_MS)) savePosition();
}
