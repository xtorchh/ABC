import asyncio
import logging
from datetime import datetime
from playwright.async_api import async_playwright
import aiohttp

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_to_discord(message, file_path=None):
    async with aiohttp.ClientSession() as session:
        data = {"content": message}
        files = {}
        if file_path:
            try:
                with open(file_path, "rb") as f:
                    files = {"file": f}
                    # Discord webhook multipart upload requires aiohttp MultipartWriter, so send file as data
                    # We'll just send message + file as multipart/form-data
                    mpwriter = aiohttp.FormData()
                    mpwriter.add_field("payload_json", '{"content": "' + message + '"}')
                    mpwriter.add_field("file", f, filename=file_path)
                    async with session.post(WEBHOOK_URL, data=mpwriter) as resp:
                        if resp.status != 204:
                            logger.error(f"Discord webhook failed with status {resp.status}")
                        else:
                            logger.info("Sent message and screenshot to Discord")
                        return
            except Exception as e:
                logger.error(f"Exception sending file to Discord: {e}")

        # fallback: just send message without file
        async with session.post(WEBHOOK_URL, json=data) as resp:
            if resp.status != 204:
                logger.error(f"Discord webhook failed with status {resp.status}")
            else:
                logger.info("Sent message to Discord")

async def scrape_currys(page):
    await page.goto("https://www.currys.co.uk/epic-deals", timeout=60000)
    await asyncio.sleep(5)  # wait for potential anti-bot page

    # Take screenshot after landing for debugging
    screenshot_path = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    await page.screenshot(path=screenshot_path)
    logger.info(f"Saved screenshot for debugging: {screenshot_path}")

    # Wait for product items
    try:
        await page.wait_for_selector(".product-item-element", timeout=15000)
    except Exception:
        logger.warning("[DEBUG] Timeout waiting for .product-item-element")
        await send_to_discord("[DEBUG] Timeout waiting for .product-item-element", screenshot_path)
        return []

    products = await page.query_selector_all(".product-item-element")
    deals = []

    for product in products:
        try:
            title_el = await product.query_selector(".product-title")
            title = (await title_el.inner_text()).strip() if title_el else "No title"

            price_el = await product.query_selector(".product-price")
            price_text = (await price_el.inner_text()).strip() if price_el else None

            save_el = await product.query_selector(".saving-amount")
            save_text = (await save_el.inner_text()).strip() if save_el else None

            if save_text and "£" in save_text:
                # Parse save amount and calculate percentage save if possible
                # Assuming save_text like "Save £70"
                save_amount = float(save_text.replace("Save £", "").strip())
                # price might be like "£200"
                price = float(price_text.replace("£", "").replace(",", "").strip()) if price_text else 0
                original_price = price + save_amount
                percent_save = (save_amount / original_price) * 100 if original_price > 0 else 0

                if percent_save >= 70:
                    deals.append({
                        "title": title,
                        "price": price_text,
                        "save": save_text,
                        "percent_save": percent_save
                    })
        except Exception as e:
            logger.error(f"Error parsing product: {e}")

    return deals

async def main():
    logger.info("Starting scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
            locale="en-GB",
            timezone_id="Europe/London",
            extra_http_headers={
                "accept-language": "en-GB,en;q=0.9"
            },
        )
        page = await context.new_page()

        logger.info("Navigating to Currys Epic Deals page...")
        deals = await scrape_currys(page)

        if not deals:
            logger.info("No qualifying deals found.")
            await send_to_discord("No qualifying deals found. See screenshot attached.", screenshot_path)
        else:
            for deal in deals:
                msg = f"**{deal['title']}**\nPrice: {deal['price']}\nSave: {deal['save']} (~{deal['percent_save']:.1f}% off)"
                await send_to_discord(msg)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())