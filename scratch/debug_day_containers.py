import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        url = "https://www.infocomm-india.com/2026-show-schedule"
        await page.goto(url, wait_until="networkidle")
        
        # Let's search for elements containing days or dates like "Wednesday", "Thursday", "Friday", "16", "17", "18"
        print("Searching for headers/titles containing days...")
        headers = await page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('h1, h2, h3, h4, h5, h6, th, td, div, span, button, a').forEach(el => {
                const text = el.innerText || '';
                if (/Wednesday|Thursday|Friday|16 Sep|17 Sep|18 Sep|September/i.test(text)) {
                    if (text.length < 100) {
                        results.push({ tag: el.tagName, className: el.className, text: text.trim().replace(/\\n/g, ' ') });
                    }
                }
            });
            return results;
        }""")
        print(f"Found {len(headers)} matches:")
        for idx, h in enumerate(headers[:30]):
            print(f"[{idx}] Tag: {h['tag']}, Class: {h['className']}, Text: '{h['text']}'")
            
        # Let's inspect the DOM hierarchy inside the main seminar list to see if there are parent columns or groups
        print("\nStructure inside .m-seminar-list:")
        seminar_list_html = await page.evaluate("""() => {
            const el = document.querySelector('.m-seminar-list');
            if (!el) return 'Not found';
            // Let's print tag name and class names of direct children
            return Array.from(el.children).map(child => `${child.tagName}.${child.className}`).join(', ');
        }""")
        print(seminar_list_html)
        
        # Let's see if there are row groups or columns
        # E.g., is there a wrapper for each day?
        # Let's find the parent element of .m-seminar-list__list__row
        parent_info = await page.evaluate("""() => {
            const row = document.querySelector('.m-seminar-list__list__row');
            if (!row) return 'No rows';
            const parent = row.parentElement;
            return `Parent: ${parent.tagName}.${parent.className}, parent of parent: ${parent.parentElement.tagName}.${parent.parentElement.className}`;
        }""")
        print(f"\nRow parent info:\n{parent_info}")
        
        # Let's print the entire outer HTML of the parent of .m-seminar-list__list__row
        # but just the structure (tags and classes) without inner text
        structure_info = await page.evaluate("""() => {
            function getStructure(el, depth=0) {
                if (depth > 4) return '';
                let res = '  '.repeat(depth) + el.tagName + (el.className ? '.' + el.className.split(' ').join('.') : '') + '\\n';
                for (let child of el.children) {
                    // Skip if it's item contents
                    if (el.className.includes('__items')) continue;
                    res += getStructure(child, depth+1);
                }
                return res;
            }
            const list = document.querySelector('.m-seminar-list');
            return list ? getStructure(list) : 'Not found';
        }""")
        print("\nSeminar list structure:")
        print(structure_info)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
