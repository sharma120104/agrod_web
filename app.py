from flask import Flask, request, render_template, jsonify
from io import BytesIO
from PIL import Image
import threading

app = Flask(__name__)

commands = {}
last_results = {}

MODEL = None
model_lock = threading.Lock()

def analyze_image(image_bytes):
    img = Image.open(BytesIO(image_bytes)).convert("RGB")

    # TEMP output (we will replace with real ML later)
    return {
        "crop_type": "unknown",
        "status": "not trained yet",
        "confidence": 0.0
    }

@app.route("/")
def index():
    pi_id = request.args.get("pi_id", "AGROD1")
    return render_template("index.html", pi_id=pi_id,
                           last_result=last_results.get(pi_id),
                           command=commands.get(pi_id, "IDLE"))

@app.route("/api/set_command", methods=["POST"])
def set_command():
    data = request.get_json()
    pi_id = data["pi_id"]
    command = data["command"]
    commands[pi_id] = command
    return jsonify({"status": "ok"})

@app.route("/api/command")
def get_command():
    pi_id = request.args.get("pi_id")
    return jsonify({"command": commands.get(pi_id, "IDLE")})

@app.route("/api/upload", methods=["POST"])
def upload():
    pi_id = request.form["pi_id"]
    image = request.files["image"]

    with model_lock:
        result = analyze_image(image.read())

    last_results[pi_id] = result
    commands[pi_id] = "IDLE"
    return jsonify({"result": result})

if __name__ == "__main__":
    app.run()
