#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ── Wi-Fi (Wokwi virtual network) ────────────────────────────────────────────
const char* WIFI_SSID = "Wokwi-GUEST";
const char* WIFI_PASS = "";

// ── MQTT ──────────────────────────────────────────────────────────────────────
const char* MQTT_BROKER = "broker.hivemq.com";
const int   MQTT_PORT   = 1883;
const char* MQTT_TOPIC  = "fan/control";
const char* CLIENT_ID   = "esp32_fan_device";
const char* DEVICE_ID   = "fan1";

// ── LED Pins ──────────────────────────────────────────────────────────────────
const int LED_LOW    = 25;   // 1 LED  → LOW
const int LED_MEDIUM = 26;   // 2 LEDs → MEDIUM
const int LED_HIGH   = 27;   // 3 LEDs → HIGH

WiFiClient   espClient;
PubSubClient mqttClient(espClient);

// ── Speed → LED states ────────────────────────────────────────────────────────
void applySpeed(String speed) {
  speed.toUpperCase();
  Serial.print("[FAN] Applying speed: ");
  Serial.println(speed);

  if (speed == "OFF") {
    digitalWrite(LED_LOW,    LOW);
    digitalWrite(LED_MEDIUM, LOW);
    digitalWrite(LED_HIGH,   LOW);
    Serial.println("[LED] ○ ○ ○  (all off)");
  } else if (speed == "LOW") {
    digitalWrite(LED_LOW,    HIGH);
    digitalWrite(LED_MEDIUM, LOW);
    digitalWrite(LED_HIGH,   LOW);
    Serial.println("[LED] ● ○ ○  (LOW)");
  } else if (speed == "MEDIUM") {
    digitalWrite(LED_LOW,    HIGH);
    digitalWrite(LED_MEDIUM, HIGH);
    digitalWrite(LED_HIGH,   LOW);
    Serial.println("[LED] ● ● ○  (MEDIUM)");
  } else if (speed == "HIGH") {
    digitalWrite(LED_LOW,    HIGH);
    digitalWrite(LED_MEDIUM, HIGH);
    digitalWrite(LED_HIGH,   HIGH);
    Serial.println("[LED] ● ● ●  (HIGH)");
  } else {
    Serial.print("[WARN] Unknown speed: ");
    Serial.println(speed);
  }
}

// ── MQTT message callback ─────────────────────────────────────────────────────
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) {
    msg += (char)payload[i];
  }
  Serial.print("[MQTT] Received on '");
  Serial.print(topic);
  Serial.print("': ");
  Serial.println(msg);

  // Parse JSON
  StaticJsonDocument<128> doc;
  DeserializationError err = deserializeJson(doc, msg);
  if (err) {
    Serial.print("[ERROR] JSON parse failed: ");
    Serial.println(err.c_str());
    return;
  }

  const char* device = doc["device"];
  const char* speed  = doc["speed"];

  if (!device || !speed) {
    Serial.println("[WARN] Missing 'device' or 'speed' field.");
    return;
  }

  // Only process commands meant for this device
  if (String(device) != DEVICE_ID) {
    Serial.print("[INFO] Command for '");
    Serial.print(device);
    Serial.println("' – ignored (not our device).");
    return;
  }

  applySpeed(String(speed));
}

// ── Wi-Fi setup ───────────────────────────────────────────────────────────────
void connectWiFi() {
  Serial.print("[WiFi] Connecting to ");
  Serial.print(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("[WiFi] Connected! IP: ");
  Serial.println(WiFi.localIP());
}

// ── MQTT reconnect ────────────────────────────────────────────────────────────
void reconnectMQTT() {
  while (!mqttClient.connected()) {
    Serial.print("[MQTT] Connecting to broker...");
    if (mqttClient.connect(CLIENT_ID)) {
      Serial.println(" connected!");
      mqttClient.subscribe(MQTT_TOPIC);
      Serial.print("[MQTT] Subscribed to '");
      Serial.print(MQTT_TOPIC);
      Serial.println("'");
    } else {
      Serial.print(" failed (rc=");
      Serial.print(mqttClient.state());
      Serial.println("). Retrying in 3s...");
      delay(3000);
    }
  }
}

// ── Arduino lifecycle ─────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(200);
  Serial.println("\n=== Smart Fan ESP32 Device ===");

  pinMode(LED_LOW,    OUTPUT);
  pinMode(LED_MEDIUM, OUTPUT);
  pinMode(LED_HIGH,   OUTPUT);
  applySpeed("OFF");  // Start with fan off

  connectWiFi();
  mqttClient.setServer(MQTT_BROKER, MQTT_PORT);
  mqttClient.setCallback(mqttCallback);
}

void loop() {
  if (!mqttClient.connected()) {
    reconnectMQTT();
  }
  mqttClient.loop();
}
