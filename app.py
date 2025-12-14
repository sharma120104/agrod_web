from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
import requests
import tempfile

app = Flask(__name__)

# PI BASE URL
PI_BASE = "http://10.123.36.54:8000"

# ---------- DUMMY PREDICTION LOGIC ----------
def predict_cotton(image):
    # detect brown-ish pixels (holes / disease)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    brown_mask = cv2.inRange(hsv, (5, 50, 50), (20, 255, 200))
    brown_ratio = brown_mask.mean()

    if brown_ratio > 5:
        return {
            "status": "Diseased",
            "confidence": "High",
            "suggestion": "Use Imidacloprid or Neem-based pesticide"
        }
    else:
        return {
            "status": "Healthy",
            "confidence": "High",
            "suggestion": "No pesticide required"
        }

def predict_coconut(image):
    # check dominant color
    avg_color = image.mean(axis=(0, 1))  # BGR
    b, g, r = avg_color

    if r > 140 and g > 140:
        return {
            "status": "Almost Mature",
            "suggestion": "Harvest in 1–2 weeks"
        }
    elif r > 120 and g < 120:
        return {
            "status": "Mature",
            "suggestion": "Ready for harvest"
        }
    else:
        return {
            "status": "Under Mature",
            "suggestion": "Not ready for harvest"
        }

# ---------- ROUTES ----------
@app.route("/")
def index():
    return render_template("index.html", pi_ip="10.123.36.54")

@app.route("/capture_and_predict", methods=["POST"])
def capture_and_predict():
    crop_type = request.json.get("crop")

    # trigger capture on Pi
    requests.get(f"{PI_BASE}/capture")

    # fetch captured image
    img_resp = requests.get(f"{PI_BASE}/captured_image")
    img_array = np.frombuffer(img_resp.content, np.uint8)
    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if crop_type == "cotton":
        result = predict_cotton(image)
        result["crop"] = "Cotton"
    else:
        result = predict_coconut(image)
        result["crop"] = "Coconut"

    return jsonify(result)

@app.route("/pump/<state>")
def pump(state):
    requests.get(f"{PI_BASE}/pump/{state}")
    return jsonify({"pump": state})




