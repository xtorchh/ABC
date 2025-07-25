import asyncio
import json
import re
import requests
from playwright.async_api import async_playwright

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

def send_to_discord(product):
    data = {
        "content": f"🔥 **{product['title']}**\n💸 Was: £{product['original_price']} | Now: £{product['discounted_price']}\n🔗 {product['url']}"
    }
    requests.post(DISCORD_WEBHOOK_URL, data=json.dumps(data), headers={"Content-Type": "application/json"})

def parse_price(text):
    match = re.search(r'£([\d,.]+)', text)
    return float(match.group(1).replace(',', '')) if match else None

async def scrape_argos(page):
    await page.goto("https://www.argos.co.uk/search/clearance/", timeout=60000)
    await page.wait_for_timeout(3000)
    cards = await page.query_selector_all("article[data-test='component-product-card']")

    for card in cards:
        try:
            title = await card.query_selector_eval("h2", "el => el.innerText")
            url_suffix = await card.query_selector_eval("a", "el => el.getAttribute('href')")
            product_url = "https://www.argos.co.uk" + url_suffix

            prices = await card.query_selector_all("div[data-test='component-product-price']")
            if not prices:
                continue

            price_text = await prices[0].inner_text()
            all_prices = re.findall(r'£[\d,.]+', price_text)
            if len(all_prices) < 2:
                continue

            original_price = parse_price(all_prices[0])
            discounted_price = parse_price(all_prices[-1])

            if original_price and discounted_price:
                discount = (original_price - discounted_price) / original_price
                if discount >= 0.8:
                    send_to_discord({
                        "title": title.strip(),
                        "original_price": original_price,
                        "discounted_price": discounted_price,
                        "url": product_url
                    })
        except:
            continue

async def scrape_currys(page):
    await page.goto("https://www.currys.co.uk/gbuk/clearance-sale-46-commercial.html", timeout=60000)
    await page.wait_for_timeout(5000)
    cards = await page.query_selector_all("li.product")

    for card in cards:
        try:
            title = await card.query_selector_eval("h3.product-title", "el => el.innerText")
            url_suffix = await card.query_selector_eval("a", "el => el.getAttribute('href')")
            product_url = "https://www.currys.co.uk" + url_suffix

            was_price_el = await card.query_selector("span.was-price")
            sale_price_el = await card.query_selector("strong.sales-price")

            if not was_price_el or not sale_price_el:
                continue

            original_price = parse_price(await was_price_el.inner_text())
            discounted_price = parse_price(await sale_price_el.inner_text())

            if original_price and discounted_price:
                discount = (original_price - discounted_price) / original_price
                if discount >= 0.8:
                    send_to_discord({
                        "title": title.strip(),
                        "original_price": original_price,
                        "discounted_price": discounted_price,
                        "url": product_url
                    })
        except:
            continue

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        await scrape_argos(page)
        await scrape_currys(page)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())