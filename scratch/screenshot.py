import asyncio

async def main():
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Set viewport size to desktop
        await page.set_viewport_size({"width": 1280, "height": 800})
        
        # Navigate to dashboard
        print("Navigating to http://localhost:8000/ ...")
        await page.goto("http://localhost:8000/")
        await page.wait_for_timeout(2000) # Wait for page load
        
        # Click on Teams tab
        print("Clicking on Teams tab...")
        await page.click("button[data-tab='teams']")
        await page.wait_for_timeout(2000)
        
        # Select 'Reflect Manager' team
        print("Selecting 'Reflect Manager' team...")
        await page.click(".team-card:has-text('Reflect Manager')")
        await page.wait_for_timeout(2000)
        
        # Click on 'Work Done' tab in Team Details
        print("Clicking on 'Work Done' tab...")
        await page.click("button[data-team-tab='work_done']")
        await page.wait_for_timeout(1000)
        
        # Take a screenshot
        screenshot_path = "scratch/screenshot.png"
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
