import asyncio
import logging
import aiohttp
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

async def send_to_discord(message: str):
    async with aiohttp.ClientSession() as session:
        json_data = {"content": message}
        async with session.post(DISCORD_WEBHOOK_URL, json=json_data) as resp:
            if resp.status == 204 or resp.status == 200:
                logging.info("Sent message to Discord")
            else:
                logging.error(f"Failed to send to Discord: {resp.status} - {await resp.text()}")

async def scrape_currys(page):
    url = "https://www.currys.co.uk/gbuk/epic-deals.html"
    logging.info("Navigating to Currys Epic Deals page...")
    await page.goto(url)

    logging.info("Waiting for .product-item-element selector")
    await page.wait_for_selector(".product-item-element")

    products = await page.query_selector_all(".product-item-element")
    logging.info(f"Found {len(products)} products")

    deals = []
    for product in products:
        # Adjust selectors if needed based on actual HTML structure
        title = await product.query_selector_eval("h3", "el => el.textContent.trim()").catch(lambda e: "")
        price = await product.query_selector_eval(".price", "el => el.textContent.trim()").catch(lambda e: "")
        save = await product.query_selector_eval(".save", "el => el.textContent.trim()").catch(lambda e: "N/A")

        deal_str = f"**{title}** | Price: {price} | Save: {save}"
        deals.append(deal_str)

    if deals:
        for deal in deals:
            await send_to_discord(deal)
    else:
        logging.info("No deals found")
        await send_to_discord("No deals found on Currys Epic Deals page.")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await scrape_currys(page)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())