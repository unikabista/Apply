# What Was Built — Unika Bista Auto-Apply System

This file documents every file created or modified in this project session.

---

## Files Created

### `profile.py`
Unika's personal information used to auto-fill every ATS form field.
Contains: name, email, phone, location, LinkedIn, school, degree, graduation year, work authorization, pronouns, gender, race, etc.
**Edit this file** if any of your details change.

---

### `tracker/log.py`
Logs every application attempt to `applications-log.csv`.

Tracks: date, company, role, ATS platform, URL, status, pay rate, tier, notes.

**Status values:**
| Status | Meaning |
|--------|---------|
| `submitted` | Form filled and submitted successfully |
| `REJECTED` | Rejection email received |
| `BLOCKED` | Could not submit (captcha, account required, etc.) |
| `CLOSED` | Job posting no longer active |
| `SKIPPED` | Skipped (exclusion keyword, already applied, user choice) |
| `PENDING` | Documents ready but not yet submitted |
| `OUTREACH SENT` | Applied + sent recruiter message |
| `INTERVIEW` | Interview invite received |
| `ERROR` | Pipeline crashed on this job |
| `DRY_RUN` | Documents generated but submission skipped |

---

### `jobdiscovery/finder.py`
Fetches Summer 2026 internship listings from the **SimplifyJobs GitHub tracker**:
`github.com/SimplifyJobs/Summer2026-Internships`

- Filters out closed roles, roles older than 21 days, and roles with exclusion keywords
  (`US Citizen only`, `security clearance`, `ITAR`, `no CPT/OPT`, etc.)
- Detects ATS platform from URL (Ashby, Greenhouse, Lever, Workday, etc.)
- Sorts by: easiest ATS to automate first, then freshest listings first

---

### `applier/base.py`
Shared Playwright helper class that all ATS appliers inherit from.

Helpers include: `fill()`, `click()`, `upload()`, `upload_via_button()`,
`click_radio_or_button()`, `answer_yes_no()`, `submit()`.

---

### `applier/ashby.py`
Auto-fills and submits **Ashby** ATS forms.
Handles: name, email, phone, location, LinkedIn, resume upload, cover letter upload,
work authorization Yes/No toggles, demographic dropdowns.

Ashby URLs look like: `jobs.ashbyhq.com/company/role-id`

---

### `applier/greenhouse.py`
Auto-fills and submits **Greenhouse** ATS forms.
Handles everything in Ashby plus: school typeahead combobox
(`University of Louisiana - Monroe`), degree dropdown, discipline field,
graduation year, EEO fields (gender, race, veteran, disability).

Greenhouse URLs look like: `boards.greenhouse.io/company/jobs/id`

---

### `applier/lever.py`
Auto-fills and submits **Lever** ATS forms.
Handles: full name field, email, phone, location, LinkedIn, resume upload,
cover letter, work authorization radio buttons.
Also handles the "Apply" button on the job listing page before the form appears.

Lever URLs look like: `jobs.lever.co/company/job-id`

---

### `auto_apply.py`
**The main orchestrator.** Runs the full pipeline end-to-end.

**Full pipeline per job:**
1. Fetch listings from SimplifyJobs GitHub tracker
2. Filter: active, intern, no exclusion keywords, not already applied
3. Sort: easiest ATS first, freshest first
4. Scrape full job description from the URL (Playwright headless browser)
5. AI-tailor resume with Gemini to match the job description
6. Generate tailored resume PDF via LaTeX
7. AI-write tailored cover letter + generate PDF (if job description available)
8. Ask for confirmation (unless `--auto-submit`)
9. Submit via the appropriate ATS applier (Ashby / Greenhouse / Lever)
10. Log result to `applications-log.csv`
11. Save `application_info.md` inside the application's folder

**Commands:**
```bash
# See what it would do — no submissions, just generate PDFs
python auto_apply.py --dry-run

# Normal run: asks "Submit? [y/n/s]" before each application
python auto_apply.py

# Only Ashby, limit 3 apps
python auto_apply.py --limit 3 --ats ashby

# Fully automatic — no prompts (use carefully!)
python auto_apply.py --auto-submit --limit 5

# Skip cover letters for all
python auto_apply.py --no-coverletter
```

---

### `WORKFLOW.md`
Adapted from Dinesh's workflow — fully customized for Unika:
- All personal info swapped (name, email, phone, LinkedIn, school, graduation, gender, pronouns)
- Removed all visa/H-1B/OPT/F-1 sections (not needed)
- Kept filter for "US Citizen only" / "security clearance" exclusions
- Changed all references from full-time roles to Summer 2026 internships
- Updated sources: Handshake first, then LinkedIn, Simplify, GitHub trackers
- Changed compensation benchmarks to internship pay ($20–$55/hr)
- Updated cover letter highlights to Unika's projects (Dristi, SATHI, Athlyze, AWS certs)

---

## Application Folder Structure

Every time `auto_apply.py` runs, it creates a folder per company:

```
applications/
└── Company_Name/
    ├── application_info.md          ← metadata: company, role, ATS, URL, status, date
    ├── job_description.txt          ← scraped full job description
    ├── Unika_Bista_Resume_RoleName.pdf
    └── Unika_Bista_CoverLetter_RoleName.pdf   (if generated)
```

`application_info.md` is updated at the end of the pipeline with the final status
(submitted, blocked, pending, etc.) so each folder is fully self-contained.

---

## Global Tracking File

`applications-log.csv` — one row per application, all companies in one place.
Open in Excel or Google Sheets to see your full application history.

---

## What Is NOT Automated (Manual Steps)

| Platform | Why manual |
|----------|-----------|
| **Workday** | Requires creating a unique account per company |
| **LinkedIn Easy Apply** | Simplify overlay can block the submit button |
| **SmartRecruiters** | Requires account creation |
| **Captcha-protected forms** | Cannot be automated (Cloudflare, reCAPTCHA Enterprise) |
| **Custom ATS** (Citadel, D.E. Shaw) | Each is unique, session timeouts, special flows |

For these, `auto_apply.py` marks the application as `PENDING` and saves the
resume + cover letter in the application folder so you can submit manually.

---

## Key Files at a Glance

```
C:\Desktop\Apply\
│
├── auto_apply.py          ← RUN THIS to auto-apply
├── profile.py             ← your personal info for form filling
├── WORKFLOW.md            ← your full job search strategy
├── BUILT.md               ← this file
├── applications-log.csv   ← generated on first run, tracks all apps
│
├── applications/          ← one folder per company, auto-created
│   └── Company_Name/
│       ├── application_info.md
│       ├── job_description.txt
│       ├── Unika_Bista_Resume_Role.pdf
│       └── Unika_Bista_CoverLetter_Role.pdf
│
├── resume/resume.yml      ← edit this to update your resume
├── coverletter/coverletter.yml  ← edit this to update your cover letter
├── mcp/about_unika_bista.yml    ← full profile, source of truth for AI tailoring
│
├── tracker/log.py         ← CSV logging
├── jobdiscovery/finder.py ← fetches jobs from GitHub tracker
├── applier/
│   ├── base.py            ← shared Playwright helpers
│   ├── ashby.py           ← Ashby form filler
│   ├── greenhouse.py      ← Greenhouse form filler
│   └── lever.py           ← Lever form filler
│
└── main.py                ← original manual tool (still works)
```
