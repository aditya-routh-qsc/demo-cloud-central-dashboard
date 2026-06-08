import asyncio
import json
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://www.infocomm-india.com/2026-show-schedule"
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle")
        
        # Select all schedule items
        items_selector = ".m-seminar-list__list__items__item"
        items_count = await page.locator(items_selector).count()
        print(f"Found {items_count} schedule items.")
        
        schedule = []
        for i in range(items_count):
            item = page.locator(items_selector).nth(i)
            
            # Extract fields safely
            title_el = item.locator(".m-seminar-list__list__items__item__title")
            title = await title_el.inner_text() if await title_el.count() > 0 else ""
            title = title.strip()
            
            link_el = title_el.locator("a")
            link = await link_el.get_attribute("href") if await link_el.count() > 0 else ""
            if link and not link.startswith("http"):
                link = f"https://www.infocomm-india.com/{link.lstrip('/')}"
            
            location_el = item.locator(".m-seminar-list__list__items__item__location")
            location = await location_el.inner_text() if await location_el.count() > 0 else ""
            location = location.replace("\n", " ").strip()
            
            duration_el = item.locator(".m-seminar-list__list__items__item__duration")
            duration = await duration_el.inner_text() if await duration_el.count() > 0 else ""
            duration = duration.strip()
            
            desc_el = item.locator(".m-seminar-list__list__items__item__description")
            desc = await desc_el.inner_text() if await desc_el.count() > 0 else ""
            desc = desc.strip()
            
            schedule.append({
                "index": i + 1,
                "title": title,
                "link": link,
                "location": location,
                "duration": duration,
                "description": desc
            })
            
        print("\nExtracted Sessions:")
        print("===================")
        for s in schedule[:5]:
            print(f"[{s['index']}] {s['title']}")
            print(f"   Time: {s['duration']}")
            print(f"   Location: {s['location']}")
            print(f"   Link: {s['link']}")
            print(f"   Description: {s['description'][:150]}...")
            print("-" * 50)
            
        # Write to JSON
        output_file = "scratch/schedule.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(schedule, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(schedule)} items to {output_file}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
