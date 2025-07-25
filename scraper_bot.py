import os
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import aiohttp
import base64
from io import BytesIO

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

if not DISCORD_WEBHOOK_URL:
    print("Error: DISCORD_WEBHOOK_URL environment variable not set.")
    exit(1)

async def send_discord_message(content, screenshot_bytes=None):
    data = {"content": content}
    files = None

    if screenshot_bytes:
        # Discord requires multipart form for files
        files = {
            "file": ("screenshot.png", screenshot_bytes)
        }

    async with aiohttp.ClientSession() as session:
        if files:
            form = aiohttp.FormData()
            form.add_field("payload_json", str(data), content_type="application/json")
            form.add_field("file", screenshot_bytes, filename="screenshot.png", content_type="image/png")
            async with session.post(DISCORD_WEBHOOK_URL, data=form) as resp:
                return await resp.text()
        else:
            async with session.post(DISCORD_WEBHOOK_URL, json=data) as resp:
                return await resp.text()

async def scrape_currys(page):
    await page.goto("https://www.currys.co.uk/gbuk/epic-deals.html")
    # Wait for product cards (adjust selector if needed)
    try:
        await page.wait_for_selector(".ProductCard", timeout=15000)
    except Exception:
        raise RuntimeError("Timeout: .ProductCard not found on page.")

    products = await page.query_selector_all(".ProductCard")

    deals = []
    for product in products:
        title_el = await product.query_selector(".ProductCard-name")
        price_el = await product.query_selector(".ProductPrice")
        save_el = await product.query_selector(".ProductCard-save")
        link_el = await product.query_selector("a.ProductCard-link")

        title = (await title_el.inner_text()) if title_el else "No title"
        price_text = (await price_el.inner_text()) if price_el else ""
        save_text = (await save_el.inner_text()) if save_el else ""

        # Extract % off from save_text e.g. "Save 70%"
        percent_off = 0
        if "save" in save_text.lower():
            import re
            m = re.search(r"(\d+)%", save_text)
            if m:
                percent_off = int(m.group(1))

        if percent_off >= 70:
            link = (await link_el.get_attribute("href")) if link_el else "#"
            full_link = f"https://www.currys.co.uk{link}" if link.startswith("/") else link

            deals.append({
                "title": title.strip(),
                "price": price_text.strip(),
                "discount": save_text.strip(),
                "link": full_link
            })
    return deals

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context()
        page = await context.new_page()
        await stealth_async(page)

        try:
            deals = await scrape_currys(page)
            if deals:
                msg = "**Currys Epic Deals (70%+ off):**\n\n"
                for d in deals:
                    msg += f"- [{d['title']}]({d['link']})\n  Price: {d['price']} | {d['discount']}\n"
                await send_discord_message(msg)
            else:
                await send_discord_message("No qualifying Currys deals found.")
        except Exception as e:
            screenshot = await page.screenshot(full_page=True)
            await send_discord_message(f"[ERROR] Exception occurred: {e}\nScreenshot attached.", screenshot_bytes=screenshot)
        finally:
            await browser.close()

if __name__ == "__main__":
    async def run_loop():
        while True:
            await main()
            await asyncio.sleep(600)  # 10 minutes

    asyncio.run(run_loop())