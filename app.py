from flask import Flask, jsonify, render_template
import threading
import json
import os
import paho.mqtt.client as mqtt

app = Flask(__name__)
DATA_FILE = "data.json"
MQTT_BROKER = "broker.emqx.io"
MQTT_TOPIC = "bike/#"  # Subscribe to all bike data

# MQTT message handler
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
    except Exception as e:
        print("JSON decode error:", e)
        data = {"value": msg.payload.decode()}

    record = {
        "topic": msg.topic,
        "payload": data
    }

    # Read existing data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                existing_data = json.load(f)
            except:
                existing_data = []
    else:
        existing_data = []

    # Append new record
    existing_data.append(record)

    # Write updated data
    with open(DATA_FILE, "w") as f:
        json.dump(existing_data, f)

# MQTT listener thread
def mqtt_listen():
    client = mqtt.Client()
    client.connect(MQTT_BROKER, 1883)
    client.subscribe(MQTT_TOPIC)
    client.on_message = on_message
    client.loop_forever()

# Start MQTT in background
threading.Thread(target=mqtt_listen, daemon=True).start()

# Dashboard route
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

# API route
@app.route("/data")
def get_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            try:
                return jsonify(json.load(f))
            except:
                return jsonify({"error": "JSON read error"}), 500
    else:
        return jsonify({"error": "No data"}), 404

# App start
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)




