import base64
import os
from flask import Flask, jsonify, render_template, request

from foodai.nutrition import get_nutrition_info
from foodai.recognizer import recognize_food
from foodai.restaurants import get_nearby_restaurants
from foodai.telegram import send_telegram_notification

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "FoodAI Backend Service Running"})


@app.route("/api/recognize", methods=["POST"])
def recognize():
    image_bytes = None

    if "image" in request.files:
        file = request.files["image"]
        image_bytes = file.read()
    elif request.is_json:
        data = request.get_json()
        img_str = data.get("image", "")
        if "," in img_str:
            img_str = img_str.split(",")[1]
        try:
            image_bytes = base64.b64decode(img_str)
        except Exception:
            return jsonify({"error": "Invalid base64 image data"}), 400
    elif "image" in request.form:
        img_str = request.form["image"]
        if "," in img_str:
            img_str = img_str.split(",")[1]
        try:
            image_bytes = base64.b64decode(img_str)
        except Exception:
            return jsonify({"error": "Invalid base64 image data"}), 400

    if not image_bytes:
        return jsonify({"error": "No image payload provided"}), 400

    try:
        recognition_res = recognize_food(image_bytes)
        food_name = recognition_res.get("food", "Unknown Food")
        confidence = recognition_res.get("confidence", "92%")
        cuisine = recognition_res.get("cuisine", "International")

        nutrition_res = get_nutrition_info(food_name)

        return jsonify(
            {
                "status": "success",
                "food": food_name,
                "confidence": confidence,
                "cuisine": cuisine,
                "nutrition": nutrition_res,
            }
        )
    except Exception as e:
        return jsonify({"error": f"Recognition failed: {str(e)}"}), 500


@app.route("/api/restaurants", methods=["GET", "POST"])
def restaurants():
    lat = None
    lng = None

    if request.method == "POST" and request.is_json:
        data = request.get_json()
        lat = data.get("latitude") or data.get("lat")
        lng = data.get("longitude") or data.get("lng")
    else:
        lat = request.args.get("latitude") or request.args.get("lat")
        lng = request.args.get("longitude") or request.args.get("lng")

    if lat is None or lng is None:
        return jsonify({"error": "Latitude and longitude parameters are required"}), 400

    try:
        lat_float = float(lat)
        lng_float = float(lng)
    except ValueError:
        return jsonify({"error": "Latitude and longitude must be valid floating numbers"}), 400

    result = get_nearby_restaurants(lat_float, lng_float, radius_meters=15000)
    return jsonify(result)


@app.route("/api/notify", methods=["POST"])
def notify():
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON payload required"}), 400

    required_keys = ["food", "confidence", "cuisine", "nutrition"]
    for key in required_keys:
        if key not in data:
            data[key] = "N/A" if key != "nutrition" else {}

    success = send_telegram_notification(data)
    if success:
        return jsonify({"status": "success", "message": "Telegram notification delivered"})
    else:
        return jsonify({"status": "error", "message": "Failed to send Telegram message"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)