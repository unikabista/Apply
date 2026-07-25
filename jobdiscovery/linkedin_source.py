"""Fetch internship listings from LinkedIn Jobs (Easy Apply only)."""
import os
import urllib.parse
from playwright.sync_api import sync_playwright

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sessions")

QUERIES = [
    "software engineer intern",
    "software developer intern",
    "data science intern",
    "machine learning intern",
    "ai engineer intern",
    "backend engineer intern",
    "full stack engineer intern",
]


def fetch_from_linkedin(max_jobs: int = 150) -> list:
    session_file = os.path.join(SESSIONS_DIR, "linkedin_session.json")
    if not os.path.exists(session_file):
        print("  [linkedin] No session — run: python login.py linkedin")
        return []

    results = []
    seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=session_file)
        page = context.new_page()
        try:
            for query in QUERIES:
                if len(results) >= max_jobs:
                    break
                _scrape_query(page, query, results, seen, max_per_query=25)
        except Exception as e:
            print(f"  [linkedin] Scrape error: {e}")
        finally:
            browser.close()

    print(f"  [linkedin] {len(results)} Easy Apply internships found.")
    return results


def _scrape_query(page, query: str, results: list, seen: set, max_per_query: int):
    encoded = urllib.parse.quote(query)
    # f_AL=true → Easy Apply only | f_JT=I → Internship type
    url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={encoded}&location=United+States&f_AL=true&f_JT=I&sortBy=DD"
    )
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
    except Exception:
        return

    fetched = 0
    for scroll in range(6):
        # Parse visible job cards
        cards = page.locator(
            "li.jobs-search-results__list-item, "
            "div.job-card-container, "
            "li[data-occludable-job-id]"
        ).all()

        for card in cards:
            if fetched >= max_per_query or len(results) >= 200:
                return
            try:
                link = card.locator("a[href*='/jobs/view/']").first
                if not link.count():
                    continue
                href = link.get_attribute("href") or ""
                if not href:
                    continue

                # Normalize URL — strip query params, keep just the job view path
                if href.startswith("/"):
                    href = "https://www.linkedin.com" + href
                href = href.split("?")[0]

                if href in seen:
                    continue
                seen.add(href)

                title_el = card.locator(
                    ".job-card-list__title, .base-search-card__title, "
                    "strong, a[href*='/jobs/view/']"
                ).first
                company_el = card.locator(
                    ".job-card-container__primary-description, "
                    ".base-search-card__subtitle, "
                    ".job-card-list__company-name"
                ).first

                title   = title_el.inner_text().strip() if title_el.count() else query
                company = company_el.inner_text().strip() if company_el.count() else ""

                results.append({
                    "company":     company,
                    "title":       title,
                    "url":         href,
                    "ats":         "linkedin",
                    "date_posted": None,
                    "location":    "United States",
                    "source":      "linkedin",
                })
                fetched += 1
            except Exception:
                continue

        if fetched >= max_per_query:
            return

        # Scroll down to load more cards
        page.evaluate("window.scrollBy(0, 1200)")
        page.wait_for_timeout(1800)
