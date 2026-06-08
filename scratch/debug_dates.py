import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://www.infocomm-india.com/2026-show-schedule"
        await page.goto(url, wait_until="networkidle")
        
        # Let's inspect the page structure around the rows
        rows_selector = ".m-seminar-list__list__row"
        rows_count = await page.locator(rows_selector).count()
        print(f"Total rows found: {rows_count}")
        
        for i in range(rows_count):
            row = page.locator(rows_selector).nth(i)
            # Check row header text
            header_el = row.locator(".m-seminar-list__list__row__header")
            header_text = ""
            if await header_el.count() > 0:
                header_text = await header_el.text_content()
                header_text = header_text.strip().replace("\n", " ")
            print(f"Row {i}: header='{header_text}'")
            
            # Check number of items in this row
            items_el = row.locator(".m-seminar-list__list__items__item")
            items_count = await items_el.count()
            print(f"  -> Items in row: {items_count}")
            if items_count > 0:
                first_item_title = await items_el.first.locator(".m-seminar-list__list__items__item__title").text_content()
                print(f"  -> First item title: '{first_item_title.strip()}'")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
