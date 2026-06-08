import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # Launch headless browser
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to InfoComm India Show Schedule...")
        await page.goto("https://www.infocomm-india.com/2026-show-schedule", wait_until="networkidle")
        
        # Get the page title and HTML content
        title = await page.title()
        print(f"Page Title: {title}")
        
        # Let's inspect the page content
        content = await page.content()
        print(f"Content Length: {len(content)} bytes")
        
        # Save a snippet of body to check
        body_text = await page.locator("body").inner_text()
        print("First 1000 characters of body text:")
        print(body_text[:1000])
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
