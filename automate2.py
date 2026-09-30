import os
import csv
import time
import re
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    WebDriverException,
    TimeoutException,
)


# ============================================================
# CONFIGURATION
# ============================================================

URL = (
    "https://isha.sadhguru.org/in/en/yoga-meditation/"
    "yoga-program-for-beginners/hatha-yoga/"
    "courses-by-certified-teachers"
)

BASE_DIR = r"D:\autmate\isha_data"

CSV_FILE = os.path.join(
    BASE_DIR,
    "Isha_Certified_Hatha_Yoga_Teachers.csv"
)

TXT_FILE = os.path.join(
    BASE_DIR,
    "Isha_Certified_Hatha_Yoga_Teachers.txt"
)

CHECKPOINT_FILE = os.path.join(
    BASE_DIR,
    "Isha_Teachers_Checkpoint.csv"
)

STATE_FILE = os.path.join(
    BASE_DIR,
    "Isha_Teachers_State.txt"
)

DEBUG_FILE = os.path.join(
    BASE_DIR,
    "Isha_Debug_Page_Text.txt"
)

MAX_CLICKS = 500

WAIT_AFTER_CLICK = 4

NO_PROGRESS_LIMIT = 5

EXTRACTION_RETRIES = 4

BROWSER_RESTART_LIMIT = 3


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

os.makedirs(BASE_DIR, exist_ok=True)


# ============================================================
# GLOBAL STATE
# ============================================================

driver = None

teachers = []

seen_keys = set()

total_clicks_this_run = 0

browser_restart_count = 0


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_line(text):
    if text is None:
        return ""

    text = str(text)

    text = text.replace("\u00a0", " ")
    text = text.replace("\r", " ")
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()


def normalize_phone(phone):
    phone = normalize_line(phone)

    return re.sub(r"[^0-9+]", "", phone)


def normalize_email(email):
    return normalize_line(email).lower()


def make_key(record):
    name = normalize_line(record.get("Name", "")).lower()
    location = normalize_line(record.get("Location", "")).lower()
    phone = normalize_phone(record.get("Phone", ""))
    email = normalize_email(record.get("Email", ""))

    return (
        name,
        location,
        phone,
        email
    )


# ============================================================
# SAFE ATOMIC WRITE
# ============================================================

def atomic_replace(temp_file, final_file):

    try:
        os.replace(temp_file, final_file)
    except Exception as e:
        print(f"WARNING: Could not replace {final_file}")
        print(e)


# ============================================================
# LOAD EXISTING CSV
# ============================================================

def load_existing_csv():

    global teachers
    global seen_keys

    teachers = []
    seen_keys = set()

    if not os.path.exists(CSV_FILE):

        print()
        print("No existing CSV found.")
        print("Starting a fresh collection.")
        print()

        return

    print()
    print("=" * 70)
    print("LOADING EXISTING DATA")
    print("=" * 70)

    try:

        with open(
            CSV_FILE,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            reader = csv.DictReader(f)

            for row in reader:

                if not row:
                    continue

                record = {
                    "Name": normalize_line(row.get("Name", "")),
                    "Location": normalize_line(row.get("Location", "")),
                    "Phone": normalize_line(row.get("Phone", "")),
                    "Email": normalize_line(row.get("Email", "")),
                    "Website": normalize_line(row.get("Website", "")),
                    "Practices": normalize_line(row.get("Practices", "")),
                }

                if not record["Name"]:
                    continue

                key = make_key(record)

                if key not in seen_keys:

                    teachers.append(record)
                    seen_keys.add(key)

        print(f"Existing records loaded: {len(teachers)}")

    except Exception as e:

        print()
        print("ERROR while loading existing CSV:")
        print(e)

        raise


# ============================================================
# SAVE CSV
# ============================================================

def save_csv():

    temp_file = CSV_FILE + ".tmp"

    try:

        with open(
            temp_file,
            "w",
            encoding="utf-8-sig",
            newline=""
        ) as f:

            fieldnames = [
                "Name",
                "Location",
                "Phone",
                "Email",
                "Website",
                "Practices"
            ]

            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames
            )

            writer.writeheader()

            for record in teachers:

                writer.writerow({
                    "Name": record.get("Name", ""),
                    "Location": record.get("Location", ""),
                    "Phone": record.get("Phone", ""),
                    "Email": record.get("Email", ""),
                    "Website": record.get("Website", ""),
                    "Practices": record.get("Practices", "")
                })

        atomic_replace(temp_file, CSV_FILE)

    except Exception as e:

        print("WARNING: CSV save failed:")
        print(e)

        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass


# ============================================================
# SAVE TXT
# ============================================================

def save_txt():

    temp_file = TXT_FILE + ".tmp"

    try:

        with open(
            temp_file,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                "ISHA CERTIFIED HATHA YOGA TEACHERS\n"
            )

            f.write("=" * 70 + "\n\n")

            f.write(
                f"TOTAL RECORDS: {len(teachers)}\n"
            )

            f.write(
                f"LOAD MORE CLICKS THIS RUN: "
                f"{total_clicks_this_run}\n\n"
            )

            for i, record in enumerate(
                teachers,
                start=1
            ):

                f.write(
                    f"TRAINER {i}\n"
                )

                f.write(
                    "-" * 50 + "\n"
                )

                f.write(
                    f"Name: {record.get('Name', '')}\n"
                )

                f.write(
                    f"Location: {record.get('Location', '')}\n"
                )

                f.write(
                    f"Phone: {record.get('Phone', '')}\n"
                )

                f.write(
                    f"Email: {record.get('Email', '')}\n"
                )

                f.write(
                    f"Website: {record.get('Website', '')}\n"
                )

                f.write(
                    f"Practices: {record.get('Practices', '')}\n"
                )

                f.write("\n")

        atomic_replace(temp_file, TXT_FILE)

    except Exception as e:

        print("WARNING: TXT save failed:")
        print(e)

        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        except:
            pass


# ============================================================
# SAVE CHECKPOINT
# ============================================================

def save_checkpoint(reason="Unknown"):

    save_csv()
    save_txt()

    try:

        with open(
            CHECKPOINT_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                f"Checkpoint reason: {reason}\n"
            )

            f.write(
                f"Records: {len(teachers)}\n"
            )

            f.write(
                f"Clicks this run: "
                f"{total_clicks_this_run}\n"
            )

            f.write(
                f"Timestamp: "
                f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )

    except Exception as e:

        print(
            "WARNING: checkpoint metadata save failed:",
            e
        )

    try:

        with open(
            STATE_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                f"TOTAL_RECORDS={len(teachers)}\n"
            )

            f.write(
                f"CLICKS_THIS_RUN={total_clicks_this_run}\n"
            )

            f.write(
                f"LAST_UPDATE="
                f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            )

    except Exception as e:

        print(
            "WARNING: state save failed:",
            e
        )

    print()
    print("SAVED CHECKPOINT")
    print(f"Reason: {reason}")
    print(f"Records: {len(teachers)}")


# ============================================================
# START BROWSER
# ============================================================

def start_browser():

    global driver

    print()
    print("=" * 70)
    print("STARTING CHROME")
    print("=" * 70)

    options = webdriver.ChromeOptions()

    options.add_argument(
        "--start-maximized"
    )

    options.add_argument(
        "--disable-notifications"
    )

    options.add_argument(
        "--disable-popup-blocking"
    )

    options.add_argument(
        "--disable-dev-shm-usage"
    )

    options.add_argument(
        "--no-sandbox"
    )

    # Keep Chrome visible.
    # DO NOT use headless mode.

    driver = webdriver.Chrome(
        options=options
    )

    driver.set_page_load_timeout(90)

    driver.set_script_timeout(60)

    print("Opening Isha teacher directory...")

    driver.get(URL)

    time.sleep(8)

    print("Page loaded.")

    try:
        driver.execute_script(
            "window.scrollTo(0, 0);"
        )
    except:
        pass

    time.sleep(2)


# ============================================================
# CLOSE BROWSER
# ============================================================

