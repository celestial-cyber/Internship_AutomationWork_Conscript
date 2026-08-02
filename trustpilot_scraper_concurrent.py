import asyncio
import json
import re

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

url = "https://www.trustpilot.com/categories/business_services"
category = "Business Services"
pages = 500

LISTING_CONCURRENCY = 8
DETAIL_CONCURRENCY = 15

def extract_html_data(html):
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',html,re.DOTALL,)
    if not match:
        return None
    return json.loads(match.group(1))


async def scrape_listing_page(browser, page_no, semaphore):
    async with semaphore:
        page = await browser.new_page()
        rows = []
        try:
            page_url = f"{url}?page={page_no}"
            await page.goto(page_url,wait_until="networkidle",timeout=30000,)
            html = await page.content()
            data = extract_html_data(html)

            if not data:
                print(f"Listing {page_no}: JSON not found")
                return rows

            businesses = data["props"]["pageProps"]["businessUnits"]["businesses"]
            for b in businesses:
                contact = b.get("contact", {}) or {}
                location = b.get("location", {}) or {}
                sub_category = next((c.get("name") or c.get("displayName", "")
                                    for c in b.get("categories", []) if c.get("isPrimary")), "")

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
                    "Location": ", ".join(filter(None,[location.get("city") or "",location.get("country") or "",])),
                    "About": "",
                    "identifyingName": b.get("identifyingName", ""),
                })

            print(f"Listing {page_no} done ({len(businesses)} companies)")

        except Exception as e:
            print(f"Listing {page_no} failed: {e}")

        finally:
            await page.close()

        return rows


async def scrape_detail_page(browser, row, semaphore):
    async with semaphore:
        page = await browser.new_page()
        try:
            profile = (f"https://www.trustpilot.com/review/"f"{row['identifyingName']}")

            await page.goto(profile,wait_until="networkidle",timeout=30000)
            html = await page.content()
            data = extract_html_data(html)

            if data:
                business = data["props"]["pageProps"]["businessUnit"]
                row["Verified_Status"] = ("Verified" if business.get("isClaimed", False) else "Not Verified")

            soup = BeautifulSoup(html, "html.parser")
            about = soup.select_one('div[data-html-block="true"].customer-generated-content')

            row["About"] = (about.get_text(" ", strip=True) if about else "")

            status = soup.select_one('h3[class*="starRatingName"]')

            row["Status"] = (status.get_text(strip=True) if status else "")

        except Exception as e:
            print(f"{row['Company']} failed: {e}")

            row["Verified_Status"] = (row.get("Verified_Status") or "Not Verified")

        finally:
            await page.close()

        return row


async def main():

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        print("Scraping listing pages...")
        listing_semaphore = asyncio.Semaphore(LISTING_CONCURRENCY)

        listing_tasks = [
            scrape_listing_page(browser,page_no,listing_semaphore)
                for page_no in range(1, pages + 1)
            ]

        listing_results = await asyncio.gather(*listing_tasks)
        all_rows = []

        for rows in listing_results:
            all_rows.extend(rows)

        print(f"Collected {len(all_rows)} businesses")

        print("Scraping company detail pages...")

        detail_semaphore = asyncio.Semaphore(DETAIL_CONCURRENCY)

        detail_tasks = [
            scrape_detail_page(browser,row,detail_semaphore)
                for row in all_rows
            ]

        all_rows = await asyncio.gather(*detail_tasks)

        await browser.close()

    df = pd.DataFrame(all_rows)
    df = df.drop(columns=["identifyingName"])
    df = df.fillna("Not Added")

    column_order = [
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

    df = df[column_order]
    output_file = "trustpilot_business_services.xlsx"
    df.to_excel(output_file,index=False)
    print(f"Saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())