import json
import logging
import threading
import time
from collections import deque
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from agents import CoordinatorAgent, simulate_environment
from mqtt_handler import MQTTHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("app")

state = {
    "mode": "manual",
    "current_speed": "OFF",
    "temperature": 25.0,
    "hour": 12,
    "time_of_day": "day",
    "is_occupied": False,
    "mqtt_connected": False,
    "last_decision": None,
}
log_buffer = deque(maxlen=100)
coordinator = CoordinatorAgent()
mqtt_handler = None
auto_thread = None
auto_running = threading.Event()

def add_log(level, message, extra=None):
    entry = {
        "ts": datetime.now().strftime("%H:%M:%S"),
        "level": level,
        "message": message,
        "extra": extra or {}
    }
    log_buffer.appendleft(entry)
    getattr(logger, level.lower(), logger.info)(message)

def on_device_status(payload):
    add_log("info", f"Device status: {payload}")

def init_mqtt():
    global mqtt_handler
    mqtt_handler = MQTTHandler(on_status_cb=on_device_status)
    connected = mqtt_handler.connect(timeout=8)
    state["mqtt_connected"] = connected
    if connected:
        add_log("info", "MQTT broker connected!")
    else:
        add_log("warning", "MQTT offline - running in simulation mode")

def send_speed(speed, mode="manual"):
    state["current_speed"] = speed
    if mqtt_handler and mqtt_handler.connected:
        mqtt_handler.publish_speed(speed, mode)
        add_log("info", f"MQTT sent: speed={speed} mode={mode}")
    else:
        add_log("warning", f"Simulated: speed={speed} mode={mode}")

def auto_control_loop():
    add_log("info", "AUTO mode started")
    while auto_running.is_set():
        env = simulate_environment()
        result = coordinator.decide(env)
        state["temperature"] = env.temperature
        state["hour"] = env.hour
        state["time_of_day"] = env.time_label
        state["is_occupied"] = env.is_occupied
        state["last_decision"] = result
        new_speed = result["final_speed"]
        send_speed(new_speed, mode="auto")
        add_log("info", f"AI decided: {new_speed} | temp={env.temperature}C | {env.time_label}", result)
        time.sleep(5)
    add_log("info", "AUTO mode stopped")

def start_auto():
    global auto_thread
    auto_running.set()
    auto_thread = threading.Thread(target=auto_control_loop, daemon=True)
    auto_thread.start()

def stop_auto():
    auto_running.clear()

app = Flask(__name__, static_folder=".")
CORS(app)
VALID_SPEEDS = {"OFF", "LOW", "MEDIUM", "HIGH"}

@app.route("/")
def index():
    return send_from_directory(".", "dashboard.html")

@app.route("/api/status")
def api_status():
    return jsonify({
        "ok": True,
        "state": state,
        "logs": list(log_buffer)[:20]
    })

@app.route("/api/set_speed", methods=["POST"])
def api_set_speed():
    if state["mode"] != "manual":
        return jsonify({"ok": False, "error": "Switch to MANUAL mode first"}), 400
    data = request.json or {}
    speed = str(data.get("speed", "")).upper()
    if speed not in VALID_SPEEDS:
        return jsonify({"ok": False, "error": "Invalid speed"}), 400
    send_speed(speed, mode="manual")
    add_log("info", f"Manual: speed set to {speed}")
    return jsonify({"ok": True, "speed": speed})

@app.route("/api/set_mode", methods=["POST"])
def api_set_mode():
    data = request.json or {}
    mode = str(data.get("mode", "")).lower()
    if mode not in ("manual", "auto"):
        return jsonify({"ok": False, "error": "Invalid mode"}), 400
    if mode == "auto" and state["mode"] != "auto":
        state["mode"] = "auto"
        start_auto()
        add_log("info", "Switched to AUTO mode")
    elif mode == "manual" and state["mode"] != "manual":
        state["mode"] = "manual"
        stop_auto()
        add_log("info", "Switched to MANUAL mode")
    return jsonify({"ok": True, "mode": state["mode"]})

@app.route("/api/logs")
def api_logs():
    return jsonify({"logs": list(log_buffer)})

if __name__ == "__main__":
    add_log("info", "Smart Fan System starting...")
    init_mqtt()
    add_log("info", "Open http://localhost:5000 in your browser")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)