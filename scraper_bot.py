import asyncio
import logging
import re
from playwright.async_api import async_playwright
import aiohttp

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"
MIN_SAVE_POUNDS = 20

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scrape_currys(page):
    url = "https://www.currys.co.uk/gbuk/epic-deals.html"
    logger.info(f"Navigating to Currys Epic Deals page...")
    await page.goto(url)
    await page.wait_for_selector(".product-item-element")

    products = await page.query_selector_all(".product-item-element")
    logger.info(f"Found {len(products)} products")

    deals = []
    for product in products:
        # Title
        title_el = await product.query_selector("h3")
        title = await title_el.inner_text() if title_el else "No title"

        # Price Now (current price)
        price_el = await product.query_selector(".product-price-now, .price-now")
        price_text = await price_el.inner_text() if price_el else ""
        
        price_match = re.search(r"£([\d,.]+)", price_text)
        price_val = float(price_match.group(1).replace(",", "")) if price_match else None

        # Save amount (usually "Save £XX")
        save_el = await product.query_selector(".product-price-save, .price-save")
        save_text = await save_el.inner_text() if save_el else ""
        
        logger.info(f"Product: {title} | Price Text: '{price_text}' | Save Text: '{save_text}'")

        save_match = re.search(r"£([\d,.]+)", save_text)
        save_val = float(save_match.group(1).replace(",", "")) if save_match else 0

        if save_val >= MIN_SAVE_POUNDS:
            deal_msg = f"**{title}**\nPrice: £{price_val:.2f}\nSave: £{save_val:.2f}"
            deals.append(deal_msg)

    return deals

async def send_to_discord(message):
    async with aiohttp.ClientSession() as session:
        data = {"content": message}
        async with session.post(WEBHOOK_URL, json=data) as resp:
            if resp.status != 204:
                logger.error(f"Discord webhook failed: {resp.status}")
            else:
                logger.info("Message sent to Discord")

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
            message = "🔥 Currys deals (Save £≥20):\n\n" + "\n\n".join(deals)
            await send_to_discord(message)
        else:
            await send_to_discord("No qualifying deals found.")
            logger.info("No qualifying deals found.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())