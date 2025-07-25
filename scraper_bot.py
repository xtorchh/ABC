import asyncio
import logging
from datetime import datetime

from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import aiohttp

# Set your Discord webhook
WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_to_discord(message: str, screenshot_path: str = None):
    data = {"content": message}
    try:
        if screenshot_path:
            with open(screenshot_path, "rb") as f:
                async with aiohttp.ClientSession() as session:
                    form_data = aiohttp.FormData()
                    form_data.add_field("file", f, filename="screenshot.png", content_type="image/png")
                    form_data.add_field("payload_json", str(data))
                    async with session.post(WEBHOOK_URL, data=form_data) as resp:
                        if resp.status != 200 and resp.status != 204:
                            logger.error(f"[ERROR] Discord webhook failed: {resp.status}")
        else:
            async with aiohttp.ClientSession() as session:
                async with session.post(WEBHOOK_URL, json=data) as resp:
                    if resp.status != 200 and resp.status != 204:
                        logger.error(f"[ERROR] Discord webhook failed: {resp.status}")
    except Exception as e:
        logger.error(f"[ERROR] Failed to send to Discord: {e}")

async def scrape_currys(page):
    logger.info("Navigating to Currys Epic Deals page...")
    await page.goto("https://www.currys.co.uk/epic-deals", timeout=60000)

    # Retry up to 3 times for selector to load
    selector = ".product-item-element"
    for attempt in range(1, 4):
        logger.debug(f"Waiting for {selector} elements, attempt {attempt}")
        try:
            await page.wait_for_selector(selector, timeout=10000)
            break
        except Exception:
            logger.warning(f"[DEBUG] Timeout on attempt {attempt}: {selector} not found")
    else:
        # Screenshot if all retries failed
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_path = f"screenshot_fail_{timestamp}.png"
        await page.screenshot(path=screenshot_path)
        logger.error(f"No {selector} elements found after 3 attempts. Screenshot saved to {screenshot_path}")
        await send_to_discord("[DEBUG] No product items found. See screenshot.", screenshot_path)
        return []

    products = await page.query_selector_all(selector)
    logger.info(f"Found {len(products)} products")

    qualifying_deals = []

    for product in products:
        try:
            title_el = await product.query_selector("h3")
            title = await title_el.inner_text() if title_el else "No Title"

            price_el = await product.query_selector(".productPrice_price")
            price_text = await price_el.inner_text() if price_el else "£0"

            saving_el = await product.query_selector(".productPrice_saving")
            saving_text = await saving_el.inner_text() if saving_el else ""

            if "save" in saving_text.lower():
                # Extract saving amount
                try:
                    save_amount = float(saving_text.lower().replace("save £", "").replace(",", "").strip())
                    current_price = float(price_text.replace("£", "").replace(",", "").strip())

                    discount_percent = (save_amount / (save_amount + current_price)) * 100

                    if discount_percent >= 70:
                        link_el = await product.query_selector("a")
                        link = await link_el.get_attribute("href")
                        qualifying_deals.append(
                            f"**{title}**\nPrice: {price_text} | Saving: {saving_text} ({discount_percent:.1f}%)\nLink: https://www.currys.co.uk{link}"
                        )
                except Exception as e:
                    logger.warning(f"[DEBUG] Could not parse discount: {e}")
        except Exception as e:
            logger.warning(f"[DEBUG] Failed to parse a product: {e}")

    return qualifying_deals

async def main():
    logger.info("Starting scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        await stealth_async(page)

        deals = await scrape_currys(page)

        if deals:
            message = f"📦 **{len(deals)} Epic Deals 70%+ Found on Currys**:\n\n" + "\n\n".join(deals)
            await send_to_discord(message)
        else:
            logger.info("No qualifying deals found.")
            await send_to_discord("❌ No qualifying 70%+ deals found.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())