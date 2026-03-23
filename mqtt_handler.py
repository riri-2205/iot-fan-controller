"""
mqtt_handler.py — MQTT Publisher / Subscriber
==============================================
• Compatible with paho-mqtt 1.x AND 2.x (auto-detected)
• Tries three public brokers in order — uses whichever responds first
• Topic  : fan/control
• Payload: {"device": "fan1", "speed": "HIGH"}

Run standalone to test connectivity:
    python mqtt_handler.py
"""

import json
import logging
import threading
import paho.mqtt.client as mqtt

logger = logging.getLogger("MQTT")

# Public MQTT brokers tried in order — first to respond wins
BROKERS = [
    ("test.mosquitto.org", 1883),
    ("broker.hivemq.com",  1883),
    ("broker.emqx.io",     1883),
]

TOPIC     = "fan/control"
DEVICE    = "fan1"
CLIENT_ID = "smart_fan_controller"


# ─────────────────────────────────────────────────────────────────────────────
# paho-mqtt version compatibility shim
# ─────────────────────────────────────────────────────────────────────────────

def _make_client() -> mqtt.Client:
    """
    paho-mqtt 2.0 introduced CallbackAPIVersion and made it mandatory.
    This factory handles both versions transparently.
    """
    try:
        # paho-mqtt >= 2.0
        from paho.mqtt.enums import CallbackAPIVersion
        client = mqtt.Client(
            callback_api_version=CallbackAPIVersion.VERSION1,
            client_id=CLIENT_ID,
            clean_session=True,
        )
        logger.debug("paho-mqtt v2.x — using CallbackAPIVersion.VERSION1")
    except ImportError:
        # paho-mqtt 1.x
        client = mqtt.Client(client_id=CLIENT_ID, clean_session=True)
        logger.debug("paho-mqtt v1.x")
    return client


# ─────────────────────────────────────────────────────────────────────────────
# MQTTHandler
# ─────────────────────────────────────────────────────────────────────────────

class MQTTHandler:
    def __init__(self, on_message_cb=None):
        self._on_message_cb = on_message_cb
        self._client        = _make_client()
        self._connected     = threading.Event()
        self._lock          = threading.Lock()
        self.broker_used    = None

        self._client.on_connect    = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_publish    = self._on_publish
        self._client.on_message    = self._on_message

    # ── Public API ────────────────────────────────────────────────────────────

    def connect(self, timeout: int = 12) -> None:
        """
        Try each broker in BROKERS until one connects successfully.
        Raises ConnectionError if all fail.
        """
        last_error = None
        for host, port in BROKERS:
            logger.info(f"Trying {host}:{port} …")
            self._connected.clear()
            try:
                self._client.connect_async(host, port, keepalive=60)
                self._client.loop_start()
                if self._connected.wait(timeout=timeout):
                    self.broker_used = host
                    logger.info(f"Connected to {host} ✓")
                    return
                # timed out — clean up before trying next
                logger.warning(f"Timed out on {host}")
                self._client.loop_stop()
                try:
                    self._client.disconnect()
                except Exception:
                    pass
            except Exception as e:
                last_error = e
                logger.warning(f"Error on {host}: {e}")
                try:
                    self._client.loop_stop()
                except Exception:
                    pass

        raise ConnectionError(
            f"All MQTT brokers failed. Last error: {last_error}\n"
            "Tip: run with --no-mqtt for a fully offline demo."
        )

    def disconnect(self) -> None:
        try:
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass
        logger.info("MQTT disconnected.")

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    def publish_speed(self, speed: str) -> bool:
        """Publish a fan speed command. Returns True on success."""
        if not self.is_connected:
            logger.warning("Not connected — skipping publish.")
            return False
        payload = json.dumps({"device": DEVICE, "speed": speed})
        with self._lock:
            result = self._client.publish(TOPIC, payload, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"✓ Published  topic={TOPIC}  payload={payload}")
            return True
        logger.error(f"Publish failed rc={result.rc}")
        return False

    # ── Callbacks ─────────────────────────────────────────────────────────────

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected.set()
            client.subscribe(TOPIC, qos=1)
            logger.info(f"Subscribed to {TOPIC}")
        else:
            _RC = {1: "bad protocol", 2: "bad client-id",
                   3: "broker unavailable", 4: "bad credentials", 5: "not authorised"}
            logger.error(f"Connect refused: {_RC.get(rc, rc)}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected.clear()
        if rc != 0:
            logger.warning(f"Unexpected disconnect rc={rc} (auto-reconnect active)")

    def _on_publish(self, client, userdata, mid):
        logger.debug(f"Publish ack mid={mid}")

    def _on_message(self, client, userdata, msg):
        text = msg.payload.decode(errors="replace")
        logger.info(f"[DEVICE-ECHO] {msg.topic}  →  {text}")
        try:
            data = json.loads(text)
            if self._on_message_cb:
                self._on_message_cb(data)
        except json.JSONDecodeError:
            logger.warning("Non-JSON message ignored.")


# ─────────────────────────────────────────────────────────────────────────────
# Quick connectivity self-test  (python mqtt_handler.py)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import time

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    # Show paho version
    try:
        import paho
        print(f"paho-mqtt version: {paho.__version__}")
    except Exception:
        print("paho-mqtt version: unknown")

    def _echo(data):
        print(f"  Echo received: {data}")

    h = MQTTHandler(on_message_cb=_echo)
    try:
        h.connect(timeout=12)
        print(f"Connected to: {h.broker_used}")
        print("Publishing test message (speed=LOW) …")
        h.publish_speed("LOW")
        time.sleep(3)
        print("Self-test PASSED ✓")
    except ConnectionError as e:
        print(f"Self-test FAILED: {e}")
    finally:
        h.disconnect()
