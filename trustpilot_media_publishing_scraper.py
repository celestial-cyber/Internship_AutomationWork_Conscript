import argparse
import asyncio
import json
import os
import random
import re
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright


DEFAULT_URL = "https://www.trustpilot.com/categories/media_publishing?country=IN"
CATEGORY = "Media & Publishing"
OUTPUT_COLUMNS = [
    "Category",
    "Sub_Category",
    "Company",
    "Reviews",
    "Status",
    "Rating",
    "Verified_Status",
    "Web_site",
    "Contact_no",
    "Email",
    "Address",
    "Location",
    "About",
]

LISTING_TIMEOUT = 60000
DETAIL_TIMEOUT = 60000
DATA_WAIT_TIMEOUT = 30000
PAGE_DELAY_MIN = 700
PAGE_DELAY_MAX = 1500
DETAIL_DELAY_MIN = 700
DETAIL_DELAY_MAX = 1500
LISTING_CONCURRENCY = 2
DETAIL_CONCURRENCY = 1


async def prepare_page(page):
    async def route_handler(route):
        if route.request.resource_type in {"image", "media", "font", "stylesheet"}:
            await route.abort()
        else:
            await route.continue_()

    await page.route("**/*", route_handler)


async def safe_goto(page, target_url, label, timeout):
    for attempt in range(3):
        try:
            await page.goto(target_url, wait_until="domcontentloaded", timeout=timeout)
            await page.wait_for_selector("script#__NEXT_DATA__", state="attached", timeout=DATA_WAIT_TIMEOUT)
            return
        except Exception as e:
            if attempt == 2:
                raise
            print(f"{label} navigation failed (attempt {attempt + 1}): {e}")
            await page.wait_for_timeout(3000)


async def fetch_page_content(page):
    for attempt in range(3):
        try:
            await page.wait_for_timeout(2000)
            return await page.content()
        except Exception as e:
            if attempt == 2:
                raise
            print(f"Content load retry {attempt + 1}: {e}")
            await page.wait_for_timeout(1000)

    return await page.content()


def extract_html_data(html):
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return None
    return json.loads(match.group(1))


async def scrape_listing_page(context, page_no, semaphore, base_url, category):
    async with semaphore:
        page = await context.new_page()
        rows = []
        try:
            await prepare_page(page)
            separator = "&" if "?" in base_url else "?"
            page_url = f"{base_url}{separator}page={page_no}"
            await safe_goto(page, page_url, f"Listing page {page_no}", LISTING_TIMEOUT)

            html = await fetch_page_content(page)
            data = extract_html_data(html)
            if not data:
                print(f"Listing page {page_no}: no JSON data found")
                return rows

            businesses = (
                data.get("props", {})
                .get("pageProps", {})
                .get("businessUnits", {})
                .get("businesses", [])
            )

            for b in businesses:
                contact = b.get("contact", {}) or {}
                location = b.get("location", {}) or {}
                sub_category = next(
                    (c.get("name") or c.get("displayName", "")
                     for c in b.get("categories", []) if c.get("isPrimary")),
                    "",
                )

                rows.append({
                    "Category": category,
                    "Sub_Category": sub_category,
                    "Company": b.get("displayName", ""),
                    "Reviews": b.get("numberOfReviews", ""),
                    "Status": "",
                    "Rating": b.get("trustScore", ""),
                    "Verified_Status": "",
                    "Web_site": contact.get("website", ""),
                    "Contact_no": contact.get("phone") or "Not Added",
                    "Email": contact.get("email") or "Not Added",
                    "Address": location.get("address") or "Not Added",
                    "Location": ", ".join(filter(None, [location.get("city") or "", location.get("country") or ""])),
                    "About": "",
                    "identifyingName": b.get("identifyingName", ""),
                })

            print(f"Listing page {page_no} fetched {len(rows)} companies")
            await page.wait_for_timeout(random.randint(PAGE_DELAY_MIN, PAGE_DELAY_MAX))
        except Exception as exc:
            print(f"Listing page {page_no} failed: {exc}")
        finally:
            await page.close()
        return rows


async def scrape_detail_page(context, row, semaphore):
    async with semaphore:
        page = await context.new_page()
        try:
            await prepare_page(page)
            identifying_name = row.get("identifyingName")
            if not identifying_name:
                row["Verified_Status"] = "Not Verified"
                row["About"] = ""
                row["Status"] = ""
                return row

            profile_url = f"https://www.trustpilot.com/review/{identifying_name}"
            await safe_goto(page, profile_url, f"Detail page {row.get('Company', 'unknown')}", DETAIL_TIMEOUT)
            await page.wait_for_timeout(1500)
            html = await fetch_page_content(page)
            data = extract_html_data(html)

            business = None
            if data:
                business = (
                    data.get("props", {})
                    .get("pageProps", {})
                    .get("businessUnit", {})
                )
                row["Verified_Status"] = "Verified" if business.get("isClaimed", False) else "Not Verified"
            else:
                row["Verified_Status"] = "Not Verified"

            soup = BeautifulSoup(html, "html.parser")
            about = soup.select_one('div[data-html-block="true"].customer-generated-content')
            row["About"] = about.get_text(" ", strip=True) if about else ""

            status = soup.select_one('h3[class*="starRatingName"]')
            row["Status"] = status.get_text(strip=True) if status else ""

            await page.wait_for_timeout(random.randint(DETAIL_DELAY_MIN, DETAIL_DELAY_MAX))
        except Exception as exc:
            print(f"Detail page failed for {row.get('Company', 'unknown')}: {exc}")
            row["Verified_Status"] = row.get("Verified_Status", "Not Verified")
            row["About"] = row.get("About", "")
            row["Status"] = row.get("Status", "")
        finally:
            await page.close()
        return row


def save_progress_to_excel(rows, output_path):
    df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if "identifyingName" in df.columns:
        df = df.drop(columns=["identifyingName"])
    df = df.fillna("Not Added")
    df = df[OUTPUT_COLUMNS]

    try:
        df.to_excel(output_path, index=False)
        print(f"Saved {len(rows)} companies to {output_path}")
        return output_path
    except PermissionError:
        base, ext = os.path.splitext(output_path)
        fallback_output = f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        df.to_excel(fallback_output, index=False)
        print(f"Excel file is locked; saved progress to {fallback_output}")
        return fallback_output


async def process_batch(context, batch_number, batch_start, batch_end, base_url, category, listing_sem, detail_sem):
    listing_tasks = [
        scrape_listing_page(context, page_no, listing_sem, base_url, category)
        for page_no in range(batch_start, batch_end + 1)
    ]
    listing_results = await asyncio.gather(*listing_tasks)

    batch_rows = []
    for page_no, rows in enumerate(listing_results, start=batch_start):
        if rows:
            batch_rows.extend(rows)
            print(f"Merged page {page_no}: {len(rows)} companies")

    print(f"Batch {batch_number} collected {len(batch_rows)} companies")

    updated_rows = []
    for index, row in enumerate(batch_rows, start=1):
        updated_row = await scrape_detail_page(context, row, detail_sem)
        updated_rows.append(updated_row)

    batch_output = f"trustpilot_media_publishing_batch_{batch_number:02d}.xlsx"
    save_progress_to_excel(updated_rows, batch_output)
    return updated_rows, batch_output


async def main():
    args = parse_args()
    browser = None
    all_rows = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=args.headless)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1440, "height": 1200},
                locale="en-US",
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            listing_sem = asyncio.Semaphore(LISTING_CONCURRENCY)
            detail_sem = asyncio.Semaphore(DETAIL_CONCURRENCY)

            total_pages = max(1, args.pages)
            batches = []
            for batch_number in range(1, (total_pages + args.batch_size - 1) // args.batch_size + 1):
                batch_start = (batch_number - 1) * args.batch_size + 1
                batch_end = min(batch_start + args.batch_size - 1, total_pages)
                batch_rows, batch_output = await process_batch(
                    context,
                    batch_number,
                    batch_start,
                    batch_end,
                    DEFAULT_URL,
                    CATEGORY,
                    listing_sem,
                    detail_sem,
                )
                batches.append(batch_output)
                all_rows.extend(batch_rows)

            if all_rows:
                save_progress_to_excel(all_rows, args.output)

            print("\nScraping finished")
            print("Created files:")
            for output in batches:
                print(f" - {output}")
            print(f"Final output: {args.output}")
    except Exception as exc:
        print(f"Scraping stopped with error: {exc}")
    finally:
        if browser:
            await browser.close()


def parse_args():
    parser = argparse.ArgumentParser(description="Scrape Trustpilot Media & Publishing listings for India")
    parser.add_argument("--pages", type=int, default=3, help="Number of listing pages to scrape")
    parser.add_argument("--batch-size", type=int, default=1, help="Number of pages per batch")
    parser.add_argument("--output", default="trustpilot_media_publishing.xlsx", help="Output Excel filename")
    parser.add_argument("--headless", action="store_true", help="Run Playwright in headless mode")
    return parser.parse_args()


if __name__ == "__main__":
    asyncio.run(main())