def close_browser():

    global driver

    if driver is not None:

        try:
            driver.quit()
        except:
            pass

        driver = None


# ============================================================
# GET EMAIL OCCURRENCES
# ============================================================

def get_email_occurrences():

    try:

        body_text = driver.find_element(
            By.TAG_NAME,
            "body"
        ).text

        return len(
            re.findall(
                r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
                body_text,
                re.I
            )
        )

    except Exception:

        return 0


# ============================================================
# GET PAGE LINES
# ============================================================

def get_lines(element):

    raw = element.get_attribute(
        "innerText"
    ) or ""

    raw = raw.replace(
        "\u00a0",
        " "
    )

    raw = raw.replace(
        "\r",
        ""
    )

    lines = raw.split("\n")

    result = []

    for line in lines:

        line = normalize_line(line)

        if line:
            result.append(line)

    return result


# ============================================================
# FIND EMAIL
# ============================================================

def find_email(lines):

    email_pattern = re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        re.I
    )

    for i, line in enumerate(lines):

        match = email_pattern.search(line)

        if match:

            return (
                match.group(0),
                i
            )

    return (
        "",
        -1
    )


# ============================================================
# FIND PHONE
# ============================================================

def find_phone(lines):

    phone_pattern = re.compile(
        r"(?<!\d)"
        r"(?:\+?\d[\d\s().-]{7,}\d)"
        r"(?!\d)"
    )

    for i, line in enumerate(lines):

        # Don't mistake email/domain numbers.
        if "@" in line:
            continue

        match = phone_pattern.search(line)

        if match:

            phone = match.group(0).strip()

            digits = re.sub(
                r"\D",
                "",
                phone
            )

            if len(digits) >= 8:

                return (
                    phone,
                    i
                )

    return (
        "",
        -1
    )


# ============================================================
# FIND WEBSITE
# ============================================================

def find_website(lines):

    for line in lines:

        lower = line.lower()

        if (
            lower.startswith("http://")
            or lower.startswith("https://")
            or lower.startswith("www.")
        ):

            return line

    return ""


# ============================================================
# BAD LINE
# ============================================================

def is_bad_name_line(line):

    lower = line.lower().strip()

    bad = [
        "load more",
        "find a teacher",
        "certified teacher",
        "contact",
        "email",
        "phone",
        "website",
        "practice",
        "practices",
        "upayoga",
    ]

    for item in bad:

        if lower == item:
            return True

    return False


# ============================================================
# PARSE ONE CARD
# ============================================================

def parse_card(element):

    try:

        lines = get_lines(element)

    except (
        StaleElementReferenceException,
        WebDriverException
    ):

        return None

    if not lines:
        return None

    email, email_index = find_email(lines)

    phone, phone_index = find_phone(lines)

    if not email:
        return None

    if not phone:
        return None

    # --------------------------------------------------------
    # NAME
    # --------------------------------------------------------

    name = ""

    for line in lines:

        if is_bad_name_line(line):
            continue

        if "@" in line:
            continue

        if re.search(
            r"https?://|www\.",
            line,
            re.I
        ):
            continue

        if re.search(
            r"\d{6,}",
            line
        ):
            continue

        # Skip obvious practice entries.
        if line.lower() in [
            "upa-yoga",
            "angamardana",
            "surya kriya",
            "yogasanas",
            "bhuta shuddhi",
        ]:
            continue

        name = line
        break

    if not name:
        return None

    # --------------------------------------------------------
    # LOCATION
    # --------------------------------------------------------

    location = ""

    start_index = 0

    if name in lines:
        start_index = lines.index(name) + 1

    for i in range(
        start_index,
        len(lines)
    ):

        line = lines[i]

        if not line:
            continue

        if line == phone:
            continue

        if email and email in line:
            continue

        if re.search(
            r"https?://|www\.",
            line,
            re.I
        ):
            continue

        if is_bad_name_line(line):
            continue

        location = line

        break

    # --------------------------------------------------------
    # WEBSITE
    # --------------------------------------------------------

    website = find_website(lines)

    # --------------------------------------------------------
    # PRACTICES
    # --------------------------------------------------------

    practice_list = []

    practice_keywords = [
        "Upa-Yoga",
        "Angamardana",
        "Surya Kriya",
        "Yogasanas",
        "Bhuta Shuddhi",
        "Yoga",
        "Bhuta",
    ]

    for line in lines:

        if line == name:
            continue

        if line == location:
            continue

        if line == phone:
            continue

        if email and email in line:
            continue

        if website and line == website:
            continue

        if line.lower() == "load more":
            continue

        for keyword in practice_keywords:

            if keyword.lower() in line.lower():

                if line not in practice_list:
                    practice_list.append(line)

                break

    practices = ", ".join(
        practice_list
    )

    return {
        "Name": name,
        "Location": location,
        "Phone": phone,
        "Email": email,
        "Website": website,
        "Practices": practices,
    }


