import asyncio
import logging
import aiohttp
from playwright.async_api import async_playwright

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"
CURRYS_URL = "https://www.currys.co.uk/epic-deals"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_to_discord(content):
    async with aiohttp.ClientSession() as session:
        data = {"content": content}
        try:
            async with session.post(WEBHOOK_URL, json=data) as resp:
                if resp.status != 204 and resp.status != 200:
                    logger.error(f"Discord webhook failed with status: {resp.status}")
        except Exception as e:
            logger.error(f"Error sending to Discord: {e}")

async def scrape_all_products(page):
    await page.goto(CURRYS_URL)
    await page.wait_for_selector(".product-item-element", timeout=15000)
    products = await page.query_selector_all(".product-item-element")
    logger.info(f"Found {len(products)} products")

    messages = []
    for idx, product in enumerate(products, 1):
        price_el = await product.query_selector(".price")
        save_el = await product.query_selector(".saving-amount")

        price_text = await price_el.inner_text() if price_el else "N/A"
        save_text = await save_el.inner_text() if save_el else "N/A"

        messages.append(f"{idx}. Price: {price_text.strip()} | Save: {save_text.strip()}")

    return "\n".join(messages)

async def main():
    logger.info("Starting temp scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()

        product_message = await scrape_all_products(page)
        if product_message:
            await send_to_discord(f"📦 Currys products on page:\n{product_message}")
        else:
            await send_to_discord("No products found on Currys page.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())