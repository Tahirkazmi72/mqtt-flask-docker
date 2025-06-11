from flask import Flask, jsonify
import threading
import json
import os
import paho.mqtt.client as mqtt

app = Flask(__name__)
DATA_FILE = "data.json"
MQTT_BROKER = "broker.emqx.io"
MQTT_TOPIC = "bike/lock"   # <-- Yahan apna MQTT topic likh do

# MQTT callback
def on_message(client, userdata, msg):
    print("Received message:", msg.topic, msg.payload)   # <-- Debug print
    try:
        data = json.loads(msg.payload)
    except:
        data = {"value": msg.payload.decode()}
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def mqtt_listen():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, 1883)
    client.subscribe(MQTT_TOPIC)
    client.on_message = on_message
    client.loop_forever()

# MQTT background thread
threading.Thread(target=mqtt_listen, daemon=True).start()

@app.route("/data")
def get_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return jsonify(json.load(f))
    return jsonify({"error": "No data"}), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
