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
import re
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Base category URL
url = "https://www.trustpilot.com/categories/money_insurance?country=IN"

# Used in Excel output
category = "Money & Insurance"

# Number of listing pages to visit
START_PAGE = int(input("Enter Start Page: "))
END_PAGE = int(input("Enter End Page: "))
PROGRESS_FILE="progress.txt"

LISTING_CONCURRENCY = 2
DETAIL_CONCURRENCY = 3


def save_progress(page):
    with open(PROGRESS_FILE,"w") as f:
        f.write(f"Last Completed Page: {page}\n")
        f.write(f"Next Start Page: {page+1}\n")

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
            separator = "&" if "?" in url else "?"
            page_url = f"{url}{separator}page={page_no}"

            await page.goto(page_url, wait_until="networkidle", timeout=30000)

            data = extract_html_data(await page.content())
            if not data:
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

            save_progress(page_no)
            print(f"✓ Listing page {page_no} completed")

        except Exception as e:
            print(e)
        finally:
            await page.close()
        return rows

async def scrape_detail_page(browser,row,semaphore):
    async with semaphore:
        page = await browser.new_page()
        try:
            profile=f"https://www.trustpilot.com/review/{row['identifyingName']}"
            await page.goto(profile,wait_until="networkidle",timeout=30000)

            html=await page.content()
            data=extract_html_data(html)

            if data:
                business=(data.get("props",{})
                            .get("pageProps",{})
                            .get("businessUnit",{}))
                row["Verified_Status"]="Verified" if business.get("isClaimed",False) else "Not Verified"

            soup=BeautifulSoup(html,"html.parser")

            about=soup.select_one('div[data-html-block="true"].customer-generated-content')
            row["About"]=about.get_text(" ",strip=True) if about else ""

            status=soup.select_one('h3[class*="starRatingName"]')
            row["Status"]=status.get_text(strip=True) if status else ""

        except Exception:
            row["Verified_Status"]="Not Verified"
        finally:
            await page.close()
        return row

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)

        listing_sem=asyncio.Semaphore(LISTING_CONCURRENCY)
        listing_tasks=[scrape_listing_page(browser,i,listing_sem) for i in range(START_PAGE,END_PAGE+1)]
        listing_results=await asyncio.gather(*listing_tasks)

        rows=[]
        for r in listing_results:
            rows.extend(r)

        print(f"Collected {len(rows)} companies")

        detail_sem=asyncio.Semaphore(DETAIL_CONCURRENCY)
        detail_tasks=[scrape_detail_page(browser,r,detail_sem) for r in rows]
        rows=await asyncio.gather(*detail_tasks)

        await browser.close()

    df=pd.DataFrame(rows)
    df=df.drop(columns=["identifyingName"])
    df=df.fillna("Not Added")

    df=df[[
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
    ]]

    output=f"trustpilot_pages_{START_PAGE}_to_{END_PAGE}.xlsx"
    df.to_excel(output,index=False)
    print(f"Saved to {output}")

if __name__=="__main__":
    asyncio.run(main())
