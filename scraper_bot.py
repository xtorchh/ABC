import asyncio
from playwright.async_api import async_playwright
import aiohttp
import re

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

async def send_discord_message(message: str, file_path: str = None):
    async with aiohttp.ClientSession() as session:
        data = aiohttp.FormData()
        data.add_field("content", message)

        if file_path:
            with open(file_path, "rb") as f:
                data.add_field("file", f, filename="debug_screenshot.png", content_type="image/png")

        try:
            async with session.post(DISCORD_WEBHOOK_URL, data=data) as resp:
                if resp.status not in [200, 204]:
                    print(f"Failed to send message: {resp.status}")
        except Exception as e:
            print(f"Exception sending message: {e}")

async def scrape_currys(page):
    await page.goto("https://www.currys.co.uk/epic-deals", timeout=60000, wait_until="networkidle")
    await page.wait_for_timeout(2000)  # extra wait for animation/load

    try:
        await page.wait_for_selector('li[data-component="ProductCard"]', timeout=10000)
    except Exception:
        await page.screenshot(path="debug_screenshot.png", full_page=True)
        await send_discord_message("[DEBUG] Timeout: ProductCard elements not found. See screenshot.", "debug_screenshot.png")
        return []

    products = await page.query_selector_all('li[data-component="ProductCard"]')
    if not products:
        await page.screenshot(path="debug_screenshot.png", full_page=True)
        await send_discord_message("[DEBUG] No ProductCard elements after wait. See screenshot.", "debug_screenshot.png")
        return []

    deals = []

    for product in products:
        try:
            title_el = await product.query_selector("h2")
            price_el = await product.query_selector('[data-testid="productPrice"]')
            save_el = await product.query_selector("span:has-text('Save')")

            title = (await title_el.inner_text()).strip() if title_el else "No title"
            price_text = (await price_el.inner_text()).strip() if price_el else None
            save_text = (await save_el.inner_text()).strip() if save_el else None

            save_pct = 0
            if save_text:
                match = re.search(r"\((\d+)%\)", save_text)
                if match:
                    save_pct = int(match.group(1))

            if save_pct >= 70 and price_text:
                deals.append(f"**{title}** - {price_text} - {save_text}")

        except Exception as e:
            await send_discord_message(f"[DEBUG] Error parsing product: {e}")

    return deals

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()

        deals = await scrape_currys(page)

        if deals:
            for deal in deals:
                await send_discord_message(deal)
        else:
            await send_discord_message("No qualifying deals found.")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())