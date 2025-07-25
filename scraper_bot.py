import asyncio
import logging
from playwright.async_api import async_playwright
import requests

WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"
CURRYS_URL = "https://www.currys.co.uk/epic-deals"
MIN_SAVE_POUNDS = 20

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s:%(message)s")


async def scrape_currys(page):
    logging.info("Navigating to Currys Epic Deals page...")
    await page.goto(CURRYS_URL, timeout=60000)

    logging.info("Waiting for .product-item-element selector")
    try:
        await page.wait_for_selector(".product-item-element", timeout=10000)
    except Exception as e:
        logging.error(f"No '.product-item-element' found: {e}")
        return []

    products = await page.query_selector_all(".product-item-element")
    logging.info(f"Found {len(products)} products")

    deals = []
    for product in products:
        try:
            name = await product.query_selector_eval(".list-product-tile-name", "el => el.textContent.trim()")
            price = await product.query_selector_eval(".value[content]", "el => el.getAttribute('content')")
            saving_elem = await product.query_selector(".primary-save-price")
            saving = 0
            if saving_elem:
                saving_text = await saving_elem.text_content()
                saving = int(saving_text.strip().replace("£", "").replace(".00", ""))

            if saving >= MIN_SAVE_POUNDS:
                # Get URL and image
                url_elem = await product.query_selector("a")
                url = "https://www.currys.co.uk" + await url_elem.get_attribute("href") if url_elem else ""

                image_elem = await product.query_selector("img")
                image = await image_elem.get_attribute("src") if image_elem else ""

                deals.append({
                    "name": name,
                    "price": price,
                    "saving": saving,
                    "url": url,
                    "image": image
                })
        except Exception as e:
            logging.warning(f"Error parsing product: {e}")
            continue

    return deals


async def send_to_discord(deals):
    for deal in deals:
        message = {
            "embeds": [{
                "title": deal["name"],
                "description": f"💷 Price: **£{deal['price']}**\n💸 You save: **£{deal['saving']}**",
                "url": deal["url"],
                "image": {"url": deal["image"]},
                "color": 5814783
            }]
        }
        try:
            response = requests.post(WEBHOOK_URL, json=message)
            if response.status_code == 204:
                logging.info("✅ Deal sent to Discord")
            else:
                logging.warning(f"⚠️ Discord responded with {response.status_code}")
        except Exception as e:
            logging.error(f"Failed to send deal to Discord: {e}")


async def main():
    logging.info("Starting Currys scraper...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        deals = await scrape_currys(page)
        await send_to_discord(deals)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())