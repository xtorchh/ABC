import asyncio
import logging
import requests

MIN_SAVE_POUNDS = 20
WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

async def scrape_currys(page):
    await page.goto("https://www.currys.co.uk/epic-deals")
    await page.wait_for_selector(".product-item-element")

    products = await page.query_selector_all(".product-item-element")
    deals = []

    for product in products:
        try:
            name = await product.query_selector_eval(".list-product-tile-name.desktop-only span", "el => el.textContent.trim()")
            price_text = await product.query_selector_eval(".product-tile-price-now .value", "el => el.textContent.trim()")
            saving_el = await product.query_selector(".primary-save-price")
            saving = 0.0
            if saving_el:
                saving_text = await saving_el.text_content()
                saving = float(saving_text.strip().replace("£", ""))
            
            url = await product.query_selector_eval("a.product-tile-link", "el => el.href")
            image = await product.query_selector_eval("img.product-tile-image", "el => el.src")

            price = float(price_text.replace("£", "").replace(",", ""))

            if saving >= MIN_SAVE_POUNDS:
                deals.append({
                    "name": name,
                    "price": price,
                    "saving": saving,
                    "url": url,
                    "image": image
                })
        except Exception as e:
            logging.warning(f"Error parsing product: {e}")

    return deals

async def send_to_discord(deals):
    for deal in deals:
        if not deal["name"] or not deal["url"]:
            continue
        
        embed = {
            "embeds": [{
                "title": deal["name"],
                "description": f"💷 Price: **£{deal['price']:.2f}**\n💸 You save: **£{deal['saving']:.2f}**",
                "url": deal["url"],
                "image": {"url": deal["image"]},
                "color": 5814783
            }]
        }
        try:
            r = requests.post(WEBHOOK_URL, json=embed)
            if r.status_code == 204:
                logging.info("✅ Deal sent to Discord")
            else:
                logging.warning(f"⚠️ Discord responded with {r.status_code}: {r.text}")
            await asyncio.sleep(1)  # Rate limiting delay
        except Exception as e:
            logging.error(f"Failed to send to Discord: {e}")

async def main():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        logging.info("Starting Currys scraper...")
        
        deals = await scrape_currys(page)
        if deals:
            await send_to_discord(deals)
        else:
            logging.info("No qualifying deals found.")

        await browser.close()

if __name__ == "__main__":
    import asyncio
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')
    asyncio.run(main())