import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://www.infocomm-india.com/2026-show-schedule"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")
        
        # Get all date tabs
        tabs_locator = page.locator(".p-tabs__navigation__title__link.js-tab-toggle")
        tabs_count = await tabs_locator.count()
        print(f"Found {tabs_count} tabs.")
        
        # Get all body content panels
        panels_locator = page.locator(".p-tabs__body__content")
        panels_count = await panels_locator.count()
        print(f"Found {panels_count} body panels.")
        
        # Iterate over each tab
        for d in range(min(tabs_count, panels_count)):
            date_text = await tabs_locator.nth(d).text_content()
            date_text = date_text.strip()
            print(f"\nProcessing tab {d}: Date = '{date_text}'")
            
            panel = panels_locator.nth(d)
            items_locator = panel.locator(".m-seminar-list__list__items__item")
            items_count = await items_locator.count()
            print(f"  -> Found {items_count} items in this panel.")
            
            for i in range(items_count):
                item = items_locator.nth(i)
                title_el = item.locator(".m-seminar-list__list__items__item__title")
                title = ""
                if await title_el.count() > 0:
                    title = (await title_el.text_content()).strip()
                
                # Check location
                location_el = item.locator(".m-seminar-list__list__items__item__location")
                location = ""
                if await location_el.count() > 0:
                    location = (await location_el.text_content()).replace("\n", " ").strip()
                
                # Check duration
                duration_el = item.locator(".m-seminar-list__list__items__item__duration")
                duration = ""
                if await duration_el.count() > 0:
                    duration = (await duration_el.text_content()).strip()
                
                print(f"    [{i+1}] {title} | {duration} | {location} | Date: {date_text}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
