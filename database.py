from telegram import send_telegram_message, send_telegram_photo, parse_trade_setup, format_detailed_message
from supabase import create_client, Client
import uuid
from datetime import datetime

import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

__all__ = ['save_data_to_supabase']

def _find_existing_crypto_entry(coin, symbol, date):
  """
  Find existing entry in the database

  Args:
    coin (str): Coin name
    symbol (str): Coin symbol
    date (str): Data of the analysis

  Returns:
    dict: entry data if found, None otherwise
  """
  existing_entry = supabase.table("crypto_analysis") \
    .select("id") \
    .eq("coin", coin) \
    .eq("symbol", symbol) \
    .eq("date", date) \
    .order("updated_at", desc=True) \
    .limit(1) \
    .execute()

  return existing_entry.data[0] if existing_entry.data else None

def _update_crypto_entry(entry_id, contents, image):
  """
  Update the existing entry in the database

  Args:
    entry_id (str): Id of the entry to update
    contents (str): Content of the analysis
    image (str): Image URL

  Returns:
    bool: True if successful, False otherwise
  """
  from datetime import datetime

  result = supabase.table("crypto_analysis").update({
    "contents": contents,
    "image": image,
    "updated_at": datetime.now().isoformat()
  }).eq("id", entry_id).execute()

  return len(result.data) > 0

def _create_crypto_entry(date, coin, symbol, contents, image):
  """
  Create a new entry in the database

  Args:
    date (str): Date of the analysis
    coin (str): Coin name
    symbol (str): Coin symbol
    contents (str): Content of the analysis
    image (str): Image URL

  Returns:
    str: Id of the new entry if successful, None otherwise
  """
  import uuid
  from datetime import datetime

  current_time = datetime.now().isoformat()
  new_id = str(uuid.uuid4())

  result = supabase.table("crypto_analysis").insert({
    "id": new_id,
    "date": date,
    "coin": coin,
    "symbol": symbol,
    "contents": contents,
    "image": image,
    "created_at": current_time,
    "updated_at": current_time
  }).execute()

  return new_id if len(result.data) > 0 else None

def save_data_to_supabase(data):
  """
    Save data to Supabase

    Args:
      data (list): Data to save
  """
  for item in data:
    contents = item.get("popup_data", "")
    image = item.get("popup_image", "")
    row = item.get("table_row", [])

    if len(row) >= 4:
      date = row[1]
      symbol = row[2]
      coin = row[3]
    else:
      # Bảng chưa render kịp nên row bị rỗng []. Phải trích xuất thủ công từ nội dung popup bù vào.
      import re
      m = re.search(r'([A-Z0-9\.]+)\s*-\s*(.*?)\s*-\s*Trade setup:', contents, re.IGNORECASE)
      if m:
        symbol = m.group(1).strip()
        coin = symbol
        date = m.group(2).strip()
      else:
        symbol, coin, date = "N/A", "N/A", "N/A"

    if not coin or not symbol or not image or coin == "Asset Name" or coin == "N/A":
      print(f"❌ Doesn't found: '{coin}'('{symbol}')")
      continue

    print(f"✅ Checking: '{coin}'('{symbol}')")

    existing_entry = _find_existing_crypto_entry(coin, symbol, date)

    if existing_entry:
      entry_id = existing_entry["id"]
      _update_crypto_entry(entry_id, contents, image)
      print(f"🔄 Data for {coin}({symbol}) has been updated on {date}.")

    else:
      _create_crypto_entry(date, coin, symbol, contents, image)
      print(f"✅ New data for {coin}({symbol}) has been added on {date}.")
      
    print(f"✅ Send the messages.")

    # Lọc dữ liệu thô
    parsed_data = parse_trade_setup(contents, coin_symbol=symbol, date_str=date)
    message_text = format_detailed_message(parsed_data)
    
    # Gửi ảnh biểu đồ (caption cơ bản)
    send_telegram_photo(image, caption=f"📊 Chart for {coin} ({symbol}) - {date}")

    # Gửi thông tin gốc (tắt HTML parse_mode vì chữ thô có thể chứa dấu < > gây lỗi API)
    send_telegram_message(f"🔬 {symbol} - {date} - {contents}", parse_mode=None)
    
    # Gửi thông tin Trade Setup chi tiết (Template 1)
    send_telegram_message(message_text)