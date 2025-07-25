import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import aiohttp
import re

# Setup logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

def parse_price(text):
    """Parse price string like '£199.99' or 'Save £70' to float."""
    if not text:
        return None
    match = re.search(r"£([\d,.]+)", text)
    if match:
        return float(match.group(1).replace(',', ''))
    return None

async def send_to_discord(content=None, file_path=None):
    async with aiohttp.ClientSession() as session:
        if file_path:
            with open(file_path, "rb") as f:
                form = aiohttp.FormData()
                form.add_field('file', f, filename=file_path)
                if content:
                    form.add_field('content', content)
                async with session.post(DISCORD_WEBHOOK, data=form) as resp:
                    if resp.status != 204 and resp.status != 200:
                        logger.error(f"[ERROR] Discord webhook failed: {resp.status}")
        else:
            json_data = {"content": content}
            async with session.post(DISCORD_WEBHOOK, json=json_data) as resp:
                if resp.status != 204 and resp.status != 200:
                    logger.error(f"[ERROR] Discord webhook failed: {resp.status}")

async def scrape_currys(page):
    url = "https://www.currys.co.uk/epic-deals"
    logger.info(f"Navigating to Currys Epic Deals page: {url}")
    await page.goto(url)
    try:
        await page.wait_for_selector(".product-item-element", timeout=45000)
    except Exception as e:
        logger.error(f"[DEBUG] Timeout waiting for .product-item-element: {e}")
        screenshot_path = f"screenshot_fail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await page.screenshot(path=screenshot_path)
        logger.error(f"Screenshot saved to {screenshot_path}")
        await send_to_discord(content="Failed to find product elements on Currys page. See screenshot.", file_path=screenshot_path)
        return []

    product_cards = await page.query_selector_all(".product-item-element")
    logger.info(f"Found {len(product_cards)} product elements.")

    deals = []

    for card in product_cards:
        title_el = await card.query_selector(".product-title")
        price_current_el = await card.query_selector(".price-now")  # Adjust selectors if needed
        save_el = await card.query_selector(".price-save")

        title = (await title_el.inner_text()).strip() if title_el else "No title"
        price_current_text = (await price_current_el.inner_text()).strip() if price_current_el else ""
        save_text = (await save_el.inner_text()).strip() if save_el else ""

        price_current = parse_price(price_current_text)
        save_amount = parse_price(save_text)

        if price_current is not None and save_amount is not None:
            price_was = price_current + save_amount
            discount_pct = round((save_amount / price_was) * 100)
        else:
            discount_pct = 0

        if discount_pct >= 70:
            deals.append({
                "title": title,
                "price_current": price_current_text,
                "save": save_text,
                "discount_pct": discount_pct,
            })

    return deals

async def main():
    logger.info("Starting scraper...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()

        deals = await scrape_currys(page)

        if deals:
            msg = "**Currys Deals (≥70% off):**\n"
            for d in deals:
                msg += f"- {d['title']}\n  Price: {d['price_current']} | Save: {d['save']} | Discount: {d['discount_pct']}%\n"
            await send_to_discord(content=msg)
            logger.info("Sent qualifying deals to Discord.")
        else:
            logger.info("No qualifying deals found.")
            await send_to_discord(content="No qualifying deals found on Currys at 70% or more discount.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())