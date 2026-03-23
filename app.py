"""
app.py — Smart Ceiling Fan Control System
==========================================
Modes:
  MANUAL  — user picks speed via web UI or CLI
  AUTO    — multi-agent AI picks speed every POLL_INTERVAL seconds

Usage:
  python app.py              → web dashboard at http://localhost:5000
  python app.py --cli        → interactive CLI
  python app.py --no-mqtt    → offline demo (no broker needed)
  python app.py --port 8080  → custom port
"""

import argparse
import json
import logging
import threading
import time
from datetime import datetime

from flask import Flask, Response, jsonify, render_template_string, request

from agents import CoordinatorAgent, simulate_environment
from mqtt_handler import MQTTHandler

# ─────────────────────────────────────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)-12s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("App")

# ─────────────────────────────────────────────────────────────────────────────
# Constants & shared state
# ─────────────────────────────────────────────────────────────────────────────

SPEEDS        = ["OFF", "LOW", "MEDIUM", "HIGH"]
POLL_INTERVAL = 5   # seconds between AUTO AI decisions

state = {
    "mode":        "MANUAL",
    "speed":       "OFF",
    "temperature": None,
    "hour":        None,
    "mqtt_ok":     False,
    "broker":      None,
    "logs":        [],
}
state_lock = threading.Lock()

coordinator = CoordinatorAgent()
mqtt_client = MQTTHandler()

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    entry = f"[{ts}] {msg}"
    logger.info(msg)
    with state_lock:
        state["logs"].insert(0, entry)
        if len(state["logs"]) > 100:
            state["logs"].pop()


def set_speed(speed: str, source: str = "MANUAL"):
    """Update state and publish via MQTT."""
    if speed not in SPEEDS:
        _log(f"Invalid speed '{speed}' — ignored.")
        return
    with state_lock:
        state["speed"] = speed
    _log(f"[{source}] Fan speed → {speed}")
    ok = mqtt_client.publish_speed(speed)
    if ok:
        _log(f"MQTT published  fan/control  speed={speed}")
    else:
        _log("MQTT publish skipped (not connected)")


def on_device_message(data: dict):
    _log(f"[DEVICE] Received ← device={data.get('device')}  speed={data.get('speed')}")

# ─────────────────────────────────────────────────────────────────────────────
# AUTO-mode background thread
# ─────────────────────────────────────────────────────────────────────────────

def auto_loop():
    while True:
        time.sleep(POLL_INTERVAL)
        with state_lock:
            if state["mode"] != "AUTO":
                continue
        env = simulate_environment()
        with state_lock:
            state["temperature"] = env["temperature"]
            state["hour"]        = env["hour"]
        _log(f"[AUTO] env  temp={env['temperature']}°C  hour={env['hour']}h")
        decision = coordinator.decide(env)
        set_speed(decision, source="AUTO-AI")


# ─────────────────────────────────────────────────────────────────────────────
# Flask web dashboard
# ─────────────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Fan Controller</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#080c14;--panel:#0d1422;--border:#1a2a4a;
  --accent:#00d4ff;--accent2:#ff6b35;--green:#00ff88;
  --text:#c8d8f0;--dim:#4a6080;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Share Tech Mono',monospace;min-height:100vh;
  background-image:radial-gradient(ellipse at 20% 10%,rgba(0,212,255,.05) 0%,transparent 60%),
                   radial-gradient(ellipse at 80% 80%,rgba(255,107,53,.04) 0%,transparent 60%)}
header{border-bottom:1px solid var(--border);padding:1rem 2rem;display:flex;align-items:center;gap:.8rem}
header h1{font-family:'Orbitron',sans-serif;font-size:1.2rem;font-weight:900;letter-spacing:.15em;
  color:var(--accent);text-shadow:0 0 20px rgba(0,212,255,.4)}
.dot{width:9px;height:9px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);
  animation:pulse 2s ease-in-out infinite}
.mqtt-badge{margin-left:auto;font-size:.65rem;padding:.25rem .6rem;border-radius:4px;border:1px solid;
  letter-spacing:.08em}
.mqtt-badge.ok{border-color:var(--green);color:var(--green)}
.mqtt-badge.fail{border-color:var(--accent2);color:var(--accent2)}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
main{display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;padding:1.2rem 2rem;max-width:1060px;margin:0 auto}
@media(max-width:660px){main{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--border);border-radius:8px;padding:1.2rem}
.card h2{font-family:'Orbitron',sans-serif;font-size:.7rem;letter-spacing:.2em;color:var(--dim);
  margin-bottom:1rem;text-transform:uppercase}
