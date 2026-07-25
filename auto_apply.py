"""
auto_apply.py — full pipeline orchestrator

Usage:
  python auto_apply.py                        # interactive mode (asks before each submit)
  python auto_apply.py --dry-run              # tailor + generate PDFs, no submission
  python auto_apply.py --limit 5              # process at most 5 jobs per run
  python auto_apply.py --ats ashby,lever      # only target specific ATS platforms
  python auto_apply.py --no-coverletter       # skip cover letter for all roles

Pipeline per job:
  1. Fetch job list from GitHub tracker (SimplifyJobs Summer 2026)
  2. Filter: active, intern, no exclusion keywords, not already applied
  3. Sort: easiest ATS first, freshest first
  4. For each job:
     a. Scrape full job description
     b. Pick the closest resume variant for the role (unless forced)
     c. AI-tailor that resume with Claude
     d. Generate resume PDF
     d. AI-write + generate cover letter (Tier 1 only, unless --no-coverletter)
     e. Prompt user to proceed/skip (unless --auto-submit)
     f. Submit via ATS-specific Playwright applier
     g. Log result to applications-log.csv
"""

import argparse
import os
import sys
import yaml

from jobdiscovery.finder import fetch_jobs, detect_ats
from jobdescription.scraptor import JobDescriptionScraper
from tailoring.tailor import tailor_resume, tailor_cover_letter
from resume.generator import ResumeGenerator
from coverletter.generator import CoverLetterGenerator
from tracker import log as tracker
from profile import PROFILE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESUME_YAML = os.path.join(BASE_DIR, "resume", "resume.yml")
COVERLETTER_YAML = os.path.join(BASE_DIR, "coverletter", "coverletter.yml")


# ------------------------------------------------------------------ #
# Resume variant selection                                             #
# ------------------------------------------------------------------ #
#
# The pipeline picks the closest resume variant for the role, then AI-tailors
# it to the specific job description. "default" is resume.yml (general purpose).

RESUME_VARIANTS = {
    "ml":         os.path.join(BASE_DIR, "resume", "resume_ml.yml"),
    "leadership": os.path.join(BASE_DIR, "resume", "resume_leadership.yml"),
    "sw":         os.path.join(BASE_DIR, "resume", "resume_sw.yml"),
    "default":    RESUME_YAML,
}

# Keyword signals per variant. A hit in the job TITLE counts more than the JD
# because the title is the strongest indicator of role type.
_VARIANT_KEYWORDS = {
    "ml": [
        "machine learning", "ml engineer", "ai engineer", "artificial intelligence",
        "deep learning", "data scien", "nlp", "llm", "computer vision",
        "applied scientist", "research", "generative ai", "mlops",
    ],
    "leadership": [
        "product manager", "product management", "program manager", "developer advocate",
        "developer relations", "devrel", "community", "founding", "chief of staff",
        "technical program", "operations",
    ],
    "sw": [
        "software engineer", "full stack", "full-stack", "backend", "back end",
        "frontend", "front end", "web developer", "platform engineer", "swe",
        "application developer", "systems engineer",
    ],
}

TITLE_WEIGHT = 3   # title matches weigh 3x a JD match


def select_resume_variant(title: str, jd: str = "") -> tuple:
    """Pick the best-matching resume variant for a role.

    Scores each variant's keywords against the title (x3) and the JD (x1).
    Returns (variant_key, yaml_path). Falls back to the default resume when
    no variant scores above zero.
    """
    title_l = (title or "").lower()
    jd_l = (jd or "").lower()

    scores = {}
    for key, keywords in _VARIANT_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in title_l:
                score += TITLE_WEIGHT
            if kw in jd_l:
                score += 1
        scores[key] = score

    best_key = max(scores, key=scores.get)
    if scores[best_key] == 0:
        return "default", RESUME_VARIANTS["default"]
    return best_key, RESUME_VARIANTS[best_key]


# ------------------------------------------------------------------ #
# Applier factory                                                      #
# ------------------------------------------------------------------ #

def get_applier(ats: str):
    if ats == "ashby":
        from applier.ashby import AshbyApplier
        return AshbyApplier(PROFILE)
    if ats == "greenhouse":
        from applier.greenhouse import GreenhouseApplier
        return GreenhouseApplier(PROFILE)
    if ats == "lever":
        from applier.lever import LeverApplier
        return LeverApplier(PROFILE)
    if ats == "workday":
        from applier.workday import WorkdayApplier
        return WorkdayApplier(PROFILE)
    if ats == "smartrecruiters":
        from applier.smartrecruiters import SmartRecruitersApplier
        return SmartRecruitersApplier(PROFILE)
    if ats == "linkedin":
        from applier.linkedin import LinkedInApplier
        return LinkedInApplier(PROFILE)
    if ats == "indeed":
        from applier.indeed import IndeedApplier
        return IndeedApplier(PROFILE)
    if ats == "handshake":
        from applier.handshake import HandshakeApplier
        return HandshakeApplier(PROFILE)
    # Generic fallback for any other ATS / career pages
    from applier.generic import GenericApplier
    return GenericApplier(PROFILE)


