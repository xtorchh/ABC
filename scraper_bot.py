import asyncio
import logging
from playwright.async_api import async_playwright
import aiohttp

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/115.0.0.0 Safari/537.36"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def scrape_currys(page):
    await page.goto("https://www.currys.co.uk/epic-deals", timeout=60000)
    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            logger.info(f"Waiting for .product-item-element, attempt {attempt}")
            await page.wait_for_selector(".product-item-element", timeout=15000)
            products = await page.query_selector_all(".product-item-element")
            logger.info(f"Found {len(products)} product elements")
            deals = []
            for product in products:
                # Extract price and saving info
                price_el = await product.query_selector(".price")
                save_el = await product.query_selector(".saving-amount")
                if price_el and save_el:
                    price_text = (await price_el.inner_text()).strip()
                    save_text = (await save_el.inner_text()).strip()
                    # Only keep deals with 'save' value (you can customize filter here)
                    if "save" in save_text.lower() or "£" in save_text:
                        deals.append({
                            "price": price_text,
                            "saving": save_text,
                            "html": await product.inner_html()
                        })
            return deals
        except Exception as e:
            logger.warning(f"[DEBUG] Timeout on attempt {attempt}: {e}")
    logger.error("No product-item-element elements found after 3 attempts.")
    await page.screenshot(path="screenshot_fail.png")
    return []

async def send_to_discord(deals):
    if not deals:
        logger.info("No qualifying deals found.")
        return
    content = "**Currys Epic Deals (70% Save £ Deals)**\n"
    for deal in deals:
        content += f"Price: {deal['price']} | Save: {deal['saving']}\n"
    async with aiohttp.ClientSession() as session:
        payload = {"content": content}
        async with session.post(WEBHOOK_URL, json=payload) as resp:
            if resp.status != 204:
                text = await resp.text()
                logger.error(f"[ERROR] Discord webhook failed: {resp.status} {text}")
            else:
                logger.info("Sent message to Discord")

async def main():
    logger.info("Starting scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()
        deals = await scrape_currys(page)
        await send_to_discord(deals)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())