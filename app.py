from flask import Flask, jsonify
import threading
import json
import os
import paho.mqtt.client as mqtt

app = Flask(__name__)
DATA_FILE = "data.json"
MQTT_BROKER = "broker.emqx.io"
MQTT_TOPIC = "bike/#"   # All bike data (lock + location)

# MQTT callback
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
    except Exception as e:
        print("JSON error:", e)
        data = {"value": msg.payload.decode()}

    # Message meta info: topic + timestamp
    record = {
        "topic": msg.topic,
        "payload": data
    }

    # Append new data to list
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            try:
                old_data = json.load(f)
            except:
                old_data = []
    else:
        old_data = []

    old_data.append(record)

    with open(DATA_FILE, "w") as f:
        json.dump(old_data, f)

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
