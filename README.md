# Altfins Scraper

Tự động đăng nhập [Altfins](https://altfins.com/), thu thập trade setup từ trang Technical Analysis, lưu vào Supabase và gửi cảnh báo qua Telegram (hỗ trợ nhiều group).

---

## Kiến trúc

```
main.py                         # Entry point — khởi tạo dependencies & chạy pipeline
src/
├── config.py                   # Centralized config (env vars)
├── models/
│   └── trade_setup.py          # Pydantic model — data contract duy nhất
├── scraper/
│   ├── driver.py               # Headless Chrome setup
│   ├── auth.py                 # Email/password login
│   └── extractor.py            # DOM extraction (grid, popup, image)
├── parsers/
│   └── altfins_parser.py       # Parse raw text → TradeSetup, format Telegram message
├── repositories/
│   ├── base.py                 # Abstract Repository interface
│   └── supabase_repository.py  # Supabase implementation
├── notifiers/
│   ├── base.py                 # Abstract Notifier interface (Strategy pattern)
│   ├── telegram_notifier.py    # Gửi alert đến nhiều Telegram group
│   ├── discord_notifier.py     # Stub — sẵn sàng implement
│   └── email_notifier.py       # Stub — sẵn sàng implement
└── pipeline.py                 # Orchestrator: scrape → parse → save → notify
tests/
├── test_parser.py
├── test_repository.py
├── test_notifiers.py
└── test_pipeline.py
```

### Flow

```
main.py → ScrapePipeline
              ├── scraper/ (Chrome → login → extract rows/popup/image)
              ├── parsers/ (raw text → TradeSetup model)
              ├── repositories/ (find / create / update Supabase)
              └── notifiers[] (fan-out: Telegram group 1, group 2, ...)
```

### Design Patterns áp dụng

| Pattern | Áp dụng tại |
|---|---|
| **Repository** | `repositories/` — tách DB logic, dễ swap Supabase → Postgres |
| **Strategy** | `notifiers/` — thêm Discord/Email không cần sửa pipeline |
| **Pipeline** | `pipeline.py` — mỗi bước tách biệt, dễ test từng phần |
| **Dependency Injection** | `main.py` — wire dependencies vào pipeline, không có global state |

---

## Yêu cầu hệ thống

- Python 3.9+
- Google Chrome (cho Selenium)

---

## Cài đặt

```sh
# 1. Clone repo
git clone https://github.com/dangchison/altfins.git
cd altfins

# 2. Cài packages
pip install -r requirements.txt

# 3. Tạo .env từ template
cp .env.example .env
```

---

## Cấu hình `.env`

```env
# Altfins credentials
ALTFINS_ACCOUNT=your_email@example.com
ALTFINS_PASSWORD=your_password

# Supabase
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_supabase_anon_key

# Telegram — hỗ trợ nhiều group, cách nhau bởi dấu phẩy
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_IDS=-100123456,-100789012

# Số dòng scrape mỗi lần chạy (mặc định: 2)
NUM_ROWS=2
```

> **Lưu ý:** `TELEGRAM_CHAT_IDS` nhận nhiều chat ID cách nhau bởi dấu phẩy — dùng để gửi đến nhiều group Telegram cùng lúc.

---

## Chạy scraper

```sh
python main.py
```

---

## Chạy tests

```sh
python -m pytest tests/ -v
```

---

## Database Setup (Supabase)

```sql
CREATE TABLE crypto_analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date TEXT NOT NULL,
  coin TEXT NOT NULL,
  symbol TEXT NOT NULL,
  contents TEXT NOT NULL,
  image TEXT NOT NULL,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_timestamp
BEFORE UPDATE ON crypto_analysis
FOR EACH ROW
EXECUTE FUNCTION update_timestamp();
```

---

## Telegram Bot Setup

1. Mở Telegram, tìm **BotFather** và gửi `/newbot`
2. Làm theo hướng dẫn để lấy **Bot Token**
3. Thêm bot vào group, lấy chat ID qua:
   ```
   https://api.telegram.org/bot<your_token>/getUpdates
   ```
4. Điền vào `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=your_token
   TELEGRAM_CHAT_IDS=-100group1,-100group2
   ```

---

## Thêm notifier mới (Discord, Email...)

1. Tạo class mới trong `src/notifiers/`, kế thừa `BaseNotifier`
2. Implement method `send(setup: TradeSetup) -> None`
3. Đăng ký trong `main.py`:

```python
from src.notifiers.discord_notifier import DiscordNotifier

notifiers = [
    TelegramNotifier(...),
    DiscordNotifier(webhook_url="https://discord.com/api/webhooks/..."),
]
```

---

## Automation (GitHub Actions / cron-job.org)

File `.github/workflows/scrape.yml` chạy `python main.py` theo lịch cron.  
Các secret cần khai báo trong **Settings → Secrets and variables → Actions**:

| Secret | Mô tả |
|---|---|
| `ALTFINS_ACCOUNT` | Email đăng nhập Altfins |
| `ALTFINS_PASSWORD` | Password Altfins |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_KEY` | Supabase anon key |
| `TELEGRAM_BOT_TOKEN` | Token của Telegram bot |
| `TELEGRAM_CHAT_IDS` | Chat IDs cách nhau bởi dấu phẩy |

---

## Packages

| Package | Mục đích |
|---|---|
| `selenium` | Điều khiển trình duyệt |
| `webdriver-manager` | Tự động quản lý ChromeDriver |
| `requests` | HTTP calls (Telegram API) |
| `supabase` | Kết nối Supabase |
| `python-dotenv` | Load `.env` |
| `pydantic` | Data model & validation |
| `pydantic-settings` | Load config từ env vars |
| `pytest` + `pytest-mock` | Unit & integration tests |
