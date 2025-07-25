import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import aiohttp

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_to_discord(message: str, screenshot_path: str = None):
    async with aiohttp.ClientSession() as session:
        data = {"content": message}
        files = {}
        if screenshot_path:
            with open(screenshot_path, "rb") as f:
                file_bytes = f.read()
            files = {"file": file_bytes}
            # Note: discord.py or aiohttp webhook file upload requires multipart/form-data
            # Here, simpler approach: upload via multipart
            # We'll use aiohttp's FormData

            form = aiohttp.FormData()
            form.add_field("payload_json", '{"content": "%s"}' % message)
            form.add_field("file", file_bytes, filename="screenshot.png", content_type="image/png")
            try:
                async with session.post(WEBHOOK_URL, data=form) as resp:
                    if resp.status != 204:
                        logger.error(f"Discord webhook failed with status {resp.status}")
            except Exception as e:
                logger.error(f"Failed to send to Discord: {e}")
            return

        try:
            async with session.post(WEBHOOK_URL, json=data) as resp:
                if resp.status != 204:
                    logger.error(f"Discord webhook failed with status {resp.status}")
        except Exception as e:
            logger.error(f"Failed to send to Discord: {e}")

async def scrape_currys(page):
    url = "https://www.currys.co.uk/epic-deals"
    await page.goto(url)

    # Wait for deals container; adjust selector if needed
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(f"Waiting for .product-item-element, attempt {attempt}")
            await page.wait_for_selector(".product-item-element", timeout=15000)
            break
        except Exception:
            logger.warning(f"[DEBUG] Timeout on attempt {attempt}: .product-item-element not found")
            if attempt == max_attempts:
                screenshot_name = f"screenshot_fail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                await page.screenshot(path=screenshot_name)
                await send_to_discord(f"[ERROR] No product-item-element found after {max_attempts} attempts. See screenshot.", screenshot_name)
                return []

    products = await page.query_selector_all(".product-item-element")
    deals = []
    for product in products:
        try:
            title = await product.query_selector_eval(".product-title", "el => el.textContent.trim()")
            price_text = await product.query_selector_eval(".price", "el => el.textContent.trim()")
            save_text = await product.query_selector_eval(".save", "el => el.textContent.trim()", strict=False)  # might be missing
            # Example: Check if save_text has 70% or more
            if save_text and "70%" in save_text:
                deals.append(f"{title} - {price_text} - {save_text}")
        except Exception:
            continue
    return deals

async def main():
    logger.info("Starting scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        deals = await scrape_currys(page)
        if deals:
            message = "**Currys 70%+ Deals Found:**\n" + "\n".join(deals)
        else:
            message = "No qualifying deals found."

        await send_to_discord(message)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())