# ============================================================
# EXTRACT TRAINERS
# ============================================================

def extract_trainers():

    global driver

    # --------------------------------------------------------
    # Find all elements containing email addresses.
    # Each trainer card normally contains an email.
    # --------------------------------------------------------

    email_elements = driver.find_elements(
        By.XPATH,
        "//*[contains(text(),'@')]"
    )

    candidates = []

    for element in email_elements:

        try:

            current = element

            selected = None

            # Climb only a limited number of ancestors.
            # This prevents selecting the whole page.
            for _ in range(8):

                try:

                    text = current.get_attribute(
                        "innerText"
                    ) or ""

                except (
                    StaleElementReferenceException,
                    WebDriverException
                ):

                    break

                email_count = len(
                    re.findall(
                        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
                        text,
                        re.I
                    )
                )

                if email_count == 1:

                    # Check that this container is
                    # reasonably sized.

                    line_count = len(
                        text.splitlines()
                    )

                    if 3 <= line_count <= 40:

                        selected = current

                        break

                try:
                    current = current.find_element(
                        By.XPATH,
                        ".."
                    )
                except:
                    break

            if selected is not None:
                candidates.append(
                    selected
                )

        except (
            StaleElementReferenceException,
            WebDriverException
        ):

            continue

    # --------------------------------------------------------
    # Remove duplicate DOM elements.
    # --------------------------------------------------------

    unique_elements = []

    seen_text = set()

    for element in candidates:

        try:

            text = element.get_attribute(
                "innerText"
            ) or ""

            signature = (
                text[:1000]
            )

            if signature in seen_text:
                continue

            seen_text.add(signature)

            unique_elements.append(
                element
            )

        except:
            continue

    # --------------------------------------------------------
    # Parse cards.
    # --------------------------------------------------------

    records = []

    local_keys = set()

    for element in unique_elements:

        try:

            record = parse_card(
                element
            )

        except (
            StaleElementReferenceException,
            WebDriverException
        ):

            continue

        if not record:
            continue

        key = make_key(record)

        if key in local_keys:
            continue

        local_keys.add(key)

        records.append(record)

    return records


# ============================================================
# SAFE EXTRACTION WITH RETRIES
# ============================================================

def extract_with_retries():

    last_error = None

    for attempt in range(
        1,
        EXTRACTION_RETRIES + 1
    ):

        try:

            records = extract_trainers()

            return records

        except (
            ConnectionResetError,
            WebDriverException
        ) as e:

            last_error = e

            print()
            print(
                f"Extraction connection error "
                f"(attempt {attempt}/"
                f"{EXTRACTION_RETRIES})"
            )

            print(
                str(e)[:300]
            )

            time.sleep(
                3 * attempt
            )

    print()
    print(
        "Extraction failed after retries."
    )

    if last_error:
        print(
            str(last_error)
        )

    return None


# ============================================================
# ADD NEW RECORDS
# ============================================================

def add_records(records):

    if records is None:
        return 0

    added = 0

    for record in records:

        key = make_key(record)

        if key in seen_keys:
            continue

        teachers.append(record)

        seen_keys.add(key)

        added += 1

    return added


