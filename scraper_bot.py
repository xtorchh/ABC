import asyncio
import logging
from playwright.async_api import async_playwright
import aiohttp

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_to_discord(content):
    async with aiohttp.ClientSession() as session:
        data = {"content": content}
        async with session.post(WEBHOOK_URL, json=data) as resp:
            if resp.status != 204 and resp.status != 200:
                logger.error(f"Discord webhook failed with status {resp.status}")
            else:
                logger.info("Sent message to Discord")

async def scrape_currys(page):
    await page.goto("https://www.currys.co.uk/epic-deals")
    await page.wait_for_selector(".product-item-element")

    product_cards = await page.query_selector_all(".product-item-element")
    logger.info(f"Found {len(product_cards)} products")

    deals = []

    for card in product_cards:
        try:
            title = await card.query_selector_eval(".product-title", "el => el.textContent.trim()")
        except:
            title = "No title found"

        try:
            current_price = await card.query_selector_eval(".current-price", "el => el.textContent.trim()")
        except:
            current_price = "No current price"

        try:
            original_price = await card.query_selector_eval(".original-price", "el => el.textContent.trim()")
        except:
            original_price = None

        try:
            discount = await card.query_selector_eval(".discount-tag", "el => el.textContent.trim()")
        except:
            discount = None

        # Compose a simple deal summary
        deal_summary = f"**{title}**\nPrice Now: {current_price}"
        if original_price:
            deal_summary += f"\nWas: {original_price}"
        if discount:
            deal_summary += f"\nDiscount: {discount}"

        deals.append(deal_summary)

    return deals

async def main():
    logger.info("Starting scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        deals = await scrape_currys(page)
        await browser.close()

    if deals:
        logger.info(f"Sending {len(deals)} deals to Discord")
        for deal in deals:
            await send_to_discord(deal)
    else:
        logger.info("No deals found.")

if __name__ == "__main__":
    asyncio.run(main())