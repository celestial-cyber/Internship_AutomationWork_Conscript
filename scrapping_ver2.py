# Trustpilot Money & Insurance (India) Scraper
# ---------------------------------------------------------
# This script scrapes Trustpilot's Money & Insurance category
# for India and exports the data to an Excel file.
#
# WHY Playwright?
# Trustpilot is a dynamic website. Playwright waits for the
# page to fully render before extracting data.
#
# Install:
# pip install playwright pandas beautifulsoup4 openpyxl
# playwright install
#
import asyncio
import json
import os
import re
from datetime import datetime
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import random


# Base category URL
url = "https://www.trustpilot.com/categories/media_publishing?country=IN"

# Used in Excel output
category = "Media Publishing"

# Number of listing pages to visit
pages = 112

# Process the site in batches so progress is saved incrementally.
BATCH_SIZE = 50

# Trustpilot rate limits aggressively.
# Moderate concurrency improves throughput while keeping requests stable.
LISTING_CONCURRENCY = 2
DETAIL_CONCURRENCY = 1

LISTING_TIMEOUT = 45000
DETAIL_TIMEOUT = 60000
DATA_WAIT_TIMEOUT = 20000

PAGE_DELAY_MIN = 500
PAGE_DELAY_MAX = 1500
DETAIL_DELAY_MIN = 500
DETAIL_DELAY_MAX = 1500

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
    "About"
]


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
            await page.wait_for_selector('script#__NEXT_DATA__',state="attached", timeout=DATA_WAIT_TIMEOUT)
            return
        except Exception as e:
            if attempt == 2:
                raise
            print(f"{label} navigation failed (attempt {attempt+1}): {e}")
            await page.wait_for_timeout(3000)


async def fetch_page_content(page):
    for attempt in range(3):
        try:
            await page.wait_for_timeout(2000)
            return await page.content()

        except Exception as e:
            if attempt == 2:
                raise

            print(f"Content load retry {attempt+1}: {e}")
            await page.wait_for_timeout(1000)

    return await page.content()


def extract_html_data(html):
    # Trustpilot stores page data inside __NEXT_DATA__ JSON.
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return None
    return json.loads(match.group(1))

async def scrape_listing_page(browser, page_no, semaphore):
    async with semaphore:
        page = await browser.new_page()
        rows = []
        try:
            await prepare_page(page)
            separator = "&" if "?" in url else "?"
            page_url = f"{url}{separator}page={page_no}"

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
                     for c in b.get("categories", [])
                     if c.get("isPrimary")),
                    ""
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
                    "Location": ", ".join(filter(None,[location.get("city") or "",location.get("country") or ""])),
                    "About": "",
                    "identifyingName": b.get("identifyingName","")
                })

            print("=" * 60)
            print(f"Listing Page : {page_no}")
            print(f"Companies Found : {len(rows)}")
            print("=" * 60)
            await page.wait_for_timeout(random.randint(PAGE_DELAY_MIN, PAGE_DELAY_MAX))

        except Exception as e:
            print(e)
        finally:
            await page.close()
        return rows

async def scrape_detail_page(browser, row, semaphore):
    async with semaphore:
        page = await browser.new_page()
        try:
            await prepare_page(page)
            profile = f"https://www.trustpilot.com/review/{row['identifyingName']}"
            await safe_goto(page, profile, f"Detail page {row.get('Company','unknown')}", DETAIL_TIMEOUT)

            await page.wait_for_timeout(1500)
            html = await fetch_page_content(page)
            data = extract_html_data(html)

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
            print(f"Detail page completed for {row.get('Company','unknown')}")
        except Exception as e:
            print(f"Detail page failed for {row.get('Company','unknown')}: {e}")
            row["Verified_Status"] = row.get("Verified_Status", "Not Verified")
            row["About"] = row.get("About", "")
            row["Status"] = row.get("Status", "")
        finally:
            await page.close()
        return row

def save_progress_to_excel(rows, output):
    df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if "identifyingName" in df.columns:
        df = df.drop(columns=["identifyingName"])
    df = df.fillna("Not Added")
    df = df[OUTPUT_COLUMNS]

    try:
        df.to_excel(output, index=False)
        print(f"Saved {len(rows)} companies to {output}")
        return output
    except PermissionError as exc:
        base, ext = os.path.splitext(output)
        fallback_output = f"{base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
        try:
            df.to_excel(fallback_output, index=False)
            print(f"Excel file is locked; saved progress to {fallback_output}")
            return fallback_output
        except Exception as fallback_exc:
            print(f"Could not save Excel file to {output} or {fallback_output}: {fallback_exc}")
            raise


async def process_batch(browser, batch_number, batch_start, batch_end, listing_sem, detail_sem):
    listing_tasks = [
        scrape_listing_page(browser, page_no, listing_sem)
        for page_no in range(batch_start, batch_end + 1)
    ]
    listing_results = await asyncio.gather(*listing_tasks)

    batch_rows = []
    for page_no, rows in enumerate(listing_results, start=batch_start):
        if rows:
            batch_rows.extend(rows)
            print(f"Listing results merged: page {page_no} -> total rows {len(rows)}")

    print(f"\nBatch {batch_number} collected {len(batch_rows)} companies from pages {batch_start}-{batch_end}")

    updated_rows = []
    batch_output = f"trustpilot_money_insurance_india_batch_{batch_number:02d}.xlsx"

    for i, row in enumerate(batch_rows, start=1):
        print(f"[{batch_number}:{i}/{len(batch_rows)}] {row['Company']}")
        updated_row = await scrape_detail_page(browser, row, detail_sem)
        updated_rows.append(updated_row)
        save_progress_to_excel(updated_rows, batch_output)

    return updated_rows, batch_output


async def main():
    browser = None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False, slow_mo=300)

            listing_sem = asyncio.Semaphore(LISTING_CONCURRENCY)
            detail_sem = asyncio.Semaphore(DETAIL_CONCURRENCY)

            total_batches = (pages + BATCH_SIZE - 1) // BATCH_SIZE
            all_batch_outputs = []

            for batch_number in range(2, total_batches + 1):
                batch_start = (batch_number - 1) * BATCH_SIZE + 1
                batch_end = min(batch_start + BATCH_SIZE - 1, pages)

                print("\n" + "=" * 60)
                print(f"STARTING BATCH {batch_number}/{total_batches}")
                print(f"Pages {batch_start}-{batch_end}")
                print("=" * 60)

                _, batch_output = await process_batch(
                    browser,
                    batch_number,
                    batch_start,
                    batch_end,
                    listing_sem,
                    detail_sem
                )
                all_batch_outputs.append(batch_output)

            print("\n" + "=" * 60)
            print("SCRAPING FINISHED")
            print("=" * 60)
            print(f"Total Pages Scraped : {pages}")
            print(f"Batches Created : {len(all_batch_outputs)}")
            print("Batch Files:")
            for output in all_batch_outputs:
                print(f" - {output}")
            print("=" * 60)
    except Exception as e:
        print(f"Scraping stopped with error: {e}")
    finally:
        if browser:
            await browser.close()

if __name__=="__main__":
    asyncio.run(main())
