from flask import Flask, request, render_template, jsonify, send_from_directory
from io import BytesIO
from PIL import Image
import threading
import os

app = Flask(__name__)

# --- Config ---
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

commands = {}
last_results = {}

MODEL = None
model_lock = threading.Lock()

def analyze_image(image_bytes):
    # TODO: replace with your real model inference
    # For now return dummy result
    return {
        "crop_type": "unknown",
        "status": "not trained yet",
        "confidence": 0.0
    }

@app.route("/")
def index():
    pi_id = request.args.get("pi_id", "AGROD1")
    return render_template("index.html",
                           pi_id=pi_id,
                           last_result=last_results.get(pi_id),
                           command=commands.get(pi_id, "IDLE"))

@app.route("/api/set_command", methods=["POST"])
def set_command():
    data = request.get_json()
    pi_id = data.get("pi_id", "AGROD1")
    command = data.get("command", "IDLE")
    commands[pi_id] = command
    return jsonify({"status": "ok", "pi_id": pi_id, "command": command})

@app.route("/api/command")
def get_command():
    pi_id = request.args.get("pi_id", "AGROD1")
    return jsonify({"command": commands.get(pi_id, "IDLE")})

@app.route("/api/upload", methods=["POST"])
def upload():
    pi_id = request.form.get("pi_id", "AGROD1")
    file = request.files.get("image")
    if not file:
        return jsonify({"ok": False, "error": "No image"}), 400

    # Save latest image for this pi
    filename = f"{pi_id}_last.jpg"
    save_path = os.path.join(UPLOAD_DIR, filename)
    file.save(save_path)

    # Run analyze (reads saved bytes)
    with open(save_path, "rb") as f:
        image_bytes = f.read()
    with model_lock:
        result = analyze_image(image_bytes)

    last_results[pi_id] = result
    commands[pi_id] = "IDLE"

    return jsonify({"ok": True, "pi_id": pi_id, "result": result})

@app.route("/api/last_result")
def last_result():
    pi_id = request.args.get("pi_id", "AGROD1")
    return jsonify({"pi_id": pi_id, "result": last_results.get(pi_id)})

@app.route("/last_image/<pi_id>")
def last_image(pi_id):
    filename = f"{pi_id}_last.jpg"
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        # optional placeholder 1x1 transparent gif or return 404
        return ("", 404)
    # serve without caching (so client always gets latest)
    response = send_from_directory(UPLOAD_DIR, filename)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)

