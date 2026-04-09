import requests
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(text):
  url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
  payload = {
    "chat_id": CHAT_ID,
    "text": text
  }
  response = requests.post(url, data=payload)
  return response.json()

def send_telegram_photo(photo_url, caption=""):
  url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
  payload = {
    "chat_id": CHAT_ID,
    "photo": photo_url,
    "caption": caption
  }
  response = requests.post(url, json=payload)
  return response.json()