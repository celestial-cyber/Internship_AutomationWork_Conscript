#!/usr/bin/env python3
"""
===========================================================
Trustpilot Money & Insurance (India) Scraper
===========================================================

Author : ChatGPT
Purpose:
    Scrape Trustpilot Money & Insurance category (India)
    Save results into Excel
    Resume automatically after interruption
    Save progress after every listing page

Output Columns
--------------
Category
Sub_Category
Company
Reviews
Status
Rating
Verified_Status
Web_site
Contact_no
Email
Address
Location
About

===========================================================
"""

# ===========================
# IMPORTS
# ===========================

import requests
import pandas as pd
import json
import re
import time
import random
import logging
import os

from bs4 import BeautifulSoup
from datetime import datetime
from typing import Dict, List, Optional


# ===========================
# CONFIGURATION
# ===========================

CATEGORY = "Money & Insurance"

BASE_URL = "https://www.trustpilot.com"

LISTING_URL = (
    "https://www.trustpilot.com/categories/"
    "money_insurance?country=IN"
)

OUTPUT_FILE = "trustpilot_money_insurance.xlsx"

PROGRESS_FILE = "progress.txt"

REQUEST_TIMEOUT = 30

MAX_RETRIES = 3

SLEEP_MIN = 1.5

SLEEP_MAX = 3.5


# ===========================
# USER AGENTS
# ===========================

HEADERS = [

{
"User-Agent":
"Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
" AppleWebKit/537.36"
" Chrome/125.0 Safari/537.36"
},

{
"User-Agent":
"Mozilla/5.0 (X11; Linux x86_64)"
" AppleWebKit/537.36"
" Chrome/124.0 Safari/537.36"
},

{
"User-Agent":
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
" AppleWebKit/537.36"
" Chrome/124.0 Safari/537.36"
}

]


# ===========================
# LOGGING
# ===========================

logging.basicConfig(

level=logging.INFO,

format="%(asctime)s | %(levelname)s | %(message)s",

handlers=[

logging.FileHandler(
"trustpilot_scraper.log",
encoding="utf-8"
),

logging.StreamHandler()

]

)

logger = logging.getLogger(__name__)


# ===========================
# CREATE SESSION
# ===========================

def create_session():

    """
    Creates a reusable HTTP session.

    Session keeps cookies
    and reuses TCP connections.

    Much faster than
    requests.get() every time.
    """

    session = requests.Session()

    session.headers.update(
        random.choice(HEADERS)
    )

    return session


# ===========================
# RANDOM DELAY
# ===========================

def polite_sleep():

    """
    Random delay
    to reduce rate limiting.
    """

    time.sleep(

        random.uniform(
            SLEEP_MIN,
            SLEEP_MAX
        )

    )


# ===========================
# SAVE PROGRESS
# ===========================

def save_progress(page):

    with open(PROGRESS_FILE, "w") as f:

        f.write(str(page))


# ===========================
# LOAD PROGRESS
# ===========================

def load_progress():

    if not os.path.exists(PROGRESS_FILE):

        return 1

    try:

        with open(PROGRESS_FILE) as f:

            return int(f.read().strip())

    except:

        return 1


# ===========================
# LOAD OLD EXCEL
# ===========================

def load_existing_data():

    """
    Resume previous scraping.
    """

    if os.path.exists(OUTPUT_FILE):

        logger.info(
            "Existing Excel found."
        )

        return pd.read_excel(
            OUTPUT_FILE
        ).to_dict("records")

    return []


# ===========================
# SAVE EXCEL
# ===========================

def save_excel(rows):

    df = pd.DataFrame(rows)

    columns = [

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

    df = df[columns]

    df.to_excel(

        OUTPUT_FILE,

        index=False

    )


# ===========================
# FETCH PAGE
# ===========================

def fetch_page(

        session,

        url,

        params=None

):

    """
    Download page with retries.
    """

    for attempt in range(MAX_RETRIES):

        try:

            response = session.get(

                url,

                params=params,

                timeout=REQUEST_TIMEOUT

            )

            if response.status_code == 200:

                return response.text

        except Exception as e:

            logger.warning(

                f"Retry {attempt+1} : {e}"

            )

        polite_sleep()

    return None


# ===========================
# EXTRACT NEXT DATA
# ===========================

def extract_json(html):

    """
    Trustpilot stores
    everything inside

    __NEXT_DATA__
    """

    match = re.search(

        r'<script id="__NEXT_DATA__".*?>(.*?)</script>',

        html,

        re.DOTALL

    )

    if not match:

        return None

    return json.loads(

        match.group(1)

    )


# ===========================
# DUPLICATE CHECK
# ===========================

def already_exists(

        company,

        rows

):

    return any(

        r["Company"] == company

        for r in rows

    )


logger.info(

    "="*60

)

logger.info(

    "Trustpilot Scraper Started"

)

logger.info(

    "="*60

)
# ==========================================================
# LISTING PAGE SCRAPER
# ==========================================================

def scrape_listing_page(session, page_number):
    """
    Scrapes one Trustpilot listing page.

    Returns
    -------
    list
        List of companies found on that page.
    """

    logger.info(f"\nScraping Listing Page {page_number}")

    # First page doesn't require &page=1
    if page_number == 1:
        url = LISTING_URL
    else:
        url = f"{LISTING_URL}&page={page_number}"

    html = fetch_page(session, url)

    if html is None:
        logger.warning(f"Unable to fetch page {page_number}")
        return []

    data = extract_json(html)

    if data is None:
        logger.warning(f"JSON not found on page {page_number}")
        return []

    # ======================================================
    # Navigate through __NEXT_DATA__
    # ======================================================

    try:

        businesses = (
            data["props"]
                ["pageProps"]
                ["businessUnits"]
                ["businesses"]
        )

    except Exception as e:

        logger.error(
            f"JSON structure changed : {e}"
        )

        return []

    page_rows = []

    for business in businesses:

        try:

            contact = business.get("contact", {}) or {}

            location = business.get("location", {}) or {}

            categories = business.get(
                "categories",
                []
            )

            primary_category = ""

            for category in categories:

                if category.get("isPrimary"):

                    primary_category = (
                        category.get("displayName")
                        or
                        category.get("name")
                        or
                        ""
                    )

                    break

            row = {

                "Category":
                    CATEGORY,

                "Sub_Category":
                    primary_category,

                "Company":
                    business.get(
                        "displayName",
                        ""
                    ),

                "Reviews":
                    business.get(
                        "numberOfReviews",
                        ""
                    ),

                "Status":
                    "",

                "Rating":
                    business.get(
                        "trustScore",
                        ""
                    ),

                "Verified_Status":
                    "",

                "Web_site":
                    contact.get(
                        "website",
                        "Not Added"
                    ),

                "Contact_no":
                    "Not Added",

                "Email":
                    "Not Added",

                "Address":
                    "Not Added",

                "Location":
                    ", ".join(

                        filter(

                            None,

                            [

                                location.get("city"),

                                location.get("country")

                            ]

                        )

                    ),

                "About":
                    "",

                # Internal value
                "identifyingName":
                    business.get(
                        "identifyingName",
                        ""
                    )

            }

            page_rows.append(row)

        except Exception as e:

            logger.warning(
                f"Company skipped : {e}"
            )

    logger.info(
        f"Found {len(page_rows)} companies."
    )

    return page_rows


# ==========================================================
# SCRAPE ALL LISTING PAGES
# ==========================================================

def scrape_all_listing_pages(
        session,
        start_page,
        existing_rows
):

    """
    Scrapes every listing page.

    Saves Excel after each page.

    Automatically resumes.
    """

    all_rows = existing_rows.copy()

    page = start_page

    empty_pages = 0

    while True:

        polite_sleep()

        page_rows = scrape_listing_page(
            session,
            page
        )

        if len(page_rows) == 0:

            empty_pages += 1

            logger.info(
                f"No companies on page {page}"
            )

            # Stop after 3 consecutive empty pages
            if empty_pages >= 3:

                logger.info(
                    "Reached end of listing pages."
                )

                break

        else:

            empty_pages = 0

            added = 0

            for row in page_rows:

                if not already_exists(
                        row["Company"],
                        all_rows
                ):

                    all_rows.append(row)

                    added += 1

            logger.info(
                f"Added {added} new companies."
            )

            # Save Excel after every page
            save_excel(all_rows)

            # Save progress
            save_progress(page)

            logger.info(
                f"Excel Updated ({len(all_rows)} companies)"
            )

        page += 1

    return all_rows

# ==========================================================
# DETAIL PAGE SCRAPER
# ==========================================================

def scrape_company_detail(session, row):
    """
    Scrape one company's Trustpilot profile.

    Fills:
        Status
        Verified_Status
        Contact_no
        Email
        Address
        About
    """

    identifying_name = row.get("identifyingName", "")

    if not identifying_name:
        return row

    profile_url = (
        BASE_URL +
        "/review/" +
        identifying_name
    )

    logger.info(
        f"Company : {row['Company']}"
    )

    html = fetch_page(
        session,
        profile_url
    )

    if html is None:
        logger.warning(
            "Unable to fetch company page."
        )
        return row

    # -----------------------------------
    # Extract JSON
    # -----------------------------------

    data = extract_json(html)

    if data:

        try:

            business = (
                data["props"]
                    ["pageProps"]
                    ["businessUnit"]
            )

            # -----------------------------------
            # Verified
            # -----------------------------------

            row["Verified_Status"] = (
                "Verified"
                if business.get(
                    "isClaimed",
                    False
                )
                else "Not Verified"
            )

            # -----------------------------------
            # Contact Information
            # -----------------------------------

            contact = business.get(
                "contactInfo",
                {}
            )

            row["Email"] = (

                contact.get(
                    "email"
                )

                or

                "Not Added"

            )

            row["Contact_no"] = (

                contact.get(
                    "phone"
                )

                or

                "Not Added"

            )

            row["Address"] = (

                contact.get(
                    "address"
                )

                or

                "Not Added"

            )

            # Sometimes website is present here

            if row["Web_site"] == "Not Added":

                row["Web_site"] = (

                    contact.get(
                        "website"
                    )

                    or

                    row["Web_site"]

                )

        except Exception as e:

            logger.warning(
                f"JSON parsing failed : {e}"
            )

    # -----------------------------------
    # HTML Parsing
    # -----------------------------------

    soup = BeautifulSoup(
        html,
        "lxml"
    )

    # -----------------------------------
    # Status
    # -----------------------------------

    status = soup.select_one(
        'h3[class*="starRatingName"]'
    )

    if status:

        row["Status"] = status.get_text(
            " ",
            strip=True
        )

    # -----------------------------------
    # About
    # -----------------------------------

    about = soup.select_one(

        'div[data-html-block="true"].customer-generated-content'

    )

    if about:

        row["About"] = about.get_text(

            " ",

            strip=True

        )

    polite_sleep()

    return row


# ==========================================================
# SCRAPE ALL DETAIL PAGES
# ==========================================================

def scrape_all_details(
        session,
        rows
):
    """
    Visit every company profile
    and complete the remaining columns.
    """

    total = len(rows)

    logger.info(
        "\nStarting Detail Scraping...\n"
    )

    for index, row in enumerate(rows, start=1):

        logger.info(

            f"[{index}/{total}] "

            f"{row['Company']}"

        )

        rows[index - 1] = scrape_company_detail(
            session,
            row
        )

        # Remove helper column before saving

        save_rows = []

        for r in rows:

            temp = r.copy()

            temp.pop(
                "identifyingName",
                None
            )

            save_rows.append(
                temp
            )

        save_excel(
            save_rows
        )

    return rows
# ==========================================================
# MAIN SCRAPER
# ==========================================================

class TrustpilotScraper:

    def __init__(self):

        logger.info("Creating HTTP Session...")

        self.session = create_session()

        logger.info("Loading previous Excel...")

        self.rows = load_existing_data()

        logger.info(
            f"Existing companies : {len(self.rows)}"
        )

    def run(self):

        # Resume automatically

        start_page = load_progress()

        logger.info(
            f"Resuming from page {start_page}"
        )

        # ---------------------------------------
        # STEP 1
        # Listing Pages
        # ---------------------------------------

        self.rows = scrape_all_listing_pages(

            self.session,

            start_page,

            self.rows

        )

        logger.info(

            f"\nListing Completed."

        )

        logger.info(

            f"Total Companies : {len(self.rows)}"

        )

        # ---------------------------------------
        # STEP 2
        # Detail Pages
        # ---------------------------------------

        self.rows = scrape_all_details(

            self.session,

            self.rows

        )

        # ---------------------------------------
        # Remove helper column
        # ---------------------------------------

        final_rows = []

        for row in self.rows:

            temp = row.copy()

            temp.pop(

                "identifyingName",

                None

            )

            final_rows.append(temp)

        save_excel(final_rows)

        logger.info("\n")

        logger.info("=" * 60)

        logger.info("SCRAPING FINISHED")

        logger.info("=" * 60)

        logger.info(

            f"Total Companies : {len(final_rows)}"

        )

        logger.info(

            f"Excel Saved : {OUTPUT_FILE}"

        )


# ==========================================================
# ENTRY POINT
# ==========================================================

def main():

    start = datetime.now()

    logger.info(

        f"Started : {start}"

    )

    scraper = TrustpilotScraper()

    scraper.run()

    end = datetime.now()

    logger.info(

        f"Finished : {end}"

    )

    logger.info(

        f"Execution Time : {end - start}"

    )


if __name__ == "__main__":

    main()