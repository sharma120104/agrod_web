from flask import Flask, request, jsonify
import cv2
import numpy as np

app = Flask(__name__)

@app.route("/predict", methods=["POST"])
def predict():
    image_file = request.files.get("image")
    crop = request.form.get("crop")

    # ---------- SAFETY NET ----------
    if image_file is None or crop is None:
        return jsonify({
            "crop": crop if crop else "Unknown",
            "status": "Error",
            "confidence": "-",
            "suggestion": "Image or crop not received properly"
        })

    # ---------- READ IMAGE ----------
    img_array = np.frombuffer(image_file.read(), np.uint8)
    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    if image is None:
        return jsonify({
            "crop": crop.capitalize(),
            "status": "Error",
            "confidence": "-",
            "suggestion": "Invalid image"
        })

    image = cv2.resize(image, (224, 224))  # faster

    # ---------- COTTON ----------
    if crop == "cotton":
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        brown_mask = cv2.inRange(hsv, (5, 50, 50), (20, 255, 200))
        brown_ratio = brown_mask.mean()

        if brown_ratio > 5:
            status = "Diseased"
            suggestion = "Use Neem oil or Imidacloprid pesticide"
        else:
            status = "Healthy"
            suggestion = "No pesticide required"

        return jsonify({
            "crop": "Cotton",
            "status": status,
            "confidence": "High",
            "suggestion": suggestion
        })

    # ---------- COCONUT ----------
    if crop == "coconut":
        b, g, r = image.mean(axis=(0, 1))

        if r > 140 and g > 140:
            status = "Almost Mature"
            suggestion = "Harvest in 1–2 weeks"
        elif r > 120:
            status = "Mature"
            suggestion = "Ready for harvest"
        else:
            status = "Under Mature"
            suggestion = "Not ready for harvest"

        return jsonify({
            "crop": "Coconut",
            "status": status,
            "confidence": "High",
            "suggestion": suggestion
        })

    # ---------- FALLBACK ----------
    return jsonify({
        "crop": crop.capitalize(),
        "status": "Unknown",
        "confidence": "-",
        "suggestion": "Unsupported crop type"
    })