/* fan visual */
.fan-wrap{display:flex;flex-direction:column;align-items:center;gap:.8rem;padding:.5rem 0}
.fan-svg{width:130px;height:130px}
@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
.speed-badge{font-family:'Orbitron',sans-serif;font-size:1.5rem;font-weight:900;
  color:var(--accent);text-shadow:0 0 16px rgba(0,212,255,.5)}
/* LEDs */
.leds{display:flex;gap:.7rem;margin:.2rem 0 .6rem}
.led{width:20px;height:20px;border-radius:50%;background:#1a2030;border:1px solid var(--border);transition:all .4s}
.led.on{background:var(--accent);box-shadow:0 0 10px var(--accent),0 0 20px rgba(0,212,255,.3)}
/* mode buttons */
.mode-row{display:flex;gap:.7rem;margin-bottom:1rem}
.btn{flex:1;padding:.6rem;border:1px solid var(--border);border-radius:5px;background:transparent;
  color:var(--dim);font-family:'Orbitron',sans-serif;font-size:.68rem;letter-spacing:.1em;
  cursor:pointer;transition:all .2s}
.btn:hover{border-color:var(--accent);color:var(--accent)}
.btn.active{background:rgba(0,212,255,.1);border-color:var(--accent);color:var(--accent);
  box-shadow:0 0 10px rgba(0,212,255,.15)}
.btn.danger.active{background:rgba(255,107,53,.1);border-color:var(--accent2);color:var(--accent2);
  box-shadow:0 0 10px rgba(255,107,53,.15)}
/* speed buttons */
.speed-grid{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}
.spd{padding:.75rem;border:1px solid var(--border);border-radius:5px;background:transparent;
  color:var(--dim);font-family:'Orbitron',sans-serif;font-size:.75rem;letter-spacing:.1em;
  cursor:pointer;transition:all .2s}
.spd:hover:not(:disabled){border-color:var(--green);color:var(--green)}
.spd.active{background:rgba(0,255,136,.1);border-color:var(--green);color:var(--green);
  box-shadow:0 0 10px rgba(0,255,136,.15)}
.spd:disabled{opacity:.28;cursor:not-allowed}
/* env */
.env-grid{display:grid;grid-template-columns:1fr 1fr;gap:.6rem;margin-top:1rem}
.env-item{padding:.7rem;background:rgba(0,0,0,.3);border-radius:4px;border:1px solid var(--border)}
.env-label{font-size:.62rem;color:var(--dim);letter-spacing:.1em;text-transform:uppercase}
.env-value{font-size:1.1rem;color:var(--accent);font-family:'Orbitron',sans-serif;margin-top:.25rem}
/* logs */
.log-box{height:220px;overflow-y:auto;font-size:.72rem;line-height:1.75;color:var(--dim);
  padding:.4rem;background:rgba(0,0,0,.3);border-radius:4px;border:1px solid var(--border)}
.log-box::-webkit-scrollbar{width:3px}
.log-box::-webkit-scrollbar-thumb{background:var(--border)}
.ll{border-bottom:1px solid rgba(255,255,255,.03);padding:1px 0}
.ll.ai{color:var(--accent)}.ll.dev{color:var(--green)}.ll.mq{color:#c084fc}
</style>
</head>
<body>
<header>
  <div class="dot"></div>
  <h1>SMART FAN CONTROL</h1>
  <span class="mqtt-badge fail" id="mqttBadge">MQTT ✗</span>
</header>
<main>
  <!-- Status -->
  <div class="card">
    <h2>Fan Status</h2>
    <div class="fan-wrap">
      <svg class="fan-svg" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
        <circle cx="50" cy="50" r="7" fill="#00d4ff" opacity=".85"/>
        <g id="blades">
          <ellipse cx="50" cy="27" rx="6" ry="15" fill="#00d4ff" opacity=".6" transform="rotate(0,50,50)"/>
          <ellipse cx="50" cy="27" rx="6" ry="15" fill="#00d4ff" opacity=".6" transform="rotate(90,50,50)"/>
          <ellipse cx="50" cy="27" rx="6" ry="15" fill="#00d4ff" opacity=".6" transform="rotate(180,50,50)"/>
          <ellipse cx="50" cy="27" rx="6" ry="15" fill="#00d4ff" opacity=".6" transform="rotate(270,50,50)"/>
        </g>
      </svg>
      <div class="speed-badge" id="speedTxt">OFF</div>
      <div class="leds">
        <div class="led" id="l1"></div>
        <div class="led" id="l2"></div>
        <div class="led" id="l3"></div>
      </div>
      <small style="color:var(--dim);font-size:.65rem">ESP32 LED simulation</small>
    </div>
  </div>

  <!-- Controls -->
  <div class="card">
    <h2>Controls</h2>
    <div class="mode-row">
      <button class="btn active" id="btnM" onclick="setMode('MANUAL')">MANUAL</button>
      <button class="btn danger"  id="btnA" onclick="setMode('AUTO')">AUTO (AI)</button>
    </div>
    <div class="speed-grid">
      <button class="spd active" id="s-OFF"    onclick="setSpeed('OFF')">OFF</button>
      <button class="spd"        id="s-LOW"    onclick="setSpeed('LOW')">LOW</button>
      <button class="spd"        id="s-MEDIUM" onclick="setSpeed('MEDIUM')">MEDIUM</button>
      <button class="spd"        id="s-HIGH"   onclick="setSpeed('HIGH')">HIGH</button>
    </div>
    <div class="env-grid">
      <div class="env-item">
        <div class="env-label">Temperature</div>
        <div class="env-value" id="envT">—</div>
      </div>
      <div class="env-item">
        <div class="env-label">Hour</div>
        <div class="env-value" id="envH">—</div>
      </div>
    </div>
  </div>

  <!-- Logs -->
  <div class="card" style="grid-column:1/-1">
    <h2>System Logs</h2>
    <div class="log-box" id="logBox"></div>
  </div>
</main>

<script>
const SPEEDS=["OFF","LOW","MEDIUM","HIGH"];
const spinClass={OFF:"",LOW:"spinning-slow",MEDIUM:"spinning-med",HIGH:"spinning-fast"};

// inject keyframes once
const ks=document.createElement("style");
ks.textContent=`
  .spinning-slow {animation:spin 2s linear infinite}
  .spinning-med  {animation:spin 0.9s linear infinite}
  .spinning-fast {animation:spin 0.35s linear infinite}
  @keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
`;
document.head.appendChild(ks);

function lc(line){
  if(line.includes("[AUTO-AI]")||line.includes("Coordinator")||line.includes("Agent")) return "ai";
  if(line.includes("[DEVICE]")) return "dev";
  if(line.includes("MQTT")||line.includes("Published")) return "mq";
  return "";
}
function updateFan(speed){
  const b=document.getElementById("blades");
  b.className=spinClass[speed]||"";
  document.getElementById("speedTxt").textContent=speed;
  const n={OFF:0,LOW:1,MEDIUM:2,HIGH:3}[speed]??0;
  [1,2,3].forEach(i=>document.getElementById("l"+i).classList.toggle("on",i<=n));
}
async function poll(){
  try{
    const d=await (await fetch("/api/state")).json();
    updateFan(d.speed);
    document.getElementById("btnM").classList.toggle("active",d.mode==="MANUAL");
    document.getElementById("btnA").classList.toggle("active",d.mode==="AUTO");
    SPEEDS.forEach(s=>{
      const b=document.getElementById("s-"+s);
      b.classList.toggle("active",d.speed===s);
      b.disabled=d.mode==="AUTO";
    });
    document.getElementById("envT").textContent=d.temperature?d.temperature+"°C":"—";
    document.getElementById("envH").textContent=d.hour!==null?d.hour+"h":"—";
    const badge=document.getElementById("mqttBadge");
    badge.textContent=d.mqtt_ok?"MQTT ✓  "+d.broker:"MQTT ✗";
    badge.className="mqtt-badge "+(d.mqtt_ok?"ok":"fail");
    document.getElementById("logBox").innerHTML=
      (d.logs||[]).map(l=>`<div class="ll ${lc(l)}">${l}</div>`).join("");
  }catch(e){}
}
async function setSpeed(s){
  await fetch("/api/speed",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({speed:s})});
}
async function setMode(m){
  await fetch("/api/mode",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({mode:m})});
}
poll();setInterval(poll,2000);
</script>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────────────────────
# Flask routes
# ─────────────────────────────────────────────────────────────────────────────

