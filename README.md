# Flipkart Deals Telegram Bot

A Telegram bot that scrapes deals from Flipkart and posts them to a Telegram channel with affiliate links.

## Features

- Scrapes deals from Flipkart
- Posts deals to a Telegram channel
- Converts product links to affiliate links
- Caches previously posted products to avoid duplicates
- Simple and easy to use commands

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the bot:
   - Edit `config.py` with your:
     - Telegram bot token
     - Channel ID
     - EarnKaro credentials

## Usage

1. Start the bot:
```bash
python bot.py
```

2. Available commands:
- `/start` - Start the bot
- `/post` - Post 5 random products to the channel
- `/post_count <number>` - Post specified number of products (max 10)
- `/help` - Show help message

## Project Structure

- `bot.py` - Main bot file
- `config.py` - Configuration settings
- `scraper.py` - Web scraping functionality
- `utils.py` - Utility functions
- `requirements.txt` - Project dependencies

## Requirements

- Python 3.7+
- python-telegram-bot
- requests
- beautifulsoup4 