import os
import io
import logging
import requests
from flask import Flask, request
import telebot
from telebot import types
from PIL import Image
import pytesseract

# ===== CONFIGURATION =====
API_TOKEN = "7140415265:AAEW1So3c-z2fKiEduqsV8j9Z2uV2JWi5So"
WEBHOOK_URL = "https://telegram-bot.onrender.com"
TESSERACT_CMD = os.environ.get("TESSERACT_CMD")  # optional: path to tesseract binary

if TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

# ===== LOGGING =====
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== INIT BOT & FLASK =====
bot = telebot.TeleBot(API_TOKEN, threaded=False)
app = Flask(__name__)

# ===== MENU BUTTONS =====
def set_bot_menu():
    commands = [
        types.BotCommand("start","ចាប់ផ្ដើម"),
        types.BotCommand("contact", "ទំនាក់ទំនង"),
        types.BotCommand("about", "អំពី bot")
    ]
    bot.set_my_commands(commands)

set_bot_menu()

# ===== COMMAND HANDLERS =====
@bot.message_handler(commands=['start'])
def start_command(message):
    text = (
        "សូមស្វាគមន៍ មកកាន់ Telegram OCR Bot 📷➡️🔤\n\n"
        "Send me an image and I will extract Khmer + English text."
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['contact'])
def contact_command(message):
    text = (
        "📞 Telegram: 087727747 , 067777947\n"
        "🌐 Facebook: leang"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['about'])
def about_command(message):
    text = (
        "ការបង្កើត Telegram bot នេះឡើងក្នុងគោលបំណងជួយដល់និស្សិត។\n"
        "This bot was created to help students convert images to text."
    )
    bot.send_message(message.chat.id, text)

# ===== IMAGE HANDLER =====
@bot.message_handler(content_types=['photo', 'document'])
def ocr_image(message):
    try:
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
        else:
            if message.document.mime_type.startswith('image/'):
                file_info = bot.get_file(message.document.file_id)
            else:
                bot.reply_to(message, "សូមផ្ញើតែឯកសាររូបភាព (image)។")
                return

        downloaded = bot.download_file(file_info.file_path)
        img = Image.open(io.BytesIO(downloaded)).convert("RGB")

        # OCR Khmer + English
        text = pytesseract.image_to_string(img, lang="khm+eng", config="--psm 6")

        if text.strip():
            if len(text) <= 4000:
                bot.reply_to(message, text)
            else:
                bio = io.BytesIO(text.encode("utf-8"))
                bio.name = "ocr_result.txt"
                bot.send_document(message.chat.id, bio)
        else:
            bot.reply_to(message, "មិនអាចស្គាល់អក្សរ។ សូមផ្ញើរូបភាពច្បាស់។")
    except Exception as e:
        logger.exception(e)
        bot.reply_to(message, f"មានបញ្ហា៖ {e}")

# ===== FLASK WEBHOOK =====
@app.route(f"/webhook/{API_TOKEN}", methods=['POST'])
def webhook():
    logger.info("Webhook called!")
    json_str = request.get_data().decode("utf-8")
    logger.info(f"Update JSON: {json_str}")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def home():
    return "Telegram OCR Bot is running."

# ===== MAIN =====
if __name__ == "__main__":
    try:
        bot.remove_webhook()
        full_webhook_url = f"{WEBHOOK_URL}/webhook/{API_TOKEN}"
        result = bot.set_webhook(url=full_webhook_url)
        logger.info(f"Setting webhook to {full_webhook_url} -> {result}")

        # Force setWebhook via Telegram API (debug)
        resp = requests.get(
            f"https://api.telegram.org/bot{API_TOKEN}/setWebhook",
            params={"url": full_webhook_url}
        )
        logger.info(f"Telegram API setWebhook response: {resp.text}")

        # Check webhook info
        info = requests.get(
            f"https://api.telegram.org/bot{API_TOKEN}/getWebhookInfo"
        ).text
        logger.info(f"Webhook info: {info}")
    except Exception as e:
        logger.exception(f"Failed to set webhook: {e}")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

