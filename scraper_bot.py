import asyncio
from playwright.async_api import async_playwright
import aiohttp
import os

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL") or "YOUR_DISCORD_WEBHOOK_URL_HERE"

async def send_debug(message: str):
    async with aiohttp.ClientSession() as session:
        payload = {"content": f"[DEBUG] {message}"}
        try:
            async with session.post(DISCORD_WEBHOOK_URL, json=payload) as resp:
                if resp.status != 204 and resp.status != 200:
                    print(f"Failed to send debug message: {resp.status}")
        except Exception as e:
            print(f"Exception sending debug: {e}")

async def scrape_currys(page):
    deals = []
    await page.goto("https://www.currys.co.uk/epic-deals", wait_until="networkidle")

    # Accept cookies if shown
    try:
        await page.click("button#onetrust-accept-btn-handler", timeout=5000)
    except:
        pass

    # Scroll slowly to load lazy content
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

    selectors = ['.ProductCard', '.product-listing-item', '.product-tile']
    products = []

    for sel in selectors:
        try:
            await page.wait_for_selector(sel, timeout=10000)
            products = await page.query_selector_all(sel)
            if products:
                await send_debug(f"Using selector '{sel}', found {len(products)} products.")
                break
        except Exception:
            continue

    if not products:
        await send_debug("No product elements found with known selectors.")
        return []

    for product in products:
        try:
            title_el = await product.query_selector('.ProductCard__Title, .product-tile__title')
            price_el = await product.query_selector('.ProductCard__Price .visually-hidden:nth-child(1), .product-tile__price')
            save_el = await product.query_selector('.ProductCard__Savings, .product-tile__saving')

            if not title_el or not price_el or not save_el:
                continue

            title = (await title_el.inner_text()).strip()
            price_text = (await price_el.inner_text()).strip()
            save_text = (await save_el.inner_text()).strip()

            def parse_price(text):
                # e.g. "£299.99"
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
            await send_debug(f"Product parsing error: {e}")
            continue

    return deals

async def notify_deals(deals):
    if not deals:
        await send_debug("No qualifying deals found.")
        return

    async with aiohttp.ClientSession() as session:
        for deal in deals:
            content = (f"**{deal['title']}**\n"
                       f"Price: £{deal['price']:.2f} (Original: £{deal['original_price']:.2f})\n"
                       f"Discount: {deal['discount_pct']}%\n"
                       f"{deal['url']}")
            payload = {"content": content}
            try:
                async with session.post(DISCORD_WEBHOOK_URL, json=payload) as resp:
                    if resp.status != 204 and resp.status != 200:
                        print(f"Failed to send deal message: {resp.status}")
            except Exception as e:
                print(f"Exception sending deal: {e}")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()

        deals = await scrape_currys(page)
        await notify_deals(deals)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())