# ============================================================
# SAVE DEBUG PAGE
# ============================================================

def save_debug_page():

    try:

        text = driver.find_element(
            By.TAG_NAME,
            "body"
        ).text

        with open(
            DEBUG_FILE,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(text)

    except Exception as e:

        print(
            "Could not save debug page:",
            e
        )


# ============================================================
# FIND LOAD MORE
# ============================================================

def find_load_more():

    selectors = [

        # Exact button text
        (
            By.XPATH,
            "//button[normalize-space()='Load More']"
        ),

        # Button containing text
        (
            By.XPATH,
            "//button[contains(normalize-space(.),'Load More')]"
        ),

        # Links
        (
            By.XPATH,
            "//a[normalize-space()='Load More']"
        ),

        (
            By.XPATH,
            "//a[contains(normalize-space(.),'Load More')]"
        ),

        # Generic elements
        (
            By.XPATH,
            "//*[normalize-space()='Load More']"
        ),
    ]

    for by, selector in selectors:

        try:

            elements = driver.find_elements(
                by,
                selector
            )

            for element in elements:

                try:

                    if element.is_displayed():
                        return element

                except:
                    continue

        except:
            continue

    return None


# ============================================================
# CLICK LOAD MORE
# ============================================================

def click_load_more():

    button = find_load_more()

    if button is None:

        print()
        print(
            "Load More button NOT found."
        )

        return False

    print(
        "Trainer Load More found."
    )

    # Scroll button into view.

    try:

        driver.execute_script(
            """
            arguments[0].scrollIntoView({
                behavior: 'instant',
                block: 'center'
            });
            """,
            button
        )

        time.sleep(1)

    except:
        pass

    # --------------------------------------------------------
    # PRIMARY: Selenium native click
    # --------------------------------------------------------

    try:

        print(
            "Clicking with Selenium native click..."
        )

        button.click()

        return True

    except Exception as e:

        print(
            "Native click failed:"
        )

        print(
            str(e)[:300]
        )

    # --------------------------------------------------------
    # FALLBACK: ActionChains
    # --------------------------------------------------------

    try:

        print(
            "Trying ActionChains click..."
        )

        button = find_load_more()

        if button is None:
            return False

        ActionChains(
            driver
        ).move_to_element(
            button
        ).pause(
            0.5
        ).click().perform()

        return True

    except Exception as e:

        print(
            "ActionChains click failed:"
        )

        print(
            str(e)[:300]
        )

    return False


# ============================================================
# RESTART BROWSER
# ============================================================

def restart_browser():

    global browser_restart_count

    if browser_restart_count >= BROWSER_RESTART_LIMIT:

        print()
        print(
            "Browser restart limit reached."
        )

        return False

    browser_restart_count += 1

    print()
    print("=" * 70)
    print(
        f"RESTARTING BROWSER "
        f"({browser_restart_count}/"
        f"{BROWSER_RESTART_LIMIT})"
    )
    print("=" * 70)

    try:
        close_browser()
    except:
        pass

    time.sleep(5)

    try:

        start_browser()

        return True

    except Exception as e:

        print(
            "Browser restart failed:"
        )

        print(e)

        return False


# ============================================================
# ADD CURRENT PAGE RECORDS
# ============================================================

def collect_current_page():

    before = len(teachers)

    records = extract_with_retries()

    if records is None:

        return None

    added = add_records(
        records
    )

    after = len(teachers)

    print()
    print(
        f"Currently extractable records: "
        f"{len(records)}"
    )

    print()
    print(
        f"New records added: {added}"
    )

    print(
        f"TOTAL RECORDS: {after}"
    )

    if after > before:

        save_checkpoint(
            "New records extracted"
        )

    return added


# ============================================================
# MAIN
# ============================================================

def main():

    global total_clicks_this_run

    print()
    print("=" * 70)
    print("ISHA CERTIFIED HATHA YOGA TEACHER COLLECTOR")
    print("=" * 70)

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "Existing CSV data will NOT be deleted."
    )

    print(
        "The script will load your existing records "
        "and continue collecting."
    )

    print()

    # --------------------------------------------------------
    # Load existing 162 records
    # --------------------------------------------------------

    load_existing_csv()

    saved_record_count = len(
        teachers
    )

    print()
    print(
        f"RESUME DATASET: "
        f"{saved_record_count} records"
    )

    # --------------------------------------------------------
    # Start Chrome
    # --------------------------------------------------------

    try:

        start_browser()

    except Exception as e:

        print()
        print(
            "Could not start Chrome:"
        )

        print(e)

        return

    # --------------------------------------------------------
    # Initial extraction
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("CHECKING CURRENT PAGE")
    print("=" * 70)

    no_progress = 0

    try:

        current_records = extract_with_retries()

        if current_records is not None:

            added = add_records(
                current_records
            )

            print()
            print(
                f"Currently extractable records: "
                f"{len(current_records)}"
            )

            print(
                f"New records added: {added}"
            )

            print(
                f"TOTAL RECORDS: "
                f"{len(teachers)}"
            )

            if added > 0:

                save_checkpoint(
                    "Initial page extraction"
                )

    except Exception as e:

        print()
        print(
            "Initial extraction failed."
        )

        print(e)

    # --------------------------------------------------------
    # Main Load More loop
    # --------------------------------------------------------

    for round_number in range(
        1,
        MAX_CLICKS + 1
    ):

        print()
        print("=" * 70)
        print(
            f"LOAD MORE ROUND {round_number}"
        )
        print("=" * 70)

        print(
            f"Records saved before click: "
            f"{len(teachers)}"
        )

        before_email_count = (
            get_email_occurrences()
        )

        print(
            f"Email occurrences before click: "
            f"{before_email_count}"
        )

        # ----------------------------------------------------
        # Find button
        # ----------------------------------------------------

        button = find_load_more()

        if button is None:

            print()
            print(
                "NO LOAD MORE BUTTON FOUND."
            )

            print(
                "The directory may have reached "
                "the end."
            )

            save_checkpoint(
                "Load More button disappeared"
            )

            break

        # ----------------------------------------------------
        # Click
        # ----------------------------------------------------

        clicked = click_load_more()

        if not clicked:

            print()
            print(
                "Could not click Load More."
            )

            no_progress += 1

            if no_progress >= NO_PROGRESS_LIMIT:

                print(
                    "Too many failed clicks."
                )

                save_checkpoint(
                    "Too many failed clicks"
                )

                break

            time.sleep(5)

            continue

        total_clicks_this_run += 1

        print(
            f"Click {round_number} completed."
        )

        # ----------------------------------------------------
        # Wait for loading
        # ----------------------------------------------------

        print(
            "Waiting for newly loaded trainers..."
        )

        time.sleep(
            WAIT_AFTER_CLICK
        )

        # ----------------------------------------------------
        # Check email count
        # ----------------------------------------------------

        after_email_count = (
            get_email_occurrences()
        )

        print(
            f"Email occurrences: "
            f"{after_email_count}"
        )

        # ----------------------------------------------------
        # Extract with retries
        # ----------------------------------------------------

        extraction_success = False

        current_records = None

        for extraction_attempt in range(
            1,
            EXTRACTION_RETRIES + 1
        ):

            try:

                current_records = (
                    extract_trainers()
                )

                extraction_success = True

                break

            except (
                ConnectionResetError,
                WebDriverException
            ) as e:

                print()
                print(
                    f"Selenium connection problem "
                    f"during extraction "
                    f"({extraction_attempt}/"
                    f"{EXTRACTION_RETRIES})"
                )

                print(
                    str(e)[:250]
                )

                time.sleep(
                    3 * extraction_attempt
                )

        # ----------------------------------------------------
        # If extraction repeatedly fails
        # ----------------------------------------------------

        if not extraction_success:

            print()
            print(
                "Extraction failed repeatedly."
            )

            print(
                "Saving everything collected so far."
            )

            save_checkpoint(
                "Extraction connection failure"
            )

            # Try browser restart.

            restarted = restart_browser()

            if restarted:

                print()
                print(
                    "Browser restarted."
                )

                print(
                    "The script will continue."
                )

                # We do NOT erase teachers.

                # The page has restarted, so the script
                # may need to rebuild the page state.
                #
                # Stop this run safely rather than
                # accidentally collecting from the wrong
                # point.

                print()
                print(
                    "For safety, this run is stopping "
                    "after the browser restart."
                )

                print(
                    "Your saved CSV remains intact."
                )

            break

        # ----------------------------------------------------
        # Add extracted records
        # ----------------------------------------------------

        previous_total = len(
            teachers
        )

        added = add_records(
            current_records
        )

        current_total = len(
            teachers
        )

        print()
        print(
            f"Currently extractable records: "
            f"{len(current_records)}"
        )

        print()
        print(
            f"New records added: {added}"
        )

        print(
            f"TOTAL RECORDS: {current_total}"
        )

        # ----------------------------------------------------
        # Save after EVERY click
        # ----------------------------------------------------

        save_checkpoint(
            "After Load More click"
        )

        # ----------------------------------------------------
        # Determine progress
        # ----------------------------------------------------

        if (
            added > 0
            or after_email_count > before_email_count
        ):

            no_progress = 0

        else:

            no_progress += 1

        print(
            f"No-progress rounds: "
            f"{no_progress}/"
            f"{NO_PROGRESS_LIMIT}"
        )

        # ----------------------------------------------------
        # Stop after repeated no-progress
        # ----------------------------------------------------

        if no_progress >= NO_PROGRESS_LIMIT:

            print()
            print(
                "No meaningful progress for "
                f"{NO_PROGRESS_LIMIT} rounds."
            )

            print(
                "Stopping safely."
            )

            save_checkpoint(
                "No progress limit reached"
            )

            break

        # ----------------------------------------------------
        # Small delay
        # ----------------------------------------------------

        time.sleep(2)

    # ========================================================
    # FINAL SAVE
    # ========================================================

    print()
    print("=" * 70)
    print("FINAL SAVE")
    print("=" * 70)

    save_checkpoint(
        "Normal script completion"
    )

    save_debug_page()

    print()
    print("=" * 70)
    print("COLLECTION STOPPED")
    print("=" * 70)

    print(
        f"TOTAL RECORDS SAVED: "
        f"{len(teachers)}"
    )

    print(
        f"LOAD MORE CLICKS THIS RUN: "
        f"{total_clicks_this_run}"
    )

    print()
    print(
        f"CSV: {CSV_FILE}"
    )

    print(
        f"TXT: {TXT_FILE}"
    )

    print(
        f"CHECKPOINT: {CHECKPOINT_FILE}"
    )

    print()
    print(
        "Chrome will remain open."
    )

    # Intentionally DON'T close Chrome.


