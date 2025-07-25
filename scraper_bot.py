import asyncio
import logging
from datetime import datetime
import aiohttp
from playwright.async_api import async_playwright

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")

async def send_screenshot_to_discord(filepath: str, message: str):
    async with aiohttp.ClientSession() as session:
        with open(filepath, "rb") as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=filepath)
            data.add_field('content', message)
            async with session.post(WEBHOOK_URL, data=data) as resp:
                if resp.status != 204 and resp.status != 200:
                    logging.error(f"Failed to send screenshot to Discord: HTTP {resp.status}")
                else:
                    logging.info("Screenshot sent to Discord")

async def scrape_currys(page):
    try:
        logging.info("Waiting for .product-item-element selector")
        await page.wait_for_selector(".product-item-element", timeout=30000)
        products = await page.query_selector_all(".product-item-element")
        logging.info(f"Found {len(products)} products")
        # Here you could parse the product info and send to Discord if you want.
        if not products:
            logging.info("No qualifying deals found.")
    except Exception as e:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshot_fail_{timestamp}.png"
        await page.screenshot(path=screenshot_path)
        logging.error(f"No '.product-item-element' found: {e}")
        await send_screenshot_to_discord(screenshot_path, "Failed to find products, screenshot attached.")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        logging.info("Starting Currys scraper...")
        await page.goto("https://www.currys.co.uk/epic-deals")
        await scrape_currys(page)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())