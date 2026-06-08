#!/usr/bin/env python
"""
InfoComm India Schedule Scraper
Scrapes the summit/show schedule from the official InfoComm India website.
"""

import argparse
import asyncio
import csv
import json
import sys
from pathlib import Path
from playwright.async_api import async_playwright

SHOW_URLS = {
    "india": "https://www.infocomm-india.com/2026-show-schedule",
    "asia": "https://www.infocomm-asia.com/2026-show-schedule",
    "global": "https://www.infocommshow.org/schedule"
}

async def scrape_schedule(url: str, fallback_path: Path | None = None) -> list[dict]:
    """Navigates to the schedule URL and extracts session details."""
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
    
    print(f"[*] Starting scraper for URL: {url}")
    try:
        async with async_playwright() as p:
            print("[*] Launching headless browser...")
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            print("[*] Navigating to page...")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            print(f"[*] Page loaded. Title: {await page.title()}")
            
            # Find schedule date tabs and panels
            tabs_locator = page.locator(".p-tabs__navigation__title__link.js-tab-toggle")
            tabs_count = await tabs_locator.count()
            
            panels_locator = page.locator(".p-tabs__body__content")
            panels_count = await panels_locator.count()
            
            print(f"[*] Found {tabs_count} date tabs and {panels_count} panels.")
            
            schedule = []
            for d in range(min(tabs_count, panels_count)):
                date_text = await tabs_locator.nth(d).text_content()
                date_text = date_text.strip()
                
                panel = panels_locator.nth(d)
                items_locator = panel.locator(".m-seminar-list__list__items__item")
                items_count = await items_locator.count()
                print(f"[*] Extracting {items_count} items for date: {date_text}")
                
                for i in range(items_count):
                    item = items_locator.nth(i)
                    
                    # Extract Title & Link
                    title_el = item.locator(".m-seminar-list__list__items__item__title")
                    title = ""
                    link = ""
                    if await title_el.count() > 0:
                        title = (await title_el.text_content()).strip()
                        link_el = title_el.locator("a")
                        if await link_el.count() > 0:
                            href = await link_el.get_attribute("href")
                            if href:
                                link = href if href.startswith("http") else f"{base_url}{href.lstrip('/')}"
                    
                    # Extract Location
                    location_el = item.locator(".m-seminar-list__list__items__item__location")
                    location = ""
                    if await location_el.count() > 0:
                        location = (await location_el.text_content()).replace("\n", " ").strip()
                    
                    # Extract Duration/Time
                    duration_el = item.locator(".m-seminar-list__list__items__item__duration")
                    duration = ""
                    if await duration_el.count() > 0:
                        duration = (await duration_el.text_content()).strip()
                    
                    # Extract Description
                    desc_el = item.locator(".m-seminar-list__list__items__item__description")
                    description = ""
                    if await desc_el.count() > 0:
                        description = (await desc_el.text_content()).strip()
                        
                    schedule.append({
                        "date": date_text,
                        "title": title,
                        "duration": duration,
                        "location": location,
                        "link": link,
                        "description": description
                    })
                
            await browser.close()
            if not schedule:
                raise ValueError("No schedule items found or extracted.")
            return schedule

    except Exception as e:
        print(f"[!] Error during scraping: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        
        if fallback_path and fallback_path.exists():
            print(f"[+] Fallback: Loading previous data from {fallback_path}", file=sys.stdout)
            try:
                if fallback_path.suffix.lower() == ".json":
                    with open(fallback_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        print(f"[+] Successfully loaded {len(data)} items from previous JSON data.", file=sys.stdout)
                        return data
                elif fallback_path.suffix.lower() == ".csv":
                    with open(fallback_path, "r", encoding="utf-8") as f:
                        reader = csv.DictReader(f)
                        data = list(reader)
                        print(f"[+] Successfully loaded {len(data)} items from previous CSV data.", file=sys.stdout)
                        return data
            except Exception as fe:
                print(f"[!] Error reading fallback file: {fe}", file=sys.stderr)
        else:
            print("[!] No fallback path provided or fallback file does not exist.", file=sys.stderr)
            
        return []

def save_to_json(data: list[dict], filepath: Path):
    """Saves the scraped data to a JSON file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[+] Successfully saved {len(data)} items to JSON file: {filepath}")

def save_to_csv(data: list[dict], filepath: Path):
    """Saves the scraped data to a CSV file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    headers = ["date", "title", "duration", "location", "link", "description"]
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for row in data:
            writer.writerow(row)
    print(f"[+] Successfully saved {len(data)} items to CSV file: {filepath}")

def main():
    parser = argparse.ArgumentParser(description="Scrape InfoComm Summit Schedules (Global, India, Asia)")
    parser.add_argument("--show", choices=["global", "india", "asia"], default="india", help="InfoComm show to scrape (default: india)")
    parser.add_argument("--url", help="Override the default URL for the selected show")
    parser.add_argument("--format", choices=["json", "csv"], default="json", help="Output format (json or csv)")
    parser.add_argument("--output", required=True, help="Path to save the output file")
    
    args = parser.parse_args()
    output_path = Path(args.output)
    
    # Resolve the target URL
    target_url = args.url if args.url else SHOW_URLS[args.show]
    
    # Run the async scraper
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    data = loop.run_until_complete(scrape_schedule(target_url, fallback_path=output_path))
    
    if not data:
        print("[!] No data scraped and no fallback available. Exiting.", file=sys.stderr)
        sys.exit(1)
        
    if args.format == "json":
        save_to_json(data, output_path)
    elif args.format == "csv":
        save_to_csv(data, output_path)

if __name__ == "__main__":
    main()
