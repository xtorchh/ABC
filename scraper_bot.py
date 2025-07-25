import asyncio
import os
import aiohttp
from playwright.async_api import async_playwright

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

async def send_discord_message(message: str, file_path: str = None):
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field("content", message)

        if file_path and os.path.exists(file_path):
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            data.add_field("file", file_bytes, filename="debug_screenshot.png", content_type="image/png")

        try:
            async with session.post(DISCORD_WEBHOOK_URL, data=data) as resp:
                if resp.status not in [200, 204]:
                    print(f"Failed to send message: {resp.status}")
        except Exception as e:
            print(f"Exception sending message: {e}")
        finally:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)

async def scrape_currys(page):
    try:
        await page.goto("https://www.currys.co.uk/epic-deals", timeout=60000)
        # Wait for product cards to load
        await page.wait_for_selector(".ProductCard", timeout=15000)

        products = await page.query_selector_all(".ProductCard")
        qualifying_deals = []

        for product in products:
            # Get discount percentage or saved amount text
            discount_text = await product.query_selector_eval(
                ".ProductCard-discountBadge, .ProductCard-saving", "el => el.textContent"
            )

            if not discount_text:
                continue

            # Extract number from discount text (e.g. "Save £150" or "70% off")
            import re
            discount_percent = 0
            # Try to find % discount first
            percent_match = re.search(r"(\d+)%", discount_text)
            if percent_match:
                discount_percent = int(percent_match.group(1))
            else:
                # Could parse amount saved but here we keep only % for simplicity
                continue

            if discount_percent >= 70:
                title = await product.query_selector_eval(".ProductCard-title", "el => el.textContent")
                price = await product.query_selector_eval(".ProductCard-price .price", "el => el.textContent")
                url = await product.query_selector_eval("a.ProductCard-link", "el => el.href")

                qualifying_deals.append(f"**{title.strip()}**\nPrice: {price.strip()}\nDiscount: {discount_text.strip()}\n{url}")

        if qualifying_deals:
            message = "🔥 Currys 70%+ OFF Deals Found:\n\n" + "\n\n".join(qualifying_deals)
            await send_discord_message(message)
        else:
            # Screenshot debug if no deals found but page loaded
            await page.screenshot(path="debug_screenshot.png", full_page=True)
            await send_discord_message("[DEBUG] No qualifying deals found. Screenshot attached.", "debug_screenshot.png")

    except Exception as e:
        # Screenshot debug on exception
        await page.screenshot(path="debug_screenshot.png", full_page=True)
        await send_discord_message(f"[ERROR] Exception occurred: {e}. Screenshot attached.", "debug_screenshot.png")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await scrape_currys(page)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())