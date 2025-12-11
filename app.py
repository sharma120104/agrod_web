# app.py — fully updated FINAL VERSION
import os
import tempfile
import threading
from flask import Flask, request, render_template, jsonify, send_from_directory, make_response

# ---- Setup ----
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

commands = {}       # Stores pending commands per Pi
last_results = {}   # Stores last analysis result per Pi
model_lock = threading.Lock()


# ---- DUMMY ML MODEL (replace later) ----
def analyze_image(image_bytes):
    """
    Replace this with your real ML model.
    """
    return {
        "crop_type": "unknown",
        "status": "not trained yet",
        "confidence": 0.0
    }


# ---- FRONTEND ----
@app.route("/")
def index():
    pi_id = request.args.get("pi_id", "AGROD1")
    return render_template("index.html",
                           pi_id=pi_id,
                           last_result=last_results.get(pi_id),
                           command=commands.get(pi_id, "IDLE"),
                           refresh_interval=700)


# ---- COMMAND API ----
@app.route("/api/set_command", methods=["POST"])
def set_command():
    data = request.get_json(force=True)
    pi_id = data.get("pi_id", "AGROD1")
    cmd = data.get("command", "IDLE")
    commands[pi_id] = cmd
    return jsonify({"ok": True, "pi_id": pi_id, "command": cmd})


@app.route("/api/command")
def get_command():
    pi_id = request.args.get("pi_id", "AGROD1")
    return jsonify({"command": commands.get(pi_id, "IDLE")})


@app.route("/api/last_result")
def api_last_result():
    pi_id = request.args.get("pi_id", "AGROD1")
    return jsonify({"pi_id": pi_id, "result": last_results.get(pi_id)})


# ---- UPLOAD API (atomic save to prevent flicker) ----
@app.route("/api/upload", methods=["POST"])
def upload():
    pi_id = request.form.get("pi_id", "AGROD1")
    file = request.files.get("image")
    if not file:
        return jsonify({"ok": False, "error": "No image"}), 400

    filename = f"{pi_id}_last.jpg"

    # Atomic write
    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jpg", dir=UPLOAD_DIR)
    try:
        with os.fdopen(tmp_fd, "wb") as tmp:
            tmp.write(file.read())
        final_path = os.path.join(UPLOAD_DIR, filename)
        os.replace(tmp_path, final_path)
    except Exception as e:
        try: os.remove(tmp_path)
        except: pass
        return jsonify({"ok": False, "error": f"Save failed: {e}"}), 500

    # Run ML analysis
    with open(final_path, "rb") as f:
        image_bytes = f.read()

    with model_lock:
        result = analyze_image(image_bytes)

    last_results[pi_id] = result
    commands[pi_id] = "IDLE"

    return jsonify({"ok": True, "pi_id": pi_id, "result": result})


# ---- LAST IMAGE API (no-cache + placeholder to prevent flashing) ----
@app.route("/last_image/<pi_id>")
def last_image(pi_id):
    filename = f"{pi_id}_last.jpg"
    path = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(path):
        placeholder = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                       b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                       b"\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01"
                       b"\xe2!\xbc\x33\x00\x00\x00\x00IEND\xaeB`\x82")
        resp = make_response(placeholder)
        resp.headers["Content-Type"] = "image/png"
        resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return resp

    resp = send_from_directory(UPLOAD_DIR, filename)
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return resp


# ---- RUN LOCAL ----
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)


