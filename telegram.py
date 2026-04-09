import requests
import os
import re
import html
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def parse_trade_setup(raw_text, coin_symbol="N/A", date_str="N/A"):
    data = {
        "coin": coin_symbol,
        "date": date_str,
        "setup": "N/A",
        "pattern": "N/A",
        "s_trend": "N/A",
        "m_trend": "N/A",
        "l_trend": "N/A",
        "momentum": "N/A",
        "support": "N/A",
        "resistance": "N/A"
    }
    
    if not raw_text:
        return data

    # 1. Setup — coin/date are injected directly from the table, no need to parse them here
    match = re.search(r'Trade setup:\s*(.*?)(?=\nPattern:|$)', raw_text, re.IGNORECASE | re.DOTALL)
    if match:
        setup_text = match.group(1).strip()
        
        # Remove educational and advertising phrases injected by Altfins
        setup_text = re.sub(r'\(Set a price alert\)\.?', '', setup_text, flags=re.IGNORECASE).strip()
        setup_text = re.sub(r'Learn to trade.*?\.', '', setup_text, flags=re.IGNORECASE).strip()
        setup_text = re.sub(r'We also issued.*?\.', '', setup_text, flags=re.IGNORECASE).strip()
        setup_text = re.sub(r'Read here\.', '', setup_text, flags=re.IGNORECASE).strip()
        setup_text = re.sub(r'Read our research.*?\.', '', setup_text, flags=re.IGNORECASE).strip()
        setup_text = re.sub(r'USDe has a market capitalization.*?USDT\.', '', setup_text, flags=re.IGNORECASE | re.DOTALL).strip()
        data["setup"] = setup_text.strip()
        
    # 2. Pattern — extract only the pattern name from the first sentence
    pattern_match = re.search(r'Pattern:\s*(.*?)(?=\nTrend:|$)', raw_text, re.IGNORECASE | re.DOTALL)
    if pattern_match:
        pattern_text = pattern_match.group(1).strip()
        first_sentence = pattern_text.split('.')[0]
        p_name = re.sub(r'Price is trading in a\s*', '', first_sentence, flags=re.IGNORECASE)
        p_name = re.sub(r'Price is\s*', '', p_name, flags=re.IGNORECASE)
        p_name = re.sub(r'(?i)pattern', '', p_name).strip()
        data["pattern"] = p_name.strip()
        
    # 3. Trend — extract short, medium and long-term directions
    trend_match = re.search(r'Trend:\s*Short-term trend is\s*(.*?), Medium-term trend is\s*(.*?), Long-term trend is\s*(.*?)\.', raw_text, re.IGNORECASE)
    if trend_match:
        data["s_trend"] = trend_match.group(1).strip()
        data["m_trend"] = trend_match.group(2).strip()
        data["l_trend"] = trend_match.group(3).strip()

    # 4. Momentum & RSI — split into two separate fields
    data["rsi"] = "N/A"
    m_match = re.search(r'Momentum(?: is|:)?\s*(.*?)(?=\nSupport and Resistance:|$)', raw_text, re.IGNORECASE | re.DOTALL)
    if m_match:
        mom_full = m_match.group(1).strip()
        # Find the sentence that contains the RSI reading
        rsi_match = re.search(r'([^.]*RSI.*?(?:\.|\)|$))', mom_full, re.IGNORECASE)
        if rsi_match:
            rsi_text = rsi_match.group(1).strip()
            # Keep only the numeric threshold range in parentheses: (RSI > 30 and RSI < 70)
            rsi_range = re.search(r'\([^)]*RSI[^)]*\)', rsi_text, re.IGNORECASE)
            data["rsi"] = rsi_range.group(0).strip() if rsi_range else rsi_text
            
            # Remove the RSI sentence to isolate the MACD/Momentum assertion
            pure_mom = mom_full.replace(rsi_match.group(0), '').strip()
            
            # Strip leftover punctuation characters
            pure_mom = pure_mom.strip(' ._,;-')
            # Keep only the first sentence — the high-level summary; do not fabricate words
            first_sentence = pure_mom.split('.')[0].strip() if pure_mom else ""
            # If Altfins provides no MACD assertion, mark as N/A rather than guessing
            data["momentum"] = first_sentence.capitalize() if first_sentence else "N/A"
        else:
            data["momentum"] = mom_full.strip(' ._,;-').capitalize()

    # 5. Support and Resistance — use newline as stop anchor to avoid breaking on decimal dots
    sr_match = re.search(r'Support and Resistance:\s*Nearest Support Zone is\s*(.*?)\.\s*Nearest Resistance Zone is\s*(.*?)(?:\n|$)', raw_text, re.IGNORECASE | re.DOTALL)
    if sr_match:
        data["support"] = sr_match.group(1).strip()
        data["resistance"] = sr_match.group(2).strip()
    else:
        s_match = re.search(r'Nearest Support Zone is\s*(.*?)(?:\n|$)', raw_text, re.IGNORECASE)
        r_match = re.search(r'Nearest Resistance Zone is\s*(.*?)(?:\n|$)', raw_text, re.IGNORECASE)
        if s_match: data["support"] = s_match.group(1).strip().strip('.')
        if r_match: data["resistance"] = r_match.group(1).strip().strip('.')

    return data

def momentum_icon(momentum_text):
    """Map Altfins momentum keywords to a signal icon. No words are fabricated."""
    t = momentum_text.lower()
    if "strongly bullish" in t:
        return "✅"  # Strong trend — safe to hold position
    if "bullish" in t and "inflect" in t:
        return "⚠️"  # Caution — momentum may be reversing
    if "bullish" in t:
        return "📈"  # Bullish
    if "strongly bearish" in t:
        return "🔴"  # Strong downtrend
    if "bearish" in t and "inflect" in t:
        return "👀"  # Watch for potential bullish reversal
    if "bearish" in t:
        return "📉"  # Bearish
    return ""  # No clear signal — do not assign an icon

def trend_icon(trend_text):
    """Map Altfins trend values to a colored directional icon."""
    t = trend_text.lower().strip()
    if "strong up" in t:   return "🟢⬆️"
    if "up" in t:          return "🟢↗️"
    if "strong down" in t: return "🔴⬇️"
    if "down" in t:        return "🔴↘️"
    return "⚪➡️"  # Neutral / Sideways

# Template 1: Detailed Single Coin Message
def format_detailed_message(parsed_data):
    # Escape raw data so Telegram HTML parse_mode does not break on < > characters (e.g. RSI < 70)
    e = {k: html.escape(str(v)) for k, v in parsed_data.items()}
    return f"""🚀 <b>#{e['coin']}</b> Trade Setup | <i>{e['date']}</i>

📝 <b>Setup:</b> {e['setup']}
📊 <b>Pattern:</b> {e['pattern']}
📈 <b>Trend:</b> S {trend_icon(parsed_data['s_trend'])} | M {trend_icon(parsed_data['m_trend'])} | L {trend_icon(parsed_data['l_trend'])}
⏱ <b>Momentum:</b> {momentum_icon(parsed_data['momentum'])} {e['momentum']}
⚡ <b>RSI:</b> {e.get('rsi', 'N/A')}
🛡 <b>Support:</b> {e['support']}
⚔️ <b>Resistance:</b> {e['resistance']}"""

def send_telegram_message(text, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
        
    response = requests.post(url, data=payload)
    result = response.json()
    if not result.get("ok"):
        print(f"⚠️ Telegram Error (Message): {result}")
    return result

def send_telegram_photo(photo_url, caption="", parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    payload = {
        "chat_id": CHAT_ID,
        "photo": photo_url,
        "caption": caption
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
        
    response = requests.post(url, data=payload)
    result = response.json()
    if not result.get("ok"):
        print(f"⚠️ Telegram Error (Photo): {result}")
    return result