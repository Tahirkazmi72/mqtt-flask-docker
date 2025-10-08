from flask import Flask, jsonify, render_template, request
import threading, json, os, time, ssl
import paho.mqtt.client as mqtt

app = Flask(__name__)

# ---- Config (env se override ho sakta hai) ----
DATA_FILE   = os.getenv("DATA_FILE", "data.json")
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.emqx.io")
MQTT_PORT   = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC  = os.getenv("MQTT_TOPIC", "mbike/#")   # subscribe topic
PUB_TOPIC   = os.getenv("PUB_TOPIC", "mbike/app-test")  # test publish topic

# ---- Global MQTT client (so routes can publish) ----
mqtt_client = mqtt.Client()
mqtt_client.enable_logger()  # detailed logs in Railway "Logs"

# ---- Handlers ----
def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload)
    except Exception:
        data = {"value": msg.payload.decode(errors="ignore")}

    record = {"topic": msg.topic, "payload": data, "ts": int(time.time())}

    try:
        existing = []
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                existing = json.load(f)
        existing.append(record)
        with open(DATA_FILE, "w") as f:
            json.dump(existing, f)
    except Exception as e:
        app.logger.exception(f"write error: {e}")

def mqtt_listen():
    try:
        if MQTT_PORT == 8883:
            mqtt_client.tls_set(cert_reqs=ssl.CERT_NONE)
            mqtt_client.tls_insecure_set(True)
        mqtt_client.on_message = on_message
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.subscribe(MQTT_TOPIC)
        app.logger.info(f"MQTT connected {MQTT_BROKER}:{MQTT_PORT}, sub {MQTT_TOPIC}")
        mqtt_client.loop_forever()
    except Exception as e:
        app.logger.exception(f"MQTT loop failed: {e}")

threading.Thread(target=mqtt_listen, daemon=True).start()

# ---- Routes ----
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/data")
def get_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return jsonify(json.load(f))
        except Exception:
            return jsonify({"error": "JSON read error"}), 500
    return jsonify({"error": "No data"}), 404

# ⭐ Test publish: proves app -> MQTT broker send is working
@app.route("/send")
def send():
    msg = request.args.get("msg", "hello from app")
    topic = request.args.get("topic", PUB_TOPIC)
    payload = {"msg": msg, "at": int(time.time())}
    try:
        res = mqtt_client.publish(topic, json.dumps(payload), qos=0)
        rc = res[0] if isinstance(res, tuple) else getattr(res, "rc", 0)
        app.logger.info(f"PUB -> {topic} {payload} rc={rc}")
        ok = (rc == mqtt.MQTT_ERR_SUCCESS)
        return {"ok": ok, "topic": topic, "payload": payload, "rc": rc}, (200 if ok else 500)
    except Exception as e:
        app.logger.exception("publish failed")
        return {"ok": False, "error": str(e)}, 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