# ------------------------------------------------------------------ #
# Application folder helpers                                           #
# ------------------------------------------------------------------ #

def _save_info(output_dir: str, company: str, title: str, ats: str,
               url: str, jd: str, status: str, notes: str = ""):
    """Write/overwrite application_info.md inside the application folder."""
    from datetime import datetime as _dt
    lines = [
        f"# {company} — {title}",
        "",
        f"| Field   | Value |",
        f"|---------|-------|",
        f"| Company | {company} |",
        f"| Role    | {title} |",
        f"| ATS     | {ats.upper()} |",
        f"| URL     | {url} |",
        f"| Status  | **{status}** |",
        f"| Date    | {_dt.now().strftime('%Y-%m-%d %H:%M')} |",
    ]
    if notes:
        lines += ["", f"**Notes:** {notes}"]
    if jd:
        lines += ["", "## Job Description (first 500 chars)", "", jd[:500] + ("..." if len(jd) > 500 else "")]
    path = os.path.join(output_dir, "application_info.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ------------------------------------------------------------------ #
# Per-job pipeline                                                     #
# ------------------------------------------------------------------ #

def process_job(job: dict, args) -> str:
    """
    Run the full pipeline for one job.
    Returns the final status string.
    """
    company = job["company"]
    title   = job["title"]
    url     = job["url"]
    ats     = job["ats"]

    print(f"\n{'='*60}")
    print(f"  Company : {company}")
    print(f"  Role    : {title}")
    print(f"  ATS     : {ats.upper()}")
    print(f"  URL     : {url}")
    print(f"{'='*60}")

    # Skip if already applied
    if tracker.already_applied(company):
        print("  [SKIP] Already applied to this company.")
        return tracker.STATUS_SKIPPED

    # ---- 1. Scrape job description -----------------------------------
    print("  Scraping job description...")
    try:
        scraper = JobDescriptionScraper()
        jd = scraper.scrape(url)
    except Exception as e:
        print(f"  [WARN] Scrape failed ({e}). Continuing with blank JD.")
        jd = ""

    # ---- 2. Build output directory -----------------------------------
    from datetime import datetime as _dt
    company_slug = company.replace(" ", "_").replace("/", "_")
    role_slug    = title.replace(" ", "").replace("/", "")
    output_dir   = os.path.join(BASE_DIR, "applications", company_slug)
    os.makedirs(output_dir, exist_ok=True)

    if jd:
        with open(os.path.join(output_dir, "job_description.txt"), "w", encoding="utf-8") as f:
            f.write(jd)

    # Save application metadata immediately so the folder is self-contained
    _save_info(output_dir, company, title, ats, url, jd, status="in_progress")

    # ---- 3. Select resume variant + tailor --------------------------
    if args.resume_variant == "auto":
        variant_key, resume_yaml = select_resume_variant(title, jd)
    else:
        variant_key = args.resume_variant
        resume_yaml = RESUME_VARIANTS[variant_key]
    print(f"  Resume variant: {variant_key}  ({os.path.basename(resume_yaml)})")

    resume_data = None
    if jd:
        print("  Tailoring resume with Claude...")
        try:
            with open(resume_yaml, "r", encoding="utf-8") as f:
                base_resume = yaml.safe_load(f)
            resume_data = tailor_resume(base_resume, jd)
        except Exception as e:
            print(f"  [WARN] Resume tailoring failed ({e}). Using base resume.")

    resume_pdf_path = os.path.join(output_dir, f"Unika_Bista_Resume_{role_slug}.pdf")
    print("  Generating resume PDF...")
    gen = ResumeGenerator(resume_yaml)
    if resume_data:
        gen.data = resume_data
    try:
        resume_pdf = gen.generate_pdf(resume_pdf_path, output_dir)
        print(f"  Resume: {resume_pdf}")
    except Exception as e:
        print(f"  [ERROR] PDF generation failed: {e}")
        tracker.log(company, title, ats, url, tracker.STATUS_ERROR, notes=str(e))
        return tracker.STATUS_ERROR

    # ---- 4. Cover letter (Tier 1 or required) ----------------------
    coverletter_pdf = None
    if not args.no_coverletter and jd:
        print("  Tailoring cover letter with Claude...")
        try:
            with open(COVERLETTER_YAML, "r", encoding="utf-8") as f:
                base_cl = yaml.safe_load(f)
            cl_data = tailor_cover_letter(base_cl, jd, company, title)
            cl_pdf_path = os.path.join(output_dir, f"Unika_Bista_CoverLetter_{role_slug}.pdf")
            cl_gen = CoverLetterGenerator(COVERLETTER_YAML)
            cl_gen.data = cl_data
            coverletter_pdf = cl_gen.generate_pdf(cl_pdf_path, output_dir, company)
            print(f"  Cover letter: {coverletter_pdf}")
        except Exception as e:
            print(f"  [WARN] Cover letter failed ({e}). Continuing without it.")

    # ---- 5. Dry-run bail-out ----------------------------------------
    if args.dry_run:
        print("  [DRY RUN] Documents generated. Skipping submission.")
        tracker.log(company, title, ats, url, "DRY_RUN")
        _save_info(output_dir, company, title, ats, url, jd, status="DRY_RUN")
        return "DRY_RUN"

    # ---- 6. Interactive confirmation --------------------------------
    if not args.auto_submit:
        answer = input(f"\n  Submit to {company} ({title})? [y/n/s(kip company)] ").strip().lower()
        if answer == "s":
            tracker.log(company, title, ats, url, tracker.STATUS_SKIPPED, notes="user skipped")
            _save_info(output_dir, company, title, ats, url, jd, status=tracker.STATUS_SKIPPED)
            return tracker.STATUS_SKIPPED
        if answer != "y":
            tracker.log(company, title, ats, url, tracker.STATUS_PENDING, notes="deferred by user")
            _save_info(output_dir, company, title, ats, url, jd, status=tracker.STATUS_PENDING)
            return tracker.STATUS_PENDING

    # ---- 7. Get applier for this ATS --------------------------------
    applier = get_applier(ats)

    # ---- 8. Submit --------------------------------------------------
    print(f"  Submitting via {ats.upper()} applier...")
    result = applier.apply(url, resume_pdf, coverletter_pdf)
    status = result.get("status", tracker.STATUS_ERROR)
    notes  = result.get("notes", "")
    print(f"  Result: {status}  {notes}")
    tracker.log(company, title, ats, url, status, notes=notes)
    _save_info(output_dir, company, title, ats, url, jd, status=status, notes=notes)
    return status


# ------------------------------------------------------------------ #
# Entry point                                                          #
# ------------------------------------------------------------------ #

def main():
    parser = argparse.ArgumentParser(description="Auto-apply to Summer 2026 internships")
    parser.add_argument("--dry-run",       action="store_true",
                        help="Generate documents but do not submit")
    parser.add_argument("--auto-submit",   action="store_true",
                        help="Submit without asking for confirmation (use carefully)")
    parser.add_argument("--limit",         type=int, default=10,
                        help="Max applications per run (default: 10)")
    parser.add_argument("--ats",           type=str,
                        default="ashby,greenhouse,lever,workday,smartrecruiters,linkedin,indeed,handshake,other",
                        help="Comma-separated ATS platforms to target (default: all)")
    parser.add_argument("--no-coverletter", action="store_true",
                        help="Skip cover letter for all applications")
    parser.add_argument("--max-age-days",  type=int, default=21,
                        help="Skip roles older than this many days (default: 21)")
    parser.add_argument("--resume-variant", type=str, default="auto",
                        choices=["auto", "default", "sw", "ml", "leadership"],
                        help="Resume to use: 'auto' picks by role type (default), "
                             "or force one of default/sw/ml/leadership")
    args = parser.parse_args()

    allowed_ats = {a.strip().lower() for a in args.ats.split(",")}

    print("\n=== Unika Bista — Auto Internship Applier ===")
    print(f"  Mode      : {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"  Limit     : {args.limit} applications")
    print(f"  ATS filter: {', '.join(sorted(allowed_ats))}")
    print(f"  Max age   : {args.max_age_days} days")
    print(f"  Resume    : {args.resume_variant}\n")

    # Fetch & filter job listings
    print("Fetching job listings...")
    jobs = fetch_jobs(max_age_days=args.max_age_days)
    jobs = [j for j in jobs if j["ats"] in allowed_ats]

    if not jobs:
        print("No matching internship listings found. Try again later.")
        return

    print(f"Found {len(jobs)} listings. Processing up to {args.limit}...\n")

    results = {
        tracker.STATUS_SUBMITTED: 0,
        tracker.STATUS_SKIPPED:   0,
        tracker.STATUS_PENDING:   0,
        tracker.STATUS_BLOCKED:   0,
        tracker.STATUS_ERROR:     0,
        "DRY_RUN":                0,
    }

    applied = 0
    for job in jobs:
        if applied >= args.limit:
            break

        status = process_job(job, args)
        results[status] = results.get(status, 0) + 1

        if status in (tracker.STATUS_SUBMITTED, "DRY_RUN"):
            applied += 1

    # Summary
    print(f"\n{'='*60}")
    print("  SESSION SUMMARY")
    print(f"{'='*60}")
    for status, count in results.items():
        if count:
            print(f"  {status:<20} {count}")
    print(f"\n  Log saved to: applications-log.csv")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
        sys.exit(0)
