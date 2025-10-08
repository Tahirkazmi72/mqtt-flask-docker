from flask import Flask, jsonify, render_template
import threading, json, os, tempfile
import paho.mqtt.client as mqtt

app = Flask(__name__)

DATA_FILE = "data.json"
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "mbike/#"   # <-- correct for your topic

_lock = threading.Lock()
_mqtt_started = False

def atomic_write(path, obj):
    """Write JSON atomically to avoid partial file/corruption."""
    d = os.path.dirname(path) or "."
    import tempfile, os
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", dir=d, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
        os.replace(tmp, path)
    finally:
        try:
            os.remove(tmp)
        except FileNotFoundError:
            pass

def append_record(record):
    with _lock:
        data = []
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
            except Exception:
                data = []
        data.append(record)
        atomic_write(DATA_FILE, data)

def on_connect(client, userdata, flags, rc, properties=None):
    print("MQTT connected rc=", rc)
    if rc == 0:
        client.subscribe(MQTT_TOPIC, qos=1)
        print("Subscribed to", MQTT_TOPIC)
    else:
        print("Connect failed")

def on_message(client, userdata, msg):
    # DEBUG: always print what we got
    print("MSG:", msg.topic, msg.payload[:100])

    # Try JSON, else store string
    payload_text = None
    try:
        payload_text = msg.payload.decode("utf-8", errors="replace")
        data = json.loads(payload_text)
    except Exception:
        data = {"value": payload_text if payload_text is not None else str(msg.payload)}

    record = {"topic": msg.topic, "payload": data}
    append_record(record)

def mqtt_listen():
    client = mqtt.Client(protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    client.loop_forever(retry_first_connection=True)

@app.before_first_request
def start_mqtt_once():
    global _mqtt_started
    if not _mqtt_started:
        threading.Thread(target=mqtt_listen, daemon=True).start()
        _mqtt_started = True
        print("MQTT thread started")

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/data")
def get_data():
    if os.path.exists(DATA_FILE):
        with _lock:
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    return jsonify(json.load(f))
            except Exception as e:
                print("JSON read error:", e)
                return jsonify({"error": "JSON read error"}), 500
    return jsonify({"error": "No data"}), 404

if __name__ == "__main__":
    # dev run (debug=False prevents double-start)
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write("[]")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
