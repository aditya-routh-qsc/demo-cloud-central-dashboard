import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://www.infocomm-india.com/2026-show-schedule"
        await page.goto(url, wait_until="networkidle")
        
        items_selector = ".m-seminar-list__list__items__item"
        items_count = await page.locator(items_selector).count()
        print(f"Total items found: {items_count}")
        
        for i in range(items_count):
            item = page.locator(items_selector).nth(i)
            title_el = item.locator(".m-seminar-list__list__items__item__title")
            title_count = await title_el.count()
            if title_count == 0:
                print(f"--- Item {i} has NO title element ---")
                html = await item.evaluate("el => el.outerHTML")
                print(html[:1000])
            else:
                title = await title_el.inner_text()
                if not title.strip():
                    print(f"--- Item {i} has empty title text ---")
                    html = await item.evaluate("el => el.outerHTML")
                    print(html[:1000])
                    
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
