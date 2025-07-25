# Argos + Currys Scraper Bot (Railway Compatible)

Finds UK products with 80%+ discounts at Argos and Currys, then posts to a Discord webhook.

## Features
- Scrapes Argos & Currys clearance sections
- Uses Playwright with headless Chromium
- Sends deals (80%+ off) to Discord via webhook
- Runs automatically every 10 minutes on Railway

## Setup Locally

```bash
pip install -r requirements.txt
python install_playwright.py
python scraper_bot.py
```