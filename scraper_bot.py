import asyncio
import logging
import aiohttp
from playwright.async_api import async_playwright
from datetime import datetime

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_to_discord(message, files=None):
    async with aiohttp.ClientSession() as session:
        json_data = {"content": message}
        try:
            async with session.post(WEBHOOK_URL, json=json_data) as resp:
                if resp.status != 204:
                    logger.error(f"Discord webhook failed: {resp.status}")
                else:
                    logger.info("Sent message to Discord")
        except Exception as e:
            logger.error(f"Failed to send to Discord: {e}")

async def scrape_currys(page):
    url = "https://www.currys.co.uk/gbuk/epic-deals.html"
    logger.info(f"Navigating to Currys Epic Deals page...")
    await page.goto(url)

    # Wait extra time for any bot checks, loading
    await page.wait_for_timeout(10000)  # 10 seconds

    try:
        await page.wait_for_selector(".product-item-element", timeout=30000)
    except Exception as e:
        logger.error(f"No '.product-item-element' found: {e}")
        await page.screenshot(path="timeout_screenshot.png")
        await send_to_discord("⚠️ Failed to find product elements on Currys page. See screenshot attached.")
        return []

    products = await page.query_selector_all(".product-item-element")
    logger.info(f"Found {len(products)} product elements")

    deals = []
    for product in products:
        title_el = await product.query_selector(".product-title")  # Update if needed
        price_el = await product.query_selector(".product-price")
        save_el = await product.query_selector(".product-save-amount")

        title = await title_el.inner_text() if title_el else "No title"
        price = await price_el.inner_text() if price_el else "No price"
        save_text = await save_el.inner_text() if save_el else ""

        # Extract save pounds from text like "Save £50"
        save_pounds = 0
        if "£" in save_text:
            try:
                save_pounds = int(save_text.split("£")[1].split()[0])
            except Exception:
                pass

        # Filter deals with save >= 20 pounds
        if save_pounds >= 20:
            deals.append(f"{title} | {price} | {save_text}")

    return deals

async def main():
    logger.info("Starting Currys scraper...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        page = await context.new_page()

        deals = await scrape_currys(page)
        if deals:
            message = "**Currys Deals:**\n" + "\n".join(deals)
            await send_to_discord(message)
        else:
            logger.info("No qualifying deals found.")
            await send_to_discord("No qualifying deals found on Currys.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())