app_flask = Flask(__name__)
app_flask.logger.setLevel(logging.WARNING)   # suppress Flask request noise


@app_flask.route("/")
def index():
    return render_template_string(HTML)


@app_flask.route("/api/state")
def api_state():
    with state_lock:
        return jsonify(dict(state))


@app_flask.route("/api/speed", methods=["POST"])
def api_speed():
    data  = request.get_json() or {}
    speed = data.get("speed", "").upper()
    if speed not in SPEEDS:
        return jsonify({"error": "invalid speed"}), 400
    with state_lock:
        if state["mode"] != "MANUAL":
            return jsonify({"error": "switch to MANUAL first"}), 400
    set_speed(speed, source="MANUAL-WEB")
    return jsonify({"ok": True, "speed": speed})


@app_flask.route("/api/mode", methods=["POST"])
def api_mode():
    data = request.get_json() or {}
    mode = data.get("mode", "").upper()
    if mode not in ("MANUAL", "AUTO"):
        return jsonify({"error": "invalid mode"}), 400
    with state_lock:
        state["mode"] = mode
    _log(f"Mode → {mode}")
    return jsonify({"ok": True, "mode": mode})


# ─────────────────────────────────────────────────────────────────────────────
# CLI mode
# ─────────────────────────────────────────────────────────────────────────────

CLI_HELP = """
Commands:
  off / low / medium / high  — set speed (MANUAL mode)
  auto                       — switch to AUTO (AI) mode
  manual                     — switch to MANUAL mode
  status                     — show current state
  quit / exit                — exit
"""

def cli_mode():
    print("\n=== Smart Fan Controller (CLI) ===")
    print(CLI_HELP)
    while True:
        try:
            cmd = input("fan> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting…")
            break

        if cmd in ("off", "low", "medium", "high"):
            with state_lock:
                state["mode"] = "MANUAL"
            set_speed(cmd.upper(), source="MANUAL-CLI")
        elif cmd == "auto":
            with state_lock:
                state["mode"] = "AUTO"
            _log("Mode → AUTO")
        elif cmd == "manual":
            with state_lock:
                state["mode"] = "MANUAL"
            _log("Mode → MANUAL")
        elif cmd == "status":
            with state_lock:
                s = dict(state)
            print(f"  mode={s['mode']}  speed={s['speed']}  "
                  f"temp={s['temperature']}  hour={s['hour']}  "
                  f"mqtt={s['mqtt_ok']}")
        elif cmd in ("quit", "exit", "q"):
            break
        else:
            print("  Unknown command. Type 'off', 'low', 'medium', 'high', 'auto', 'manual', 'status', or 'quit'.")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Smart Fan Controller")
    parser.add_argument("--cli",      action="store_true", help="Run as CLI instead of web server")
    parser.add_argument("--no-mqtt",  action="store_true", help="Skip MQTT (offline demo mode)")
    parser.add_argument("--port",     type=int, default=5000, help="Web server port (default 5000)")
    args = parser.parse_args()

    # ── MQTT connection ───────────────────────────────────────────────────────
    if not args.no_mqtt:
        mqtt_client._on_message_cb = on_device_message
        try:
            mqtt_client.connect()
            with state_lock:
                state["mqtt_ok"] = True
                state["broker"]  = mqtt_client.broker_used
            _log(f"MQTT connected → {mqtt_client.broker_used}")
        except ConnectionError as e:
            _log(f"MQTT unavailable: {e}")
            _log("Running in offline mode — AI decisions work, no device communication.")
    else:
        _log("MQTT disabled (--no-mqtt flag). Running in offline demo mode.")

    # ── Background AUTO loop ──────────────────────────────────────────────────
    t = threading.Thread(target=auto_loop, daemon=True)
    t.start()

    _log("Smart Fan Controller started.")

    # ── Start interface ───────────────────────────────────────────────────────
    try:
        if args.cli:
            cli_mode()
        else:
            _log(f"Web dashboard → http://localhost:{args.port}")
            print(f"\n  Open your browser at  http://localhost:{args.port}\n")
            app_flask.run(
                host="0.0.0.0",
                port=args.port,
                debug=False,
                use_reloader=False,
            )
    except KeyboardInterrupt:
        print("\nShutting down…")

    # ── Cleanup ───────────────────────────────────────────────────────────────
    if not args.no_mqtt and mqtt_client.is_connected:
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()
