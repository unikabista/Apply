"""Fetch internship listings from Indeed (Indeed Apply jobs only)."""
import os
import urllib.parse
from playwright.sync_api import sync_playwright

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sessions")

QUERIES = [
    "software engineer intern",
    "software developer intern",
    "data science intern",
    "machine learning intern",
    "backend engineer intern",
]


def fetch_from_indeed(max_jobs: int = 100) -> list:
    session_file = os.path.join(SESSIONS_DIR, "indeed_session.json")
    if not os.path.exists(session_file):
        print("  [indeed] No session — run: python login.py indeed")
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
            print(f"  [indeed] Scrape error: {e}")
        finally:
            browser.close()

    print(f"  [indeed] {len(results)} Indeed Apply internships found.")
    return results


def _scrape_query(page, query: str, results: list, seen: set, max_per_query: int):
    encoded = urllib.parse.quote(query)
    # iafilter=1 → Indeed Apply only | jt=internship → internship type
    url = (
        f"https://www.indeed.com/jobs"
        f"?q={encoded}&jt=internship&iafilter=1&sort=date&fromage=14"
    )
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)
    except Exception:
        return

    fetched = 0
    for page_num in range(4):  # up to 4 pages of results
        # Parse job cards
        cards = page.locator(
            "div.job_seen_beacon, "
            "div[data-testid='slider_item'], "
            "li[class*='job']"
        ).all()

        for card in cards:
            if fetched >= max_per_query:
                return
            try:
                link = card.locator("a[href*='/rc/clk'], a[href*='/pagead/'], a[id*='job']").first
                if not link.count():
                    link = card.locator("a[href*='jk=']").first
                if not link.count():
                    continue

                href = link.get_attribute("href") or ""
                if not href:
                    continue
                if href.startswith("/"):
                    href = "https://www.indeed.com" + href

                # Extract job key for deduplication
                jk = _extract_jk(href)
                if not jk or jk in seen:
                    continue
                seen.add(jk)

                title_el   = card.locator("h2.jobTitle a, h2 a span[id*='jobTitle'], h2 span").first
                company_el = card.locator(
                    "[data-testid='company-name'], .companyName, span.companyName"
                ).first
                location_el = card.locator(
                    "[data-testid='text-location'], .companyLocation"
                ).first

                title    = title_el.inner_text().strip() if title_el.count() else query
                company  = company_el.inner_text().strip() if company_el.count() else ""
                location = location_el.inner_text().strip() if location_el.count() else ""

                # Use canonical job URL
                job_url = f"https://www.indeed.com/viewjob?jk={jk}"

                results.append({
                    "company":     company,
                    "title":       title,
                    "url":         job_url,
                    "ats":         "indeed",
                    "date_posted": None,
                    "location":    location,
                    "source":      "indeed",
                })
                fetched += 1
            except Exception:
                continue

        if fetched >= max_per_query:
            return

        # Next page
        next_btn = page.locator("a[aria-label='Next Page'], a[data-testid='pagination-page-next']").first
        if next_btn.count() and next_btn.is_visible():
            next_btn.click()
            page.wait_for_timeout(2500)
        else:
            break


def _extract_jk(url: str) -> str:
    """Extract the 'jk' job key from an Indeed URL."""
    for part in url.split("&"):
        if part.startswith("jk="):
            return part[3:]
        if "?jk=" in part:
            return part.split("?jk=")[1]
    return ""
