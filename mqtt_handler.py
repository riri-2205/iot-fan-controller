import json
import logging
import threading
import time
import paho.mqtt.client as mqtt

BROKER_HOST = "broker.hivemq.com"
BROKER_PORT = 1883
TOPIC_CONTROL = "iot/smartfan/control"
TOPIC_STATUS = "iot/smartfan/status"
DEVICE_ID = "fan1"

logger = logging.getLogger("mqtt_handler")

class MQTTHandler:
    def __init__(self, on_status_cb=None):
        self._on_status_cb = on_status_cb
        self._client = mqtt.Client(
            client_id=f"smartfan-app-{int(time.time())}",
            protocol=mqtt.MQTTv311
        )
        self._connected = False
        self._lock = threading.Lock()

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def connect(self, timeout=10):
        logger.info(f"Connecting to {BROKER_HOST}...")
        try:
            self._client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            self._client.loop_start()
            deadline = time.time() + timeout
            while not self._connected and time.time() < deadline:
                time.sleep(0.1)
            return self._connected
        except Exception as e:
            logger.error(f"MQTT connect failed: {e}")
            return False

    def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()

    def publish_speed(self, speed, mode="manual"):
        payload = json.dumps({
            "device": DEVICE_ID,
            "speed": speed,
            "mode": mode,
            "ts": int(time.time())
        })
        with self._lock:
            result = self._client.publish(TOPIC_CONTROL, payload, qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.info(f"Published: {payload}")
            return True
        return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            logger.info("MQTT connected!")
            client.subscribe(TOPIC_STATUS, qos=1)
        else:
            logger.error(f"Connection failed rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        logger.warning("MQTT disconnected")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received: {payload}")
            if self._on_status_cb:
                self._on_status_cb(payload)
        except Exception as e:
            logger.warning(f"Could not parse message: {e}")

    @property
    def connected(self):
        return self._connected