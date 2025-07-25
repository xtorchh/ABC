import asyncio
import requests
from playwright.async_api import async_playwright

DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1398087107469250591/zZ7WPGGj-cQ7l5H8VRV48na0PqgOAKqE1exEIm3vBRVnuCk7BcuP21UIu-vEM8KRfLVQ"

def send_test_message():
    data = {"content": "🚀 Scraper bot started and running!"}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=data)
        if response.status_code == 204:
            print("Test message sent to Discord successfully.")
        else:
            print(f"Failed to send test message. Status code: {response.status_code}")
    except Exception as e:
        print(f"Error sending test message: {e}")

async def main():
    send_test_message()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()

        # Example: Go to Argos deals page (adjust URL to actual deals page)
        await page.goto("https://www.argos.co.uk/deals/")

        # Wait for page to load needed content
        await page.wait_for_selector(".ProductCardstyles__Content-sc-1e1ur9q-1")  # example selector

        # Scrape deals example - adapt selectors as needed
        products = await page.query_selector_all(".ProductCardstyles__Content-sc-1e1ur9q-1")

        for product in products:
            title = await product.query_selector_eval("h3", "el => el.textContent")  
            price = await product.query_selector_eval(".Price__value", "el => el.textContent")  
            discount = await product.query_selector_eval(".DiscountBadge__percentage", "el => el.textContent").catch(lambda e: None)

            if discount:
                try:
                    discount_num = int(discount.replace("%", "").strip())
                    if discount_num >= 80:
                        print(f"Deal found: {title.strip()} at {price.strip()} with {discount_num}% off")
                        # Send deal to Discord webhook here, e.g.:
                        data = {"content": f"🔥 Deal alert! {title.strip()} now {price.strip()} ({discount_num}% OFF)"}
                        requests.post(DISCORD_WEBHOOK_URL, json=data)
                except Exception as e:
                    print(f"Error parsing discount: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())