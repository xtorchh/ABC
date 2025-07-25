import asyncio
import logging
import os
from datetime import datetime

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import aiohttp

# ========== CONFIG ==========
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/your_webhook_here"
CURRYS_URL = "https://www.currys.co.uk/epic-deals"
DISCOUNT_THRESHOLD = 70  # %
MAX_ATTEMPTS = 3
TIMEOUT_MS = 15000
# ============================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_to_discord(content):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_WEBHOOK_URL, json={"content": content}) as resp:
                if resp.status != 204:
                    logger.error(f"[ERROR] Discord webhook failed: {resp.status}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to send to Discord: {e}")

async def scrape_currys(page):
    logger.info("Navigating to Currys Epic Deals page...")
    await page.goto(CURRYS_URL)

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            logger.debug(f"Waiting for .product-item-element elements, attempt {attempt}")
            await page.wait_for_selector(".product-item-element", timeout=TIMEOUT_MS)
            break
        except PlaywrightTimeoutError:
            logger.warning(f"[DEBUG] Timeout on attempt {attempt}: .product-item-element not found")
            if attempt == MAX_ATTEMPTS:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"screenshot_fail_{timestamp}.png"
                await page.screenshot(path=screenshot_path)
                logger.error(f"No product-item-element elements found after {MAX_ATTEMPTS} attempts. Screenshot saved to {screenshot_path}")
                await send_to_discord(f"❌ Currys scraper failed to find products. Screenshot saved as `{screenshot_path}`.")
                return []

    elements = await page.query_selector_all(".product-item-element")
    deals = []

    for el in elements:
        try:
            price_el = await el.query_selector(".value")
            save_el = await el.query_selector("span.saving")

            if not price_el or not save_el:
                continue

            price_text = await price_el.inner_text()
            save_text = await save_el.inner_text()

            price = float(price_text.replace("£", "").strip())
            save = float(save_text.replace("Save £", "").strip())

            if price <= 0:
                continue

            discount = round((save / (price + save)) * 100)

            if discount >= DISCOUNT_THRESHOLD:
                title_el = await el.query_selector("h3")
                title = await title_el.inner_text() if title_el else "Unnamed Product"
                deal_text = f"💥 **{title}**\nPrice: £{price:.2f} | Save: £{save:.2f} ({discount}% OFF)"
                deals.append(deal_text)

        except Exception as e:
            logger.warning(f"[WARN] Skipping product due to error: {e}")
            continue

    return deals

async def main():
    logger.info("Starting scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        deals = await scrape_currys(page)

        if deals:
            message = f"📦 **{len(deals)} Epic Deals 70%+ Found on Currys**:\n\n" + "\n\n".join(deals[:10])
            await send_to_discord(message)
        else:
            logger.info("No qualifying deals found.")
            await send_to_discord("❌ No qualifying 70%+ deals found.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())