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

async def send_debug(message):
    async with aiohttp.ClientSession() as session:
        await session.post(DISCORD_WEBHOOK_URL, json={"content": f"[DEBUG] {message}"})

async def scrape_currys(page):
    deals = []
    await page.goto("https://www.currys.co.uk/epic-deals", wait_until="domcontentloaded")

    try:
        await page.click("button#onetrust-accept-btn-handler", timeout=5000)
    except:
        pass  # cookie popup may not appear

    await page.evaluate("""
        async () => {
            await new Promise(resolve => {
                let totalHeight = 0;
                const distance = 300;
                const timer = setInterval(() => {
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if (totalHeight >= document.body.scrollHeight) {
                        clearInterval(timer);
                        resolve();
                    }
                }, 200);
            });
        }
    """)
    await page.wait_for_timeout(3000)

    try:
        await page.wait_for_selector('.ProductCard', timeout=60000)
    except:
        await send_debug("Timeout: .ProductCard not found.")
        return []

    products = await page.query_selector_all('.ProductCard')
    await send_debug(f"Found {len(products)} products.")

    for product in products:
        try:
            title_el = await product.query_selector('.ProductCard__Title')
            price_el = await product.query_selector('.ProductCard__Price .visually-hidden:nth-child(1)')
            save_el = await product.query_selector('.ProductCard__Savings')

            if not title_el or not price_el or not save_el:
                continue

            title = (await title_el.inner_text()).strip()
            price_text = (await price_el.inner_text()).strip()
            save_text = (await save_el.inner_text()).strip()

            def parse_price(text):
                return float(text.replace('£', '').replace(',', '').strip())

            price = parse_price(price_text)
            save_amount = parse_price(save_text.replace('Save', '').replace('£', ''))

            original_price = price + save_amount
            discount_pct = round((save_amount / original_price) * 100)

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
            await send_debug(f"Product error: {e}")
            continue

    return deals

async def main():
    try:
        async with async_playwright() as p:
            await send_debug("Launching browser...")
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            page = await browser.new_page()

            deals = await scrape_currys(page)

            if not deals:
                await send_debug("No qualifying deals found.")
            else:
                await send_debug(f"Found {len(deals)} deals with ≥70% discount.")
                for deal in deals:
                    await send_to_discord(deal)

            await browser.close()
    except Exception as e:
        await send_debug(f"Script crashed: {e}")

if __name__ == "__main__":
    asyncio.run(main())