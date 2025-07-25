import asyncio
import logging
import aiohttp
from playwright.async_api import async_playwright

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"
CURRYS_URL = "https://www.currys.co.uk/epic-deals"
MIN_SAVE_POUNDS = 20  # Updated minimum £ savings to 20

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_to_discord(content):
    async with aiohttp.ClientSession() as session:
        data = {"content": content}
        try:
            async with session.post(WEBHOOK_URL, json=data) as resp:
                if resp.status not in (200, 204):
                    logger.error(f"Discord webhook failed with status: {resp.status}")
        except Exception as e:
            logger.error(f"Error sending to Discord: {e}")

async def scrape_currys(page):
    await page.goto(CURRYS_URL)
    await page.wait_for_selector(".product-item-element", timeout=15000)
    products = await page.query_selector_all(".product-item-element")
    logger.info(f"Found {len(products)} products")

    qualifying_deals = []
    for product in products:
        price_el = await product.query_selector(".price")
        save_el = await product.query_selector(".saving-amount")
        title_el = await product.query_selector("h3")

        price_text = (await price_el.inner_text()).strip() if price_el else None
        save_text = (await save_el.inner_text()).strip() if save_el else None
        title_text = (await title_el.inner_text()).strip() if title_el else "No title"

        save_amount = 0
        if save_text and "Save £" in save_text:
            try:
                save_amount = int(save_text.replace("Save £", "").strip())
            except Exception:
                pass

        if save_amount >= MIN_SAVE_POUNDS:
            qualifying_deals.append(f"**{title_text}**\nPrice: {price_text}\n{save_text}")

    return qualifying_deals

async def main():
    logger.info("Starting Currys scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await page.set_user_agent(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )

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