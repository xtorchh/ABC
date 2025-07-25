import asyncio
import logging
import re
from playwright.async_api import async_playwright
import aiohttp
from datetime import datetime

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"
MIN_SAVE_POUNDS = 20

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scrape_currys(page):
    url = "https://www.currys.co.uk/gbuk/epic-deals.html"
    logger.info(f"Navigating to Currys Epic Deals page...")
    await page.goto(url)

    deals = []
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Waiting for .product-item-element, attempt {attempt}")
        try:
            await page.wait_for_selector(".product-item-element", timeout=10000)
            product_elements = await page.query_selector_all(".product-item-element")
            logger.info(f"Found {len(product_elements)} product elements")
            for product in product_elements:
                # Get title
                title_el = await product.query_selector("h3")
                title = await title_el.inner_text() if title_el else "No title"

                # Get price
                price_el = await product.query_selector(".product-price-now")
                price_text = await price_el.inner_text() if price_el else ""
                price = re.findall(r"£([\d,.]+)", price_text)
                price_val = float(price[0].replace(",", "")) if price else None

                # Get save £ text
                save_el = await product.query_selector(".product-price-save")
                save_text = await save_el.inner_text() if save_el else ""
                save_match = re.findall(r"£([\d,.]+)", save_text)
                save_val = float(save_match[0].replace(",", "")) if save_match else 0

                if save_val >= MIN_SAVE_POUNDS:
                    deal = f"**{title}**\nPrice: £{price_val:.2f}\nSave: £{save_val:.2f}\n"
                    deals.append(deal)

            break  # exit attempts loop if found elements
        except Exception as e:
            logger.warning(f"[DEBUG] Timeout on attempt {attempt}: .product-item-element not found")
            if attempt == max_attempts:
                logger.error(f"No product-item-element elements found after {max_attempts} attempts.")
    return deals

async def send_to_discord(message):
    async with aiohttp.ClientSession() as session:
        data = {"content": message}
        async with session.post(WEBHOOK_URL, json=data) as resp:
            if resp.status != 204:
                logger.error(f"[ERROR] Discord webhook failed: {resp.status}")
            else:
                logger.info("Sent message to Discord")

async def main():
    logger.info("Starting Currys scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        ))
        page = await context.new_page()

        deals = await scrape_currys(page)
        if deals:
            message = "🔥 Currys qualifying deals (Save £≥20):\n\n" + "\n\n".join(deals)
            await send_to_discord(message)
            logger.info(f"Sent {len(deals)} deals to Discord.")
        else:
            await send_to_discord("No qualifying deals found.")
            logger.info("No qualifying deals found.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())