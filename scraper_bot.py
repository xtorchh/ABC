import asyncio
import aiohttp
from playwright.async_api import async_playwright

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

async def send_to_discord(deal):
    content = (
        f"**{deal['title']}**\n"
        f"Price: £{deal['price']:.2f} (was £{deal['original_price']:.2f})\n"
        f"Discount: {deal['discount_pct']}%\n"
        f"{deal['url']}"
    )
    async with aiohttp.ClientSession() as session:
        await session.post(DISCORD_WEBHOOK_URL, json={"content": content})

async def send_debug_message(message):
    async with aiohttp.ClientSession() as session:
        await session.post(DISCORD_WEBHOOK_URL, json={"content": f"[DEBUG] {message}"})

async def scrape_currys(page):
    deals = []
    await page.goto("https://www.currys.co.uk/epic-deals", wait_until="domcontentloaded")

    # Accept cookies
    try:
        await page.click("button#onetrust-accept-btn-handler", timeout=5000)
    except:
        pass

    try:
        await page.wait_for_selector('.ProductCard', timeout=60000)
    except:
        await send_debug_message("Timeout waiting for .ProductCard")
        return []

    products = await page.query_selector_all('.ProductCard')
    for product in products:
        try:
            title_el = await product.query_selector('.ProductCard__Title')
            price_el = await product.query_selector('.ProductCard__Price .visually-hidden:nth-child(1)')
            original_price_el = await product.query_selector('.ProductCard__WasPrice')

            if not title_el or not price_el:
                continue

            title = (await title_el.inner_text()).strip()
            price_text = (await price_el.inner_text()).strip()
            original_price_text = (await original_price_el.inner_text()).strip() if original_price_el else None

            def parse_price(text):
                return float(text.replace('£', '').replace(',', '').strip())

            price = parse_price(price_text)
            original_price = parse_price(original_price_text) if original_price_text else None

            if original_price and original_price > 0:
                discount_pct = round((original_price - price) / original_price * 100)
            else:
                discount_pct = 0

            if discount_pct >= 70:
                url = await product.query_selector_eval('a', 'a => a.href')
                deals.append({
                    'title': title,
                    'price': price,
                    'original_price': original_price,
                    'discount_pct': discount_pct,
                    'url': url
                })

        except Exception as e:
            await send_debug_message(f"Error parsing product: {str(e)}")
            continue

    return deals

async def main():
    try:
        async with async_playwright() as p:
            await send_debug_message("Launching browser...")
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()

            deals = await scrape_currys(page)

            if not deals:
                await send_debug_message("No 70%+ deals found.")
            else:
                await send_debug_message(f"Found {len(deals)} deals. Sending to Discord...")
                for deal in deals:
                    await send_to_discord(deal)

            await browser.close()
            await send_debug_message("Browser closed. Done.")

    except Exception as e:
        await send_debug_message(f"Scraper failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())