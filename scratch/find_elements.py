import asyncio
import re
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating...")
        await page.goto("https://www.infocomm-india.com/2026-show-schedule", wait_until="networkidle")
        
        content = await page.content()
        
        # Look for text like "AVIXA Xchange Live" or "Opening Ceremony" or times like "10:30"
        print("Searching for AVIXA Xchange Live...")
        matches = [m.start() for m in re.finditer("AVIXA Xchange Live", content)]
        print(f"Found {len(matches)} matches.")
        for idx, pos in enumerate(matches[:5]):
            start = max(0, pos - 100)
            end = min(len(content), pos + 200)
            print(f"Match {idx+1}: {content[start:end]}\n---")
            
        # Let's inspect the tags around some schedule text
        # Let's query elements with classes that might contain schedule items, e.g. divs, sections, lists, articles
        # Let's see if there's any JSON-LD or script tags with schedule data
        # We can find all class names used in the page
        classes = await page.evaluate("""() => {
            const classNames = new Set();
            document.querySelectorAll('*').forEach(el => {
                if (el.className) {
                    if (typeof el.className === 'string') {
                        el.className.split(/\\s+/).forEach(c => classNames.add(c));
                    }
                }
            });
            return Array.from(classNames);
        }""")
        print(f"Total unique classes: {len(classes)}")
        # Filter classes that contain words like schedule, program, session, list, item, event
        interesting_classes = [c for c in classes if any(x in c.lower() for x in ["schedule", "program", "session", "list", "item", "event", "track", "time", "date"])]
        print(f"Interesting classes: {interesting_classes}")

        # Let's extract all list item text or table text if any
        # Let's dump all text of elements that have some classes
        for cls in sorted(interesting_classes)[:15]:
            count = await page.locator(f".{cls}").count()
            print(f"Class .{cls}: {count} elements")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