# ============================================================
# CTRL+C / UNEXPECTED ERROR HANDLING
# ============================================================

if __name__ == "__main__":

    try:

        main()

    except KeyboardInterrupt:

        print()
        print("=" * 70)
        print("CTRL+C DETECTED")
        print("=" * 70)

        print(
            "Saving all collected records before stopping..."
        )

        try:
            save_checkpoint(
                "Manual Ctrl+C stop"
            )
        except Exception as e:
            print(
                "Could not save checkpoint:",
                e
            )

        print()
        print(
            f"Records safely saved: "
            f"{len(teachers)}"
        )

        print(
            "You can run the script again later."
        )

        print(
            "Existing CSV data will be loaded automatically."
        )

    except Exception as e:

        print()
        print("=" * 70)
        print("UNEXPECTED ERROR")
        print("=" * 70)

        print(
            repr(e)
        )

        traceback.print_exc()

        print()
        print(
            "Attempting emergency save..."
        )

        try:

            save_checkpoint(
                "Unexpected error"
            )

        except Exception as save_error:

            print(
                "Emergency save also failed:"
            )

            print(
                save_error
            )

        print()
        print(
            f"Records currently in memory: "
            f"{len(teachers)}"
        )

        print(
            "Your previously saved CSV should remain intact."
        )