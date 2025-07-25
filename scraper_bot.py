import asyncio
import logging
from playwright.async_api import async_playwright
import aiohttp
import datetime

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_to_discord(message, screenshot_path=None):
    async with aiohttp.ClientSession() as session:
        try:
            if screenshot_path:
                with open(screenshot_path, "rb") as f:
                    files = {"file": f}
                    data = {"content": message}
                    # Discord webhook file upload with aiohttp
                    # Discord expects multipart/form-data with file key "file"
                    # aiohttp requires using 'data' for form data and 'files' param isn't accepted.
                    # So we use MultipartWriter instead:
                    from aiohttp import FormData
                    form = FormData()
                    form.add_field("content", message)
                    form.add_field("file", f, filename=screenshot_path)
                    async with session.post(WEBHOOK_URL, data=form) as resp:
                        if resp.status != 204 and resp.status != 200:
                            text = await resp.text()
                            logger.error(f"Discord webhook failed: {resp.status} {text}")
                        else:
                            logger.info("Sent message and screenshot to Discord")
            else:
                async with session.post(WEBHOOK_URL, json={"content": message}) as resp:
                    if resp.status != 204 and resp.status != 200:
                        text = await resp.text()
                        logger.error(f"Discord webhook failed: {resp.status} {text}")
                    else:
                        logger.info("Sent message to Discord")
        except Exception as e:
            logger.error(f"[ERROR] Failed to send to Discord: {e}")

async def scrape_currys(page):
    attempts = 3
    selectors = [".product-item-element", ".plp-productitem-id", ".mobile-item-element"]
    for attempt in range(1, attempts + 1):
        for selector in selectors:
            logger.info(f"[DEBUG] Waiting for {selector}, attempt {attempt}")
            try:
                await page.wait_for_selector(selector, timeout=15000)
                logger.info(f"Found elements with selector: {selector}")
                return selector
            except Exception as e:
                logger.warning(f"[DEBUG] Timeout on attempt {attempt} for selector {selector}: {e}")
        if attempt < attempts:
            await asyncio.sleep(2)
    return None

async def main():
    logger.info("Starting scraper...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        url = "https://www.currys.co.uk/epic-deals"
        logger.info(f"Navigating to Currys Epic Deals page: {url}")
        await page.goto(url)

        # Take screenshot immediately after page load for debug
        debug_screenshot = f"page_after_load_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        await page.screenshot(path=debug_screenshot)
        logger.info(f"Saved initial page screenshot to {debug_screenshot}")
        await send_to_discord(f"Loaded Currys deals page - screenshot attached.", debug_screenshot)

        # Scroll down to trigger lazy loading
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(3)

        selector = await scrape_currys(page)
        if not selector:
            error_screenshot = f"screenshot_fail_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=error_screenshot)
            logger.error(f"No product elements found after 3 attempts. Screenshot saved to {error_screenshot}")
            await send_to_discord(f"[ERROR] No product elements found after 3 attempts. See screenshot.", error_screenshot)
            await browser.close()
            return

        # Extract deals info
        deals = await page.eval_on_selector_all(
            selector,
            """(elements) => elements.map(el => {
                const titleEl = el.querySelector('.product-title, .plp-product-title, h3');
                const priceEl = el.querySelector('.product-price, .plp-product-price, .price');
                const saveEl = el.querySelector('.product-save, .plp-product-save, .save');
                return {
                    title: titleEl ? titleEl.innerText.trim() : null,
                    price: priceEl ? priceEl.innerText.trim() : null,
                    save: saveEl ? saveEl.innerText.trim() : null
                };
            })"""
        )

        qualifying_deals = [d for d in deals if d["save"] and "70%" in d["save"]]

        if not qualifying_deals:
            logger.info("No qualifying deals found.")
            await send_to_discord("No qualifying deals with 70%+ discount found on Currys.")
        else:
            for deal in qualifying_deals:
                msg = f"Deal Found:\n{deal['title']}\nPrice: {deal['price']}\nSave: {deal['save']}"
                await send_to_discord(msg)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())