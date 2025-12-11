from flask import Flask, request, render_template, jsonify, send_from_directory, Response
import os
import threading
import time
from io import BytesIO
from PIL import Image

app = Flask(__name__)

# ----------------------------
# Configuration / Globals
# ----------------------------
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

commands = {}       # maps pi_id -> command (e.g., "PUMP_ON", "CAPTURE", "IDLE")
last_results = {}   # maps pi_id -> analysis result dict
model_lock = threading.Lock()

# ----------------------------
# Placeholder ML inference
# ----------------------------
def analyze_image(image_bytes):
    """
    Replace this function with real ML model inference.
    image_bytes: raw bytes of the uploaded image.
    Must return a dict serializable to JSON, for example:
      {"crop_type":"cotton","status":"diseased","confidence":0.93}
    """
    # Temporary dummy output:
    return {
        "crop_type": "unknown",
        "status": "not trained yet",
        "confidence": 0.0
    }

# ----------------------------
# Web routes
# ----------------------------
@app.route("/")
def index():
    pi_id = request.args.get("pi_id", "AGROD1")
    return render_template("index.html",
                           pi_id=pi_id,
                           last_result=last_results.get(pi_id),
                           command=commands.get(pi_id, "IDLE"))

@app.route("/api/set_command", methods=["POST"])
def set_command():
    data = request.get_json(force=True)
    pi_id = data.get("pi_id", "AGROD1")
    command = data.get("command", "IDLE")
    commands[pi_id] = command
    return jsonify({"status": "ok", "pi_id": pi_id, "command": command})

@app.route("/api/command")
def get_command():
    pi_id = request.args.get("pi_id", "AGROD1")
    return jsonify({"command": commands.get(pi_id, "IDLE")})

@app.route("/api/last_result")
def api_last_result():
    pi_id = request.args.get("pi_id", "AGROD1")
    return jsonify({"pi_id": pi_id, "result": last_results.get(pi_id)})

@app.route("/api/upload", methods=["POST"])
def upload():
    """
    Endpoint for Pi to POST images:
    - form field: pi_id
    - file field: image
    Saves the image to uploads/<pi_id>_last.jpg and runs analyze_image().
    """
    pi_id = request.form.get("pi_id", "AGROD1")
    image = request.files.get("image")
    if not image:
        return jsonify({"ok": False, "error": "no image provided"}), 400

    filename = f"{pi_id}_last.jpg"
    path = os.path.join(UPLOAD_DIR, filename)
    try:
        image.save(path)
    except Exception as e:
        return jsonify({"ok": False, "error": f"save failed: {e}"}), 500

    # Run analysis (thread-safe)
    with model_lock:
        try:
            with open(path, "rb") as f:
                image_bytes = f.read()
            result = analyze_image(image_bytes)
        except Exception as e:
            result = {"error": f"analysis failed: {e}"}

    last_results[pi_id] = result
    commands[pi_id] = "IDLE"
    return jsonify({"ok": True, "result": result})

# Serve the last saved image for direct download/view
@app.route("/last_image/<pi_id>")
def last_image(pi_id):
    filename = f"{pi_id}_last.jpg"
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        return ("", 404)
    return send_from_directory(UPLOAD_DIR, filename)

# ----------------------------
# MJPEG stream built from saved file
# ----------------------------
def mjpeg_generator(pi_id="AGROD1", fps=2):
    boundary = b"--frame\r\n"
    header = b"Content-Type: image/jpeg\r\n\r\n"
    filename = f"{pi_id}_last.jpg"
    path = os.path.join(UPLOAD_DIR, filename)
    delay = 1.0 / max(1, fps)

    while True:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    frame = f.read()
                yield boundary + header + frame + b"\r\n"
            except Exception:
                # read error; skip
                pass
        else:
            # no image yet; yield a short pause
            pass
        time.sleep(delay)

@app.route("/mjpeg_stream/<pi_id>")
def mjpeg_stream(pi_id="AGROD1"):
    return Response(mjpeg_generator(pi_id=pi_id, fps=2),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

# ----------------------------
# Run (for local debugging)
# ----------------------------
if __name__ == "__main__":
    # Port 5000 is what Render expects for local testing; in production use gunicorn app:app
    app.run(host="0.0.0.0", port=5000)
