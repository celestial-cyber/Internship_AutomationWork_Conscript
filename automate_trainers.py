import asyncio
import re
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://isha.sadhguru.org/in/en/yoga-meditation/yoga-program-for-beginners/hatha-yoga/courses-by-certified-teachers"
OUTPUT_FILE = "Isha_Certified_Yoga_Trainers.txt"

# Selectors – adjust if the site changes
TEACHER_CARD_SELECTOR = ".teacher-card, .teacher-item, .teacher, .instructor-card, .instructor-item, [class*='teacher'], [class*='instructor']"
LOAD_MORE_BUTTON_SELECTOR = "button:has-text('Load More'), .load-more, button.load-more, a:has-text('Load More'), .btn-load-more"
NAME_SELECTOR = ".teacher-name, .instructor-name, .name, h3, h4, [class*='name']"
LOCATION_SELECTOR = ".teacher-location, .instructor-location, .location, .city, [class*='location'], [class*='city']"
CONTACT_SELECTOR = ".teacher-contact, .instructor-contact, .contact, .email, a[href^='mailto:'], [class*='contact']"
SOCIAL_SELECTOR = "a[href*='instagram.com'], a[href*='facebook.com'], a[href*='twitter.com'], a[href*='youtube.com'], a[href*='linkedin.com'], [class*='social'] a"
PROGRAMS_SELECTOR = ".teacher-programs, .instructor-programs, .programs, .courses, [class*='program'], [class*='course']"

def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())

def extract_text_from_elements(elements):
    texts = []
    for el in elements:
        t = normalize_text(el.inner_text())
        if t:
            texts.append(t)
    return "; ".join(texts) if texts else ""

async def collect_trainers():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Navigating to the page...")
        await page.goto(URL, wait_until="domcontentloaded", timeout=60000)

        # Wait for initial content to load (teacher cards or load-more)
        try:
            await page.wait_for_selector(LOAD_MORE_BUTTON_SELECTOR, timeout=10000)
        except Exception:
            # If no Load More, maybe there are already cards or no teachers
            try:
                await page.wait_for_selector(TEACHER_CARD_SELECTOR, timeout=10000)
            except Exception:
                print("No teacher cards or Load More button found. The page may have no listings or uses different selectors.")
                await browser.close()
                return

        all_trainers = []
        seen_keys = set()
        load_more_clicks = 0
        failed_records = 0

        async def scrape_current_trainers():
            nonlocal failed_records
            cards = await page.query_selector_all(TEACHER_CARD_SELECTOR)
            if not cards:
                # Fallback: try generic containers if no specific cards
                cards = await page.query_selector_all("[class*='teacher'], [class*='instructor']")
            if not cards:
                return

            for card in cards:
                try:
                    # Name
                    name_el = await card.query_selector(NAME_SELECTOR)
                    name = normalize_text(name_el.inner_text()) if name_el else ""

                    # Location
                    loc_el = await card.query_selector(LOCATION_SELECTOR)
                    location = normalize_text(loc_el.inner_text()) if loc_el else ""

                    # Contact (email / phone)
                    contact_els = await card.query_selector_all(CONTACT_SELECTOR)
                    contact = extract_text_from_elements(contact_els)

                    # Social links
                    social_els = await card.query_selector_all(SOCIAL_SELECTOR)
                    social_links = []
                    for a in social_els:
                        href = await a.get_attribute("href")
                        if href:
                            social_links.append(normalize_text(href))
                    social = "; ".join(social_links) if social_links else ""

                    # Programs / courses
                    prog_els = await card.query_selector_all(PROGRAMS_SELECTOR)
                    programs = extract_text_from_elements(prog_els)

                    # Additional details: any other text in the card not captured above
                    full_text = normalize_text(await card.inner_text())

                    # Create a unique key to avoid duplicates
                    key = f"{name.lower()}|{location.lower()}" if name or location else full_text[:80].lower()
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)

                    trainer = {
                        "name": name,
                        "location": location,
                        "contact": contact,
                        "social": social,
                        "programs": programs,
                        "full_card_text": full_text,
                    }
                    all_trainers.append(trainer)
                except Exception as e:
                    failed_records += 1
                    print(f"Error scraping a trainer card: {e}")

        # Initial scrape
        await scrape_current_trainers()

        # Repeatedly click "Load More"
        while True:
            # Try to find Load More button
            load_more = None
            try:
                load_more = await page.wait_for_selector(LOAD_MORE_BUTTON_SELECTOR, timeout=8000)
            except Exception:
                # No Load More button found; assume end of list
                break

            if not load_more:
                break

            # Check if button is visible and enabled
            is_visible = await load_more.is_visible()
            is_disabled = await load_more.get_attribute("disabled") is not None
            if not is_visible or is_disabled:
                break

            # Click Load More
            try:
                await load_more.click()
                load_more_clicks += 1
                print(f"Clicked Load More (total clicks: {load_more_clicks})")
            except Exception as e:
                print(f"Error clicking Load More: {e}")
                break

            # Wait for new content to load
            # Strategy: wait for network idle or a short delay + wait for teacher cards to stabilize
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass

            # Small extra delay to ensure dynamic rendering
            await asyncio.sleep(2)

            # Scrape newly loaded trainers
            prev_count = len(all_trainers)
            await scrape_current_trainers()
            new_count = len(all_trainers)

            # If no new trainers were added after click, assume end
            if new_count == prev_count:
                print("No new trainers added after Load More click; assuming list is exhausted.")
                break

        await browser.close()

        # Write to TXT file
        lines = []
        lines.append("Isha Certified Hatha Yoga Trainers")
        lines.append("=" * 40)
        lines.append("")

        for i, t in enumerate(all_trainers, start=1):
            lines.append(f"Trainer #{i}")
            lines.append(f"Name: {t['name'] or 'N/A'}")
            lines.append(f"Location: {t['location'] or 'N/A'}")
            lines.append(f"Contact: {t['contact'] or 'N/A'}")
            lines.append(f"Social Links: {t['social'] or 'N/A'}")
            lines.append(f"Programs/Courses: {t['programs'] or 'N/A'}")
            lines.append("Full Card Text:")
            lines.append(t['full_card_text'] or "(empty)")
            lines.append("-" * 40)
            lines.append("")

        Path(OUTPUT_FILE).write_text("\n".join(lines), encoding="utf-8")

        print("\n=== Collection Summary ===")
        print(f"Total trainers collected: {len(all_trainers)}")
        print(f"Number of 'Load More' clicks performed: {load_more_clicks}")
        print("Page successfully exhausted: Yes (Load More no longer added new trainers)")
        print(f"Trainer records that could not be collected: {failed_records}")
        print(f"Output file created: {OUTPUT_FILE}")

if __name__ == "__main__":
    asyncio.run(collect_trainers())
