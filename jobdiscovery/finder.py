import requests
from datetime import datetime, timedelta

# Primary tracker: SimplifyJobs Summer 2026 Internships
SIMPLIFY_JSON_URL = (
    "https://raw.githubusercontent.com/SimplifyJobs/"
    "Summer2026-Internships/dev/.github/scripts/listings.json"
)

# Keywords that disqualify a role (check full JSON blob)
SKIP_KEYWORDS = [
    "us citizen only",
    "us citizens only",
    "security clearance",
    "secret clearance",
    "top secret",
    "itar",
    "must be a u.s. citizen",
    "must be authorized without sponsorship",
    "no cpt",
    "no opt",
    "us person required",
    "active clearance",
    "green card required",
]

# Keywords that make a title relevant
ROLE_KEYWORDS = [
    "software", "engineer", "developer", "swe", "ml", "machine learning",
    "ai", "artificial intelligence", "data", "backend", "frontend",
    "full stack", "fullstack", "platform", "cloud", "devops", "sre",
    "infrastructure", "python", "research", "intern",
]

ATS_PRIORITY = {
    "ashby":           0,
    "lever":           1,
    "greenhouse":      2,
    "smartrecruiters": 3,
    "linkedin":        4,
    "handshake":       5,
    "indeed":          6,
    "workday":         7,
    "other":           8,
}


def detect_ats(url: str) -> str:
    u = (url or "").lower()
    if "ashbyhq.com" in u or "jobs.ashbyhq" in u:
        return "ashby"
    if "greenhouse.io" in u or "boards.greenhouse" in u:
        return "greenhouse"
    if "lever.co" in u or "jobs.lever" in u:
        return "lever"
    if "workday" in u or "myworkdayjobs" in u:
        return "workday"
    if "smartrecruiters" in u:
        return "smartrecruiters"
    if "linkedin.com" in u:
        return "linkedin"
    if "joinhandshake.com" in u or "handshake.com" in u:
        return "handshake"
    if "indeed.com" in u:
        return "indeed"
    return "other"


def fetch_from_simplify(max_age_days: int = 21) -> list:
    try:
        resp = requests.get(SIMPLIFY_JSON_URL, timeout=20)
        resp.raise_for_status()
        jobs = resp.json()
    except Exception as e:
        print(f"  [finder] Could not fetch SimplifyJobs tracker: {e}")
        return []

    cutoff = datetime.now() - timedelta(days=max_age_days)
    results = []

    for job in jobs:
        if not job.get("active", True):
            continue
        if not job.get("is_visible", True):
            continue

        url = job.get("url") or ""
        if not url:
            continue

        title = (job.get("title") or "").lower()
        if "intern" not in title and "internship" not in title:
            continue

        # Date filter
        ts = job.get("date_posted")
        if ts:
            try:
                if datetime.fromtimestamp(ts) < cutoff:
                    continue
            except Exception:
                pass

        # Skip disqualifying keywords anywhere in the record
        blob = str(job).lower()
        if any(kw in blob for kw in SKIP_KEYWORDS):
            continue

        results.append({
            "company": job.get("company_name", ""),
            "title": job.get("title", ""),
            "url": url,
            "ats": detect_ats(url),
            "date_posted": ts,
            "location": ", ".join(job.get("location") or []),
            "source": "simplify",
        })

    return results


def fetch_jobs(max_age_days: int = 21) -> list:
    """Fetch, filter, and sort internship listings from all sources."""
    jobs = fetch_from_simplify(max_age_days)

    # Pull from authenticated sources if sessions exist
    try:
        from jobdiscovery.linkedin_source import fetch_from_linkedin
        jobs += fetch_from_linkedin()
    except Exception as e:
        print(f"  [finder] LinkedIn source skipped: {e}")

    try:
        from jobdiscovery.indeed_source import fetch_from_indeed
        jobs += fetch_from_indeed()
    except Exception as e:
        print(f"  [finder] Indeed source skipped: {e}")

    try:
        from jobdiscovery.handshake_source import fetch_from_handshake
        jobs += fetch_from_handshake()
    except Exception as e:
        print(f"  [finder] Handshake source skipped: {e}")

    jobs = _dedupe(jobs)
    jobs = _sort(jobs)
    print(f"  [finder] {len(jobs)} total internship listings found.")
    return jobs


def _dedupe(jobs: list) -> list:
    seen = set()
    out = []
    for j in jobs:
        key = (j["company"].lower(), j["url"])
        if key not in seen:
            seen.add(key)
            out.append(j)
    return out


def _sort(jobs: list) -> list:
    def score(j):
        ats_score = ATS_PRIORITY.get(j["ats"], 3)
        freshness = -(j.get("date_posted") or 0)
        return (ats_score, freshness)
    return sorted(jobs, key=score)
