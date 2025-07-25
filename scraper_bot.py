import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import aiohttp
import logging
import datetime

DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def send_to_discord(content: str, file_path=None):
    async with aiohttp.ClientSession() as session:
        data = {"content": content}
        files = None
        if file_path:
            files = {"file": open(file_path, "rb")}
        try:
            if files:
                # multipart upload if screenshot file present
                async with session.post(DISCORD_WEBHOOK, data=data, files=files) as resp:
                    if resp.status not in (200, 204):
                        logger.error(f"Discord webhook failed with status: {resp.status}")
            else:
                async with session.post(DISCORD_WEBHOOK, json=data) as resp:
                    if resp.status not in (200, 204):
                        logger.error(f"Discord webhook failed with status: {resp.status}")
                    else:
                        logger.info("Sent message to Discord")
        except Exception as e:
            logger.error(f"Failed to send to Discord: {e}")
        finally:
            if files:
                files["file"].close()

async def scrape_currys(page):
    logger.info("Navigating to Currys Epic Deals page...")
    await page.goto("https://www.currys.co.uk/epic-deals", wait_until="networkidle")

    # Wait and retry logic to wait for product cards up to 3 tries
    for attempt in range(1, 4):
        try:
            logger.debug(f"Waiting for .ProductCard elements, attempt {attempt}")
            await page.wait_for_selector(".ProductCard", timeout=15000)
            break
        except PlaywrightTimeoutError:
            logger.warning(f"[DEBUG] Timeout on attempt {attempt}: .ProductCard not found")
            if attempt == 3:
                # Save screenshot on failure
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"screenshot_fail_{timestamp}.png"
                await page.screenshot(path=screenshot_path)
                logger.error(f"No ProductCard elements found after 3 attempts. Screenshot saved to {screenshot_path}")
                await send_to_discord(f"⚠️ [ERROR] Timeout: ProductCard elements not found after retries. See screenshot attached.", file_path=screenshot_path)
                return []
            await asyncio.sleep(5)  # wait before retrying

    products = await page.query_selector_all(".ProductCard")
    logger.debug(f"Found {len(products)} product cards.")

    deals = []
    for product in products:
        try:
            title = await product.query_selector_eval(".product-title", "el => el.innerText")
            price_text = await product.query_selector_eval(".price", "el => el.innerText")
            save_text = await product.query_selector_eval(".save-percentage", "el => el.innerText")
        except Exception as e:
            logger.debug(f"Skipping product due to missing fields: {e}")
            continue

        if not (title and price_text and save_text):
            continue

        import re
        m = re.search(r"(\d+)%", save_text)
        discount = int(m.group(1)) if m else None

        if discount and discount >= 70:
            deals.append({
                "title": title.strip(),
                "price": price_text.strip(),
                "discount": discount
            })

    return deals

async def main():
    logger.info("Starting scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        deals = await scrape_currys(page)
        if deals:
            msg_lines = ["🔥 **Currys Deals 70%+ Off:**"]
            for d in deals:
                msg_lines.append(f"- {d['title']} | Price: {d['price']} | Save: {d['discount']}%")
            msg = "\n".join(msg_lines)
            await send_to_discord(msg)
        else:
            logger.info("No qualifying deals found.")
            await send_to_discord("No qualifying deals found on Currys Epic Deals page.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())