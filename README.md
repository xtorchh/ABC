# Argos + Currys Scraper Bot

Finds products with 80%+ discounts at Argos and Currys and sends them to Discord.

## Runs Every 10 Minutes on Railway

- Uses Playwright to scrape both sites
- Posts results via Discord Webhook

## Setup Locally

```bash
pip install -r requirements.txt
playwright install
python scraper_bot.py
```