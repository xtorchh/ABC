import asyncio
import logging
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright
import aiohttp
import os

# === CONFIGURATION ===
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"  # 🔁 Replace with your webhook

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def send_screenshot_to_discord(file_path, webhook_url):
    try:
        with open(file_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("file", f, filename="screenshot.png", content_type="image/png")

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, data=data) as resp:
                    if resp.status != 204:
                        logger.error(f"[ERROR] Discord upload failed: {resp.status}")
                    else:
                        logger.info("[INFO] Screenshot sent to Discord")
    except Exception as e:
        logger.exception(f"[ERROR] Failed to send to Discord: {e}")


async def send_text_to_discord(content):
    try:
        async with aiohttp.ClientSession() as session:
            payload = {"content": content}
            async with session.post(DISCORD_WEBHOOK_URL, json=payload) as resp:
                if resp.status != 204:
                    logger.error(f"[ERROR] Discord webhook failed: {resp.status}")
                else:
                    logger.info("[INFO] Sent message to Discord")
    except Exception as e:
        logger.exception(f"[ERROR] Failed to send to Discord: {e}")


async def scrape_currys(page):
    logger.info("Navigating to Currys Epic Deals page...")
    await page.goto("https://www.currys.co.uk/epic-deals", timeout=60000)
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(5)  # Ensure dynamic content loads

    # Screenshot for debugging after load
    await page.screenshot(path="debug_after_load.png", full_page=True)

    selector = ".product-item-element"
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        logger.debug(f"Waiting for {selector} elements, attempt {attempt}")
        try:
            await page.wait_for_selector(selector, timeout=5000)
            break
        except Exception:
            logger.warning(f"[DEBUG] Timeout on attempt {attempt}: {selector} not found")
    else:
        filename = f"screenshot_fail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await page.screenshot(path=filename, full_page=True)
        logger.error(f"No {selector} elements found after {max_attempts} attempts. Screenshot saved to {filename}")
        await send_screenshot_to_discord(filename, DISCORD_WEBHOOK_URL)
        return []

    # Scrape items
    product_cards = await page.query_selector_all(selector)
    logger.info(f"Found {len(product_cards)} product elements")

    deals = []

    for card in product_cards:
        try:
            title = await card.query_selector_eval("h3, .product-title", "el => el.innerText")  # Fallback tag
            price_now = await card.inner_text()
            if "Save £" in price_now or "save £" in price_now:
                deals.append(f"**{title.strip()}**\n{price_now.strip()}")
        except Exception as e:
            logger.warning(f"Failed parsing a product: {e}")

    return deals


async def main():
    logger.info("Starting scraper...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        deals = await scrape_currys(page)
        await browser.close()

        if deals:
            for deal in deals:
                await send_text_to_discord(deal)
        else:
            await send_text_to_discord("No qualifying deals found.")
            logger.info("No qualifying deals found.")


if __name__ == "__main__":
    asyncio.run(main())