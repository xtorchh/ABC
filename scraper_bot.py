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

async def scrape_currys(page):
    deals = []
    await page.goto("https://www.currys.co.uk/epic-deals")
    await page.wait_for_selector('.product-listing-item')

    products = await page.query_selector_all('.product-listing-item')
    for product in products:
        title_el = await product.query_selector('.product-title')
        price_el = await product.query_selector('.price--actual')
        original_price_el = await product.query_selector('.price--was')

        if not title_el or not price_el:
            continue

        title = (await title_el.inner_text()).strip()
        price_text = (await price_el.inner_text()).strip()
        original_price_text = (await original_price_el.inner_text()).strip() if original_price_el else None

        def parse_price(text):
            return float(text.replace('£', '').replace(',', '').strip())

        try:
            price = parse_price(price_text)
            original_price = parse_price(original_price_text) if original_price_text else None
        except Exception:
            continue

        if original_price and original_price > 0:
            discount_pct = round((original_price - price) / original_price * 100)
        else:
            discount_pct = 0

        if discount_pct >= 70:  # Only 70%+ deals
            url = await product.query_selector_eval('a', 'a => a.href')
            deals.append({
                'title': title,
                'price': price,
                'original_price': original_price,
                'discount_pct': discount_pct,
                'url': url
            })
    return deals

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()

        deals = await scrape_currys(page)

        for deal in deals:
            await send_to_discord(deal)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())