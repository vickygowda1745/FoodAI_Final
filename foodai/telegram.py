import os
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def format_telegram_message(data: dict) -> str:
    food = data.get("food", "Unknown Food")
    confidence = data.get("confidence", "N/A")
    cuisine = data.get("cuisine", "N/A")

    nutrition = data.get("nutrition", {})
    if not isinstance(nutrition, dict):
        nutrition = {}

    calories = nutrition.get("calories", "N/A")
    protein = nutrition.get("protein", "N/A")
    carbs = nutrition.get("carbs", "N/A")
    fat = nutrition.get("fat", "N/A")
    fiber = nutrition.get("fiber", "N/A")

    timestamp = data.get("timestamp", "N/A")
    lat = data.get("latitude")
    lng = data.get("longitude")

    if lat is not None and lng is not None and lat != "" and lng != "":
        osm_link = f"https://www.openstreetmap.org/?mlat={lat}&mlon={lng}#map=16/{lat}/{lng}"
    else:
        osm_link = "Location not provided"

    message = (
        f"🍽 <b>FOODAI SCAN</b>\n\n"
        f"<b>Food:</b> {food}\n"
        f"<b>Confidence:</b> {confidence}\n"
        f"<b>Cuisine:</b> {cuisine}\n\n"
        f"<b>Estimated nutrition</b>\n\n"
        f"<b>Calories:</b> {calories}\n"
        f"<b>Protein:</b> {protein}\n"
        f"<b>Carbs:</b> {carbs}\n"
        f"<b>Fat:</b> {fat}\n"
        f"<b>Fiber:</b> {fiber}\n\n"
        f"<b>Time:</b> {timestamp}\n\n"
        f"<b>OpenStreetMap location:</b>\n{osm_link}"
    )
    return message


def send_telegram_notification(data: dict) -> bool:
    token = os.getenv("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN)
    chat_id = os.getenv("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)

    if not token or not chat_id:
        print("[Telegram Error] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing.")
        return False

    text_content = format_telegram_message(data)
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text_content,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"[Telegram Error] Request failed: {e}")
        return False