"""Fetch internship listings from Handshake."""
import os
from playwright.sync_api import sync_playwright

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sessions")

HANDSHAKE_SEARCH = (
    "https://app.joinhandshake.com/stu/postings"
    "?page=1&per_page=50&sort_direction=desc&sort_column=default"
    "&job_type_names[]=Internship"
    "&employment_type_names[]=Internship"
)


def fetch_from_handshake(max_jobs: int = 100) -> list:
    session_file = os.path.join(SESSIONS_DIR, "handshake_session.json")
    if not os.path.exists(session_file):
        print("  [handshake] No session — run: python login.py handshake")
        return []

    results = []
    seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=session_file)
        page = context.new_page()
        try:
            _scrape_listings(page, results, seen, max_jobs)
        except Exception as e:
            print(f"  [handshake] Scrape error: {e}")
        finally:
            browser.close()

    print(f"  [handshake] {len(results)} internships found.")
    return results


def _scrape_listings(page, results: list, seen: set, max_jobs: int):
    page_num = 1
    while len(results) < max_jobs:
        url = HANDSHAKE_SEARCH.replace("page=1", f"page={page_num}")
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2500)
        except Exception:
            break

        # Handshake job cards
        cards = page.locator(
            "div[class*='job-listing'], "
            "li[class*='posting'], "
            "div[data-hook='job-card']"
        ).all()

        if not cards:
            # Try generic card selectors
            cards = page.locator("article, li[class*='JobCard']").all()

        if not cards:
            break

        added = 0
        for card in cards:
            if len(results) >= max_jobs:
                return
            try:
                link = card.locator("a[href*='/jobs/'], a[href*='/postings/']").first
                if not link.count():
                    continue

                href = link.get_attribute("href") or ""
                if not href:
                    continue
                if href.startswith("/"):
                    href = "https://app.joinhandshake.com" + href
                if href in seen:
                    continue
                seen.add(href)

                title_el   = card.locator("h3, h2, [class*='title'], [data-hook='job-title']").first
                company_el = card.locator("[class*='company'], [data-hook='company-name']").first
                loc_el     = card.locator("[class*='location'], [data-hook='location']").first

                title    = title_el.inner_text().strip() if title_el.count() else "Internship"
                company  = company_el.inner_text().strip() if company_el.count() else ""
                location = loc_el.inner_text().strip() if loc_el.count() else ""

                results.append({
                    "company":     company,
                    "title":       title,
                    "url":         href,
                    "ats":         "handshake",
                    "date_posted": None,
                    "location":    location,
                    "source":      "handshake",
                })
                added += 1
            except Exception:
                continue

        if added == 0:
            break  # no new jobs on this page

        page_num += 1
