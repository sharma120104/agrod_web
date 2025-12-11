# app.py
from flask import Flask, request, render_template, jsonify, Response, send_from_directory
from io import BytesIO
from PIL import Image
import threading
import time
import os

app = Flask(__name__)

# Directories
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory state
commands = {}
last_results = {}
model_lock = threading.Lock()

# ---- Dummy analyze_image (keep or replace with your model inference) ----
def analyze_image(image_bytes):
    # replace this with real model code later
    return {"crop_type": "unknown", "status": "not trained yet", "confidence": 0.0}

# ===== API ROUTES =====

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

# Save uploaded file and analyze
@app.route("/api/upload", methods=["POST"])
def upload():
    pi_id = request.form.get("pi_id", "AGROD1")
    image = request.files.get("image")
    if not image:
        return jsonify({"ok": False, "error": "no image"}), 400

    filename = f"{pi_id}_last.jpg"
    path = os.path.join(UPLOAD_DIR, filename)
    image.save(path)   # save file for streaming and debugging

    # run (dummy) analyze
    with model_lock:
        result = analyze_image(open(path, "rb").read())

    last_results[pi_id] = result
    commands[pi_id] = "IDLE"
    return jsonify({"ok": True, "result": result})

@app.route("/api/last_result", methods=["GET"])
def last_result():
    pi_id = request.args.get("pi_id", "AGROD1")
    return jsonify({"pi_id": pi_id, "result": last_results.get(pi_id)})

# Serve the last saved image (for direct viewing)
@app.route("/last_image/<pi_id>")
def last_image(pi_id):
    filename = f"{pi_id}_last.jpg"
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        return ("", 404)
    return send_from_directory(UPLOAD_DIR, filename)

# ===== MJPEG STREAM (server-side) =====
def mjpeg_generator(pi_id="AGROD1", fps=2):
    """
    Generator that yields MJPEG frames from the latest file saved by the Pi.
    fps: frames per second to attempt (server will loop and send the same file if unchanged)
    """
    boundary = b"--frame\r\n"
    content_type = b"Content-Type: image/jpeg\r\n\r\n"

    filename = f"{pi_id}_last.jpg"
    path = os.path.join(UPLOAD_DIR, filename)

    delay = 1.0 / max(1, fps)
    while True:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    frame = f.read()
                yield boundary + content_type + frame + b"\r\n"
            except Exception:
                # if reading fails, just skip this iteration
                pass
        else:
            # no image yet, wait a bit
            pass
        time.sleep(delay)

@app.route("/mjpeg_stream/<pi_id>")
def mjpeg_stream(pi_id="AGROD1"):
    # default 2 fps; you can allow query param to change fps if desired
    return Response(mjpeg_generator(pi_id=pi_id, fps=2),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

# Run
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
