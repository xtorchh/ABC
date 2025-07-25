import asyncio
import logging
import datetime
import aiohttp
from playwright.async_api import async_playwright

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CURRYS_URL = "https://www.currys.co.uk/epic-deals"

async def send_to_discord(content, filename=None):
    async with aiohttp.ClientSession() as session:
        data = {"content": content}
        files = None
        if filename:
            with open(filename, "rb") as f:
                files = {"file": f}
            # Note: aiohttp expects files differently; simpler to send without file for now
            # If you want to send files, consider multipart/form-data or use a library like discord.py
            # For now, sending content only

        try:
            async with session.post(WEBHOOK_URL, json=data) as resp:
                if resp.status != 204 and resp.status != 200:
                    logger.error(f"[ERROR] Discord webhook failed: {resp.status}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to send to Discord: {e}")

async def scrape_currys(page):
    await page.goto(CURRYS_URL)
    deals = []

    # Wait for product elements
    attempts = 3
    for i in range(attempts):
        try:
            logger.info(f"Waiting for .product-item-element, attempt {i+1}")
            await page.wait_for_selector(".product-item-element", timeout=15000)
            break
        except Exception:
            logger.warning(f"[DEBUG] Timeout on attempt {i+1}: .product-item-element not found")
            if i == attempts - 1:
                logger.error(f"No product-item-element elements found after {attempts} attempts.")
                screenshot_path = f"screenshot_fail_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_path)
                await send_to_discord(f"❌ No product items found on Currys. See screenshot attached.", filename=screenshot_path)
                return []

    products = await page.query_selector_all(".product-item-element")
    logger.info(f"Found {len(products)} product elements")

    for product in products:
        price_el = await product.query_selector(".price")
        save_el = await product.query_selector(".saving-amount")
        price_text = await price_el.inner_text() if price_el else "N/A"
        save_text = await save_el.inner_text() if save_el else "N/A"
        logger.info(f"Product price text: {price_text} | Save text: {save_text}")

        # Filter deals with 'save' or '£' in save text
        if save_text and ("save" in save_text.lower() or "£" in save_text):
            deals.append({
                "price": price_text.strip(),
                "saving": save_text.strip(),
                "html": await product.inner_html()
            })

    return deals

async def main():
    logger.info("Starting scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        deals = await scrape_currys(page)

        if deals:
            logger.info(f"Found {len(deals)} qualifying deals.")
            message = "🔥 Currys qualifying deals:\n"
            for d in deals:
                message += f"- Price: {d['price']} | Save: {d['saving']}\n"
            await send_to_discord(message)
        else:
            logger.info("No qualifying deals found.")
            await send_to_discord("No qualifying deals found on Currys Epic Deals page.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())