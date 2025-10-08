import os
import json
import ssl
import threading
import logging
from flask import Flask, jsonify
import paho.mqtt.client as mqtt

app = Flask(__name__)

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s: %(message)s')

# ---------- Config ----------
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.emqx.io")
MQTT_PORT = int(os.getenv("MQTT_PORT", 8883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "mbike/#")
DATA_FILE = os.getenv("DATA_FILE", "/tmp/data.json")

# ---------- MQTT Handlers ----------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info(f"✅ Connected to MQTT broker {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(MQTT_TOPIC)
        logging.info(f"📡 Subscribed to topic: {MQTT_TOPIC}")
    else:
        logging.error(f"❌ MQTT connection failed, code={rc}")

def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode()
        logging.info(f"📨 Received: {msg.topic} -> {payload}")
        data = { "topic": msg.topic, "payload": payload }
        with open(DATA_FILE, "w") as f:
            json.dump(data, f)
    except Exception as e:
        logging.exception(f"Error writing message: {e}")

def mqtt_thread():
    client = mqtt.Client()
    try:
        client.tls_set(cert_reqs=ssl.CERT_NONE)
        client.tls_insecure_set(True)
        client.on_connect = on_connect
        client.on_message = on_message
        logging.info("🚀 Starting MQTT client thread...")
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_forever()
    except Exception as e:
        logging.exception(f"MQTT loop failed: {e}")

# Start MQTT thread before Flask starts
threading.Thread(target=mqtt_thread, daemon=True).start()

# ---------- Flask Routes ----------
@app.route("/")
def home():
    return "MQTT Flask App is running!"

@app.route("/data")
def get_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            logging.exception("Error reading data file")
            return jsonify({"error": "failed to read data"}), 500
    else:
        return jsonify({"error": "No data"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
