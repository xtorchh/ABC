import asyncio
import aiohttp
from playwright.async_api import async_playwright
import logging
import os
from datetime import datetime

# ========== CONFIG ==========
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/your_webhook_here"  # Replace with your actual webhook
DEAL_THRESHOLD_PERCENT = 70  # only send deals with 70% or more discount
# ============================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_to_discord(content, file_path=None):
    data = aiohttp.FormData()
    data.add_field("content", content)
    if file_path:
        with open(file_path, "rb") as f:
            data.add_field("file", f, filename="screenshot.png", content_type="image/png")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(DISCORD_WEBHOOK_URL, data=data) as resp:
                if resp.status not in (200, 204):
                    logger.error(f"[ERROR] Discord webhook failed: {resp.status}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to send to Discord: {e}")

async def scrape_currys(page):
    url = "https://www.currys.co.uk/epic-deals"
    await page.goto(url, timeout=60000)
    try:
        await page.wait_for_selector(".ProductCard", timeout=15000)
        items = await page.query_selector_all(".ProductCard")
    except Exception:
        logger.debug("[DEBUG] Timeout: .ProductCard elements not found.")
        screenshot_path = f"screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        await page.screenshot(path=screenshot_path)
        await send_to_discord("[ERROR] Currys blocked the scraper or layout changed.", screenshot_path)
        return []

    deals = []
    for item in items:
        title_el = await item.query_selector("h2")
        price_el = await item.query_selector(".ProductCard-price")
        was_price_el = await item.query_selector(".ProductCard-wasPrice")

        if not (title_el and price_el and was_price_el):
            continue

        title = await title_el.inner_text()
        price_text = await price_el.inner_text()
        was_price_text = await was_price_el.inner_text()

        try:
            price = float(price_text.replace("£", "").replace(",", "").strip())
            was_price = float(was_price_text.replace("£", "").replace(",", "").strip())
            discount = round((was_price - price) / was_price * 100, 2)
        except ValueError:
            continue

        if discount >= DEAL_THRESHOLD_PERCENT:
            deal_text = f"**{title}**\nNow: £{price:.2f} | Was: £{was_price:.2f} (-{discount:.0f}%)\n{url}"
            deals.append(deal_text)

    return deals

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        logger.info("Scraping Currys...")
        deals = await scrape_currys(page)
        await browser.close()

        if not deals:
            logger.info("No qualifying deals found.")
            await send_to_discord("No 70%+ Currys deals found at the moment.")
        else:
            for deal in deals:
                await send_to_discord(deal)
                await asyncio.sleep(1)  # prevent rate limiting

if __name__ == "__main__":
    asyncio.run(main())

