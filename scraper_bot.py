import asyncio
import logging
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import aiohttp
import datetime

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_to_discord(message, image_path=None):
    async with aiohttp.ClientSession() as session:
        data = {"content": message}
        if image_path:
            with open(image_path, "rb") as f:
                img_bytes = f.read()
            payload = aiohttp.FormData()
            payload.add_field("file", img_bytes, filename="screenshot.png", content_type="image/png")
            payload.add_field("payload_json", '{"content": "' + message + '"}')
            try:
                async with session.post(WEBHOOK_URL, data=payload) as resp:
                    if resp.status != 204:
                        logger.error(f"Discord webhook failed with status {resp.status}")
            except Exception as e:
                logger.error(f"Exception sending to Discord: {e}")
        else:
            try:
                async with session.post(WEBHOOK_URL, json=data) as resp:
                    if resp.status != 204:
                        logger.error(f"Discord webhook failed with status {resp.status}")
            except Exception as e:
                logger.error(f"Exception sending to Discord: {e}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
        page = await context.new_page()

        await stealth_async(page)

        logger.info("Navigating to Currys Epic Deals page...")
        await page.goto("https://www.currys.co.uk/epic-deals", timeout=60000)

        # Wait and check for the main product container or "checking your connection" message
        attempts = 3
        selector = ".product-item-element"
        for attempt in range(1, attempts + 1):
            try:
                logger.info(f"Waiting for {selector}, attempt {attempt}")
                await page.wait_for_selector(selector, timeout=15000)
                logger.info(f"Found product elements on attempt {attempt}")
                break
            except Exception:
                logger.warning(f"[DEBUG] Timeout on attempt {attempt}: {selector} not found")

                # Screenshot on last attempt or if suspicious page is detected
                if attempt == attempts or "just checking your connection" in (await page.content()).lower():
                    screenshot_path = f"screenshot_fail_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    await page.screenshot(path=screenshot_path)
                    logger.error(f"No {selector} elements found after {attempts} attempts. Screenshot saved to {screenshot_path}")
                    await send_to_discord(f"Blocked or no deals found on Currys. Screenshot attached.", screenshot_path)
                    await browser.close()
                    return

        # Example extraction logic here
        deals = []
        products = await page.query_selector_all(selector)
        for product in products:
            title_el = await product.query_selector("a")
            price_el = await product.query_selector(".price")
            save_el = await product.query_selector(".save")

            title = await title_el.inner_text() if title_el else "No title"
            price = await price_el.inner_text() if price_el else "No price"
            save = await save_el.inner_text() if save_el else "No save info"

            # Filter deals with >= 70% off (example, you can customize)
            if save != "No save info" and "%" in save:
                try:
                    discount = int(save.strip().replace("Save ", "").replace("%", ""))
                    if discount >= 70:
                        deals.append(f"{title} | {price} | {save}")
                except:
                    continue

        if deals:
            message = "🔥 Currys deals with 70%+ off:\n" + "\n".join(deals)
            await send_to_discord(message)
            logger.info("Sent deals to Discord")
        else:
            logger.info("No qualifying deals found.")
            await send_to_discord("No qualifying Currys deals found.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())