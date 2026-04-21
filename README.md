# Altfins Scraper (v2.0)

Tự động đăng nhập [Altfins](https://altfins.com/), thu thập dữ liệu phân tích tiền điện tử từ nhiều nguồn (Technical Analysis, Chart Patterns, Market Highlights), lưu vào Supabase và gửi cảnh báo trực quan qua Telegram.

---

## 🌟 Tính năng mới (v2.0)

- **Đa nguồn dữ liệu**: Quét cùng lúc từ 3 mục quan trọng nhất của Altfins.
- **Dữ liệu thời gian thực**: Lấy chính xác giá hiện tại, biến động 24h và tiềm năng lợi nhuận (Profit Potential).
- **Playwright Engine**: Chuyển đổi sang Playwright giúp xử lý Shadow DOM cực tốt và tăng tốc độ quét.
- **Quản lý Session thông minh**: Tự động đồng bộ session login lên Supabase, giúp duy trì trạng thái đăng nhập lâu dài và tránh bị Altfins khóa tài khoản.
- **Cấu hình Local linh hoạt**: Tùy chọn bỏ qua đồng bộ session khi phát triển ở máy cá nhân.

---

## 🏗 Kiến trúc hệ thống

```
main.py                         # Entry point — khởi tạo dependencies & chạy pipeline
src/
├── config.py                   # Quản lý cấu hình (Environment Variables)
├── models/
│   └── trade_setup.py          # Pydantic model — hợp đồng dữ liệu thống nhất
├── scraper/
│   ├── driver.py               # Playwright setup (Headless Chrome)
│   ├── auth.py                 # Đăng nhập và quản lý trạng thái phiên
│   ├── extractor.py            # Trích xuất dữ liệu dạng bảng (Technical Analysis)
│   └── patterns_extractor.py   # Trích xuất dữ liệu dạng thẻ (Chart Patterns/Highlights)
├── parsers/
│   └── altfins_parser.py       # Phân tích văn bản & định dạng tin nhắn Telegram
├── repositories/
│   ├── base.py                 # Giao diện Repository trừu tượng
│   └── supabase_repository.py  # Triển khai lưu trữ trên Supabase
├── notifiers/
│   ├── base.py                 # Giao diện Notifier trừu tượng
│   └── telegram_notifier.py    # Gửi cảnh báo đa group Telegram
└── pipeline.py                 # Điều phối luồng: scrape → parse → save → notify
```

---

## ⚙️ Cài đặt

```sh
# 1. Clone repo
git clone https://github.com/dangchison/altfins.git
cd altfins

# 2. Cài đặt các gói phụ thuộc
pip install -r requirements.txt

# 3. Cài đặt trình duyệt cho Playwright
playwright install chromium

# 4. Tạo file cấu hình
cp .env.example .env
```

---

## 📄 Cấu hình `.env`

| Biến | Mô tả |
|---|---|
| `ALTFINS_ACCOUNT` | Email tài khoản Altfins |
| `ALTFINS_PASSWORD` | Mật khẩu tài khoản Altfins |
| `SUPABASE_URL` | Đường dẫn dự án Supabase |
| `SUPABASE_KEY` | Khóa API Anon của Supabase |
| `TELEGRAM_BOT_TOKEN` | Token từ BotFather |
| `TELEGRAM_CHAT_IDS` | Danh sách ID chat (cách nhau bởi dấu phẩy) |
| `TECHNICAL_ANALYSIS_MAX_ROWS` | Số dòng tối đa cần quét ở trang TA |
| `ENABLE_...` | Bật/Tắt quét từ các nguồn tương ứng (true/false) |
| `USE_PERSISTENT_SESSION` | `true` để đồng bộ session với Supabase, `false` để chạy local |

---

## 🗄 Database Setup (Supabase)

Sử dụng câu lệnh SQL sau để tạo bảng dữ liệu:

```sql
CREATE TABLE crypto_analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date TEXT NOT NULL,
  coin TEXT NOT NULL,
  symbol TEXT NOT NULL,
  contents TEXT NOT NULL,
  image TEXT NOT NULL,
  source_type TEXT DEFAULT 'TECHNICAL_ANALYSIS',
  pattern_name TEXT,
  interval TEXT,
  status TEXT,
  signal TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 🚀 Chạy ứng dụng

```sh
# Chạy scraper chính
python main.py

# Chạy kiểm thử
python -m pytest tests/ -v
```

---

## 🤖 GitHub Actions

Hệ thống được thiết kế để chạy tự động qua GitHub Actions. Hãy khai báo các biến trong phần **Repository Secrets** giống như trong file `.env`. 

File workflow nằm tại: `.github/workflows/scrape.yml`
