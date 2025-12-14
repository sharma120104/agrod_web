from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import requests
import os

app = Flask(__name__)

# ===============================
# PI CONFIG (DO NOT CHANGE)
# ===============================
PI_IP = "10.123.36.54"
PI_BASE = f"http://{PI_IP}:8000"
TIMEOUT = 10  # seconds

# ===============================
# DUMMY PREDICTION LOGIC
# ===============================
def predict_cotton(image):
    # Detect brown-ish pixels (holes / disease)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    brown_mask = cv2.inRange(hsv, (5, 50, 50), (20, 255, 200))
    brown_ratio = brown_mask.mean()

    if brown_ratio > 5:
        return {
            "crop": "Cotton",
            "status": "Diseased",
            "confidence": "High",
            "suggestion": "Use Imidacloprid or Neem-based pesticide"
        }
    else:
        return {
            "crop": "Cotton",
            "status": "Healthy",
            "confidence": "High",
            "suggestion": "No pesticide required"
        }

def predict_coconut(image):
    # Detect dominant color (BGR)
    avg_color = image.mean(axis=(0, 1))
    b, g, r = avg_color

    if r > 140 and g > 140:
        status = "Almost Mature"
        suggestion = "Harvest in 1–2 weeks"
    elif r > 120 and g < 120:
        status = "Mature"
        suggestion = "Ready for harvest"
    else:
        status = "Under Mature"
        suggestion = "Not ready for harvest"

    return {
        "crop": "Coconut",
        "status": status,
        "confidence": "High",
        "suggestion": suggestion
    }

# ===============================
# ROUTES
# ===============================
@app.route("/")
def index():
    return render_template("index.html", pi_ip=PI_IP)

@app.route("/pump/<state>")
def pump(state):
    try:
        requests.get(f"{PI_BASE}/pump/{state}", timeout=TIMEOUT)
        return jsonify({"pump": state})
    except Exception as e:
        return jsonify({"error": "Pi not reachable", "details": str(e)}), 500

@app.route("/capture_and_predict", methods=["POST"])
def capture_and_predict():
    try:
        data = request.get_json()
        crop_type = data.get("crop")

        # 1️⃣ Trigger capture on Pi
        requests.get(f"{PI_BASE}/capture", timeout=TIMEOUT)

        # 2️⃣ Fetch captured image from Pi
        img_resp = requests.get(f"{PI_BASE}/captured_image", timeout=TIMEOUT)
        img_array = np.frombuffer(img_resp.content, np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if image is None:
            return jsonify({"error": "Failed to decode image"}), 500

        # 3️⃣ Predict
        if crop_type == "cotton":
            result = predict_cotton(image)
        else:
            result = predict_coconut(image)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": "Prediction failed", "details": str(e)}), 500

# ===============================
# RENDER-COMPATIBLE START
# ===============================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)



