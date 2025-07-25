import asyncio
from playwright.async_api import async_playwright
import aiohttp
import re

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

async def send_discord_message(message: str):
    async with aiohttp.ClientSession() as session:
        payload = {"content": message}
        try:
            async with session.post(DISCORD_WEBHOOK_URL, json=payload) as resp:
                if resp.status not in [200, 204]:
                    print(f"Failed to send message: {resp.status}")
        except Exception as e:
            print(f"Exception sending message: {e}")

async def scrape_currys(page):
    await page.goto("https://www.currys.co.uk/epic-deals", timeout=60000)
    try:
        await page.wait_for_selector('li[data-component="ProductCard"]', timeout=30000)
    except Exception:
        await send_discord_message("[DEBUG] Timeout: ProductCard elements not found.")
        return []

    products = await page.query_selector_all('li[data-component="ProductCard"]')
    deals = []

    for product in products:
        try:
            title_el = await product.query_selector("h2")
            price_el = await product.query_selector('[data-testid="productPrice"]')
            save_el = await product.query_selector("span:has-text('Save')")

            title = (await title_el.inner_text()).strip() if title_el else "No title"
            price_text = (await price_el.inner_text()).strip() if price_el else None
            save_text = (await save_el.inner_text()).strip() if save_el else None

            # Extract % from "Save £100 (71%)"
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
        page = await browser.new_page()
        deals = await scrape_currys(page)
        await browser.close()

        if not deals:
            await send_discord_message("No qualifying deals found.")
        else:
            for deal in deals:
                await send_discord_message(deal)

if __name__ == "__main__":
    asyncio.run(main())