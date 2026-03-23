# Smart Ceiling Fan IoT Control System

An AI-powered IoT demo where a multi-agent Python backend controls a simulated
ESP32 device (Wokwi) via MQTT — with a real-time web dashboard.

```
┌─────────────────────┐     MQTT publish      ┌──────────────────┐
│  Python Backend     │ ──────────────────────▶│  broker          │
│                     │                        │  (mosquitto.org) │
│  • Flask dashboard  │ ◀──────────────────────│                  │
│  • Multi-agent AI   │     MQTT subscribe     └────────┬─────────┘
│  • MQTT handler     │                                 │ subscribe
└─────────────────────┘                        ┌────────▼─────────┐
                                               │  ESP32 (Wokwi)   │
                                               │  LED1 ● GPIO 25  │
                                               │  LED2 ● GPIO 26  │
                                               │  LED3 ● GPIO 27  │
                                               └──────────────────┘
```

---

## Files

```
smart_fan_final/
├── app.py              Main app — Flask web server + CLI + AUTO loop
├── agents.py           Multi-agent AI (Temperature, Preference, Energy, Coordinator)
├── mqtt_handler.py     MQTT client — paho v1+v2 compatible, 3-broker fallback
├── requirements.txt    Python dependencies
└── esp32_fan/
    ├── sketch.ino      ESP32 Arduino firmware (paste into Wokwi)
    ├── diagram.json    Wokwi circuit — 3 LEDs on GPIO 25/26/27
    └── wokwi.toml      Wokwi library auto-install config
```

---

## Quickstart — Python App

### Step 1 — Install dependencies

```bash
cd iot_fan_controller
pip install -r requirements.txt
```

### Step 2 — Run

```bash
# Web dashboard (recommended)
python app.py
# Open http://localhost:5000

# CLI mode
python app.py --cli

# Offline demo (no internet / broker issues)
python app.py --no-mqtt

# Custom port
python app.py --port 8080
```

### Step 3 — Test MQTT separately (optional)

```bash
python mqtt_handler.py
```

This prints your paho-mqtt version, tries three brokers in order, publishes a
test message, and confirms the round-trip echo. Run this first if you're seeing
MQTT errors.

---

## Quickstart — Wokwi ESP32

1. Go to **https://wokwi.com/projects/new/esp32**

2. In the **code editor** tab — replace all content with `esp32_fan/sketch.ino`

3. In the **diagram.json** tab — replace all content with `esp32_fan/diagram.json`

4. Install libraries (pick ONE method):

   **Method A — Library Manager UI (most reliable)**
   - Click the 📚 Libraries icon in the left sidebar
   - Search `PubSubClient` → Install (by Nick O'Leary, v2.8)
   - Search `ArduinoJson`  → Install (by Benoit Blanchon, v6.x)

   **Method B — wokwi.toml**
   - Click **+ New File** → name it `wokwi.toml`
   - Paste the contents of `esp32_fan/wokwi.toml`
   - Wokwi will auto-install libraries on next simulation start

5. Click **▶ Start Simulation**

6. Watch the Serial Monitor — you should see:
   ```
   === Smart Fan ESP32 Device ===
   [WiFi] Connected  IP=...
   [MQTT] Connected
   [MQTT] Subscribed to fan/control
   ```

7. Send commands from the Python app → LEDs light up in Wokwi

---

## MQTT Broker

The app tries these public brokers **in order** and uses the first that responds:

| Broker | Host | Port |
|--------|------|------|
| Eclipse Mosquitto | `test.mosquitto.org` | 1883 |
| HiveMQ | `broker.hivemq.com` | 1883 |
| EMQX | `broker.emqx.io` | 1883 |

The ESP32 firmware is hardcoded to `test.mosquitto.org` (same as the Python
app's first choice). They will automatically talk to each other.

> **Note:** If you're on a corporate network or VPN, port 1883 may be blocked.
> Use `python app.py --no-mqtt` to run a fully offline demo where the AI agent
> logic still works — you just won't see LED updates in Wokwi.

---

## Multi-Agent AI Logic

```
Temperature (20–40°C sim)
    < 25°C  → OFF
    25–30°C → LOW
    30–35°C → MEDIUM
    ≥ 35°C  → HIGH
         │
         ▼
User Preference (real clock)
    22:00–06:00 → cap at LOW
    otherwise   → no change
         │
         ▼
Energy Agent
    HIGH → MEDIUM (always)
         │
         ▼
    Final Speed → MQTT publish
```

The Coordinator runs every **5 seconds** in AUTO mode.

---

## LED Mapping

| Speed  | GPIO 25 (Blue) | GPIO 26 (Yellow) | GPIO 27 (Red) |
|--------|:--------------:|:----------------:|:-------------:|
| OFF    | ○              | ○                | ○             |
| LOW    | ●              | ○                | ○             |
| MEDIUM | ●              | ●                | ○             |
| HIGH   | ●              | ●                | ●             |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `MQTT build failed` | Run `python mqtt_handler.py` to see which broker works. If all fail, use `--no-mqtt`. |
| paho-mqtt version error | The handler auto-detects v1/v2. Make sure you installed via `pip install -r requirements.txt`. |
| `PubSubClient.h not found` in Wokwi | Install via Library Manager (📚 icon) — search PubSubClient, click Install. |
| ESP32 connects but no LED change | Check Serial Monitor broker matches Python app (both should use `test.mosquitto.org`). |
| Port 5000 already in use | Run `python app.py --port 8080` (or any free port). |
| Web UI shows MQTT ✗ but AI still works | MQTT is optional — AI decisions log normally, just no device communication. |
