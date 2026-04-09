# Scraper Altfins

## Introduction
The **Scraper Altfins** project automates logging into [Altfins](https://altfins.com/) and collecting data from the technical analysis page, then storing it in Supabase.

## System Requirements
- Python 2 or 3 (Python 3 recommended)
- **pyenv** for managing Python versions (recommended)

## Installation
1. Install Python (if not already installed):
  ```sh
  pyenv install 3.x.x  # Replace 3.x.x with the desired Python version
  pyenv global 3.x.x
  ```

2. Install required packages:
  ```sh
  pip install -r requirements.txt
  ```

3. Copy the `.env.example` file to `.env` and fill in the necessary details:
  ```sh
  cp .env.example .env
  ```

## Database Setup
Run the following SQL command in Supabase to create the `crypto_analysis` table:
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

-- Create a trigger to update `updated_at` on changes
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

### Setting up Supabase Credentials
To connect to Supabase, you need to set up your credentials in the `.env` file:
```sh
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_key_here
```
Make sure to replace `your_supabase_url_here` and `your_supabase_key_here` with the actual values from your Supabase project.

## Telegram Bot Setup
To create a Telegram bot and integrate it with this project, follow these steps:

1. Open Telegram and search for **BotFather**.
2. Start a chat and send the command:
  ```
  /newbot
  ```
3. Follow the instructions to set up your bot and get the **Bot Token**.
4. Copy the token and add it to your `.env` file:
  ```
  TELEGRAM_BOT_TOKEN=your_bot_token_here
  ```
5. (Optional) If you want the bot to send messages to a specific chat, get the chat ID by sending a message to the bot and using the following API:
  ```sh
  https://api.telegram.org/bot<your_bot_token>/getUpdates
  ```
6. Add the chat ID to your `.env` file:
  ```
  TELEGRAM_CHAT_ID=your_chat_id_here
  ```
7. Implement the bot logic in your Python script to send updates via Telegram.

## Used Packages
This project uses the following libraries:
- `selenium` - Automates browser interactions.
- `webdriver-manager` - Manages browser drivers.
- `requests` - Sends HTTP requests.
- `supabase` - Connects to the Supabase database.
- `dotenv` - Manages environment variables from the `.env` file.

## Running the Scraper
Run the following command to start the scraper:
```sh
python scraper.py
```

## Notes
- Ensure that all required information is correctly set in the `.env` file before running.
- If you encounter missing package errors, rerun the installation command.

