---
name: job-application-workflow
description: Complete end-to-end workflow for finding, tailoring, generating, verifying, and submitting internship applications for Unika Bista
type: reference
---

# Internship Application Workflow — Unika Bista

## Core Principle: Tailor Hard, Reach Out Direct

Mass, untailored ATS applications convert poorly. The two things that move the needle for internships are (1) a resume that mirrors the exact keywords in the job description so it survives ATS + recruiter scanning, and (2) direct human contact (recruiter/hiring-manager outreach, replying to founders on hiring threads) that gets you past the resume pile entirely.

Every application should be one of:

- **Tailored ATS app** — keyword-mirrored resume for a confirmed, relevant internship.
- **Direct outreach** — a short, personal message to a recruiter or founder within 48 hours of applying.
- **Quick win** — finishing a PENDING app or a fast Ashby/Lever form.

### Daily Target Mix (5–8 apps/day)

- **2–3 direct outreach** (message recruiters on LinkedIn, reply to hiring-thread posts) — highest response rate
- **2–3 tailored ATS apps** (fresh, relevant internship postings)
- **1–2 quick wins** (pending apps, easy Ashby forms)

### Time Per Application

- Direct outreach: ~15 min (research company + personalized message)
- Tailored ATS app: 20–30 min (keyword mirror + form fill)
- Quick wins: ~5 min

## Phase 1: Finding Jobs

### Target: Summer internships (SWE / AI / ML / Full-Stack / Data)

The pipeline (`jobdiscovery/finder.py`) currently pulls from the **SimplifyJobs Summer internship tracker**
(`github.com/SimplifyJobs/Summer2026-Internships`). When a new season's tracker opens, update that URL in `finder.py`.

### Sources (in priority order)

#### Tier A — Direct Outreach (highest response rate — do first every day)

1. **Recruiter / hiring-manager LinkedIn messages** at companies you've applied to (see Phase 8). This is the single highest-leverage channel.
2. **HN "Who is Hiring?"** thread (1st of every month) — searchable at `hnhiring.com`. Reply directly to intern-friendly posts.
3. **r/forhire** and university/club job boards from small companies.
4. **Cold message founders/CTOs** at small startups (<30 people) that don't have a formal intern program — many will take a strong intern if you reach out.

#### Tier B — Pre-Screened ATS (relevant, intern-friendly)

5. **Handshake** — many companies recruit interns here exclusively.
6. **LinkedIn** internship search (filter: Internship, past 24 hours, on-site/remote as you prefer).
7. **Simplify** (`simplify.jobs`) — pre-filtered new-grad/intern roles, autofill extension.
8. **GitHub trackers** (cross-reference for freshness — many "open" rows are actually closed):
   - `github.com/SimplifyJobs/Summer2026-Internships`
   - `github.com/speedyapply/2026-SWE-College-Jobs`
   - `github.com/vanshb03/Summer2026-Internships`

#### Tier C — Aggregators (check daily)

9. **YC Work at a Startup** (`ycombinator.com/jobs`) — YC startups, intern-friendly.
10. **Wellfound** (`wellfound.com`) — startup internships.
11. **Built In** (`builtin.com`) — mid-size companies.
12. **Google ATS dorking** (surfaces roles before aggregators):
    - `"software engineer" "intern" site:jobs.ashbyhq.com`
    - `"intern" "summer 2027" site:boards.greenhouse.io`

#### Tier D — Lower priority

13. **levergreen.dev** — scrapes Greenhouse, Lever, Ashby daily.
14. **Ashby public API** — poll company slugs directly.

### Filtering (apply immediately, don't waste time)

- **SKIP if** any exclusion keyword appears (these are auto-filtered by `finder.py`): "US Citizen only", "must be a U.S. citizen", "must be authorized without sponsorship", "security clearance", "secret clearance", "active clearance", "ITAR", "no CPT", "no OPT".
- **SKIP if** it's a full-time / senior role (target says "intern" or "internship").
- **SKIP if** posted older than 3 weeks.
- **SKIP if** on-site in a location you can't do (unless remote).
- **SKIP if** already in `applications-log.csv` (one application per company).
- **Target roles**: SWE Intern, AI/ML Engineer Intern, Full Stack, Backend, Data, Frontend, Platform, QA/Test.
- **Prioritize by channel**: direct message > Ashby (fastest form) > Lever > Greenhouse > Workday (slowest).
- **Prioritize by freshness**: roles posted in the last 48 hours first (fewer applicants).
- **ONE application per company** — multiple apps to the same company get batch-rejected. Pick the best-fit role.

### Role Tiers (determines effort level)

- **Tier 1 (High Priority)**: strong-brand or well-funded company, great match, posted <48 hours ago. Full tailoring + cover letter + LinkedIn outreach to recruiter.
- **Tier 1D (Direct Outreach)**: any startup where you can message the founder/CTO directly. Full tailoring + personalized message.
- **Tier 2 (Standard)**: decent match, posted <2 weeks ago. Tailored resume, cover letter only if required.
- **Tier 3 (Quick Apply)**: weaker match but relevant. Use the closest existing resume variant, no cover letter.

### Verification (BEFORE investing time)

- **Always navigate to the actual job URL** and confirm the page loads (not 404, not a redirect to a generic careers page).
- Don't trust GitHub tracker status — many roles marked "open" are closed.
- Confirm the role is actually an internship and accepts current students (CPT/OPT is fine).
- **Phantom listing detection**: if an Ashby/Lever role has been closed and reopened 3+ times, skip it.

## Phase 2: Tailoring Resume

### Source of Truth

- `mcp/about_unika_bista.yml` has ALL factual information (full experience details, all projects, all skills, all awards).
- Only pull content from this file when expanding achievements or adding details.
- `resume/resume.yml` is a curated subset tailored per role.

### Resume YAML Rules (`resume/resume.yml`)

- `%` direct in LaTeX (no escaping).
- `&` in skill names needs `\&`.
- Use `\textbf{}` for bold technical terms in achievements.
- Summary: **max 2 lines** (hard rule).
- NEVER change factual info (role, company, location, dates).
- NEVER invent technologies not in `about_unika_bista.yml`.
- NEVER create a new file. Edit in place.
- Resume variants exist: `resume_sw.yml`, `resume_ml.yml`, `resume_leadership.yml`.

### Keyword Mirroring (CRITICAL for ATS + Recruiter Scanning)

Before writing any bullet, extract the top 5–10 keywords from the JD:

- Technologies named in the requirements (e.g., "React", "Python", "Docker", "AWS").
- Domain terms (e.g., "computer vision", "automation", "full-stack", "data pipeline").
- Action patterns (e.g., "build and ship", "optimize", "collaborate").

Then rewrite bullets so these exact phrases appear naturally. Example:

- JD says "computer vision" → bullet says "computer vision", not "image processing".
- JD says "REST APIs" → bullet says "REST APIs", not "web services".
- JD says "React and TypeScript" → put React before TypeScript in your skills list.

### Summary Section (Make It a Mini Pitch)

The summary is the first thing a recruiter reads. Make it specific, not generic.

- BAD: "Results-driven CS student with experience in software development."
- GOOD: "CS junior building AI systems and automation pipelines — shipped a computer-vision accessibility app (99% uptime, 40% faster task completion) and migrated 10K+ records into PostgreSQL — seeking a Summer SWE internship at [Company]."
- Include: target role context, 1–2 quantified highlights, tech-stack match.
- Every summary should feel written for THIS specific role.

### What to Tailor Per Job

- `summary` — rewrite with target role keywords and company context, max 2 lines.
- `experience.achievements` — rewrite bullets to match the JD:
  - Pull full achievement details from `about_unika_bista.yml`.
  - Pick the bullets that best match the JD keywords and responsibilities.
  - Reword to mirror the JD language exactly (see Keyword Mirroring above).
  - Every bullet should have a number (metric, percentage, count).
  - Example: for a front-end role, lead with React/full-stack bullets. For an AI role, lead with the Xerox AI agent, SATHI (RAG/agentic), and Dristi work.
- `skills` — reorder categories and items to put JD-relevant skills first.
- `projects` — choose/reorder the 3 most relevant of SATHI, Dristi, Athlyze.
- Toggle optional sections (leadership, awards) to fit one page.

### What Stays Constant

- `personal` info (name, phone, email, LinkedIn).
- `education` section.
- Factual details: titles, companies, dates, locations.

### Reuse Strategy

- **Tier 1 roles**: always tailor fresh.
- **Tier 2 roles**: reuse if the JD is very similar, but at minimum rewrite the summary.
- **Tier 3 roles**: use the closest existing variant as-is.

## Phase 3: Tailoring Cover Letter

### When to Write a Cover Letter

- **REQUIRED**: Tier 1 roles and any form with a mandatory cover letter field.
- **SKIP**: Tier 2/3 roles where the cover letter is optional.
- Reinvest time saved into deeper resume tailoring.

### Cover Letter YAML Rules (`coverletter/coverletter.yml`)

- Catchy opening with a personal touch about the specific company/role.
- **NO dashes (-) or em-dashes in sentences.** Use periods, commas, or restructure.
- Strict business letter format.
- `[Company Name]` / `[Role Title]` placeholders auto-replaced by the generator.

### Structure (3 paragraphs)

1. **Opening**: hook mentioning something specific about the company/role that excites you.
2. **Body**: your experience. Reference resume highlights — Xerox (AI agent across Microsoft 365 for senior leadership at a Fortune 500 company; volunteer-management system serving 40,000+ employees, replacing a $95K/year platform), Design Arts Seminars (REST API integrations in Python/JavaScript, reviewing AI-generated code with Claude Code/Copilot/Cursor, 25% faster dev cycles), ULM IT (full-stack features cutting submission errors 35%, Python/SQL pipelines migrating 10,000+ records), Dristi (voice-controlled AI app, 99% uptime, 40% faster tasks, 2nd at ULM Hawkathon, 3rd at Nexus Technology Cup), SATHI (agentic career assistant with RAG + prompt engineering), AWS AI Practitioner + Cloud Practitioner certifications, CodePath AI Engineer Program, and President of Girls Who Code.
3. **Closing**: express interest, request an interview, include phone (+1-318-350-8760) and email (unika.bista0@gmail.com).

### What to Customize

- `recipient`: company name, title.
- `letter.date`: current date.
- `letter.opening`: "Dear [Company Name] Hiring Team:"
- `letter.body`: fully rewrite for each application.

## Phase 4: Generating PDFs

### Preferred: the automated pipeline

`auto_apply.py` scrapes the JD, AI-tailors the resume/cover letter, generates the PDFs, and (optionally) submits — see `BUILT.md` for full commands. Common ones:

```bash
python auto_apply.py --dry-run            # generate PDFs only, no submission
python auto_apply.py --limit 3 --ats ashby
python auto_apply.py --no-coverletter
```

### Manual generation (single role)

```bash
printf "Company Name\nRole Title\n\n3\n" | python main.py
```

- Option 1 = Resume only, 2 = Cover Letter only, 3 = Both.
- Output: `applications/{Company}/Unika_Bista_Resume_{Role}.pdf` (and cover letter if generated).

### Pipeline

YAML → LaTeX (`resume/generator.py`, `coverletter/generator.py`) → pdflatex (2 passes) → PDF.

- ATS-optimized. LaTeX line wrapping is UNPREDICTABLE from YAML text alone — always verify the rendered PDF.

## Phase 5: Verification (MUST DO EVERY TIME)

### Post-Generation Checklist

1. **Read the PDF** using the Read tool (it renders the PDF visually).
2. **Summary**: verify exactly 2 lines (not 3, not 5).
3. **Page fill**: no whitespace gap at the bottom.
4. **One page**: content does not overflow to page 2.
5. **Content accuracy**: spot check achievements against `about_unika_bista.yml`.
6. **Keyword check**: verify the top 3–5 JD keywords appear in the resume.
7. **If any issue found**: fix the YAML, regenerate, and re-verify.

### Common Problems

- Summary too long (wraps to 3+ lines) — shorten text.
- Gap at bottom — add more achievement bullets or expand descriptions.
- Overflow to page 2 — remove a bullet, condense text, or drop a section.
- Bold terms not rendering — check `\textbf{}` syntax in YAML.
- JD keywords missing — rewrite bullets to include them naturally.

## Phase 6: Submitting Application

### ATS-Specific Notes

**Ashby** (fastest):

- "Upload File" button triggers the file chooser directly.
- Yes/No toggle buttons: click in sequence, submit before state changes.
- Location field is a combobox dropdown.
- Upload the tailored resume via the Resume field (not "Autofill from resume").

**Lever**:

- Uploading the resume triggers autofill of name/email/phone/links.
- Radio buttons: if validation fails, set `.checked = true` via `page.evaluate()` and dispatch a change event.

**Greenhouse**:

- Combobox dropdowns: type slowly, wait, then Enter.
- School list uses "University of Louisiana - Monroe" (with hyphens).
- Some companies use reCAPTCHA Enterprise which blocks automated browsers.
- Education: School, Degree ("Bachelor's Degree"), Discipline ("Computer Science").

**Workday** (slowest):

- Requires creating an account per company. Best done manually — mark as PENDING for follow-up.

### Simplify Browser Extension

- Auto-fills many Greenhouse/Lever/Ashby forms: name, email, phone, location, school, degree, dates, LinkedIn, pronouns, EEO fields.
- After it autofills, verify the data and fill anything it missed.
- **Always override Simplify's resume with the tailored PDF.** Simplify uploads a generic resume — Replace/Remove it and upload the role-specific PDF from the pipeline.

### Account Creation & Login

- Use email **unika.bista0@gmail.com**; prefer "Sign in with Google" when available.
- If an OTP/verification code is required, it goes to unika.bista0@gmail.com — ask the user for the code or read it via Playwright at `https://mail.google.com`.
- Don't guess passwords — ask the user.
- Cached sessions may exist in `.playwright-mcp/`.

### Form Filling Defaults

- Name: Unika Bista
- Email: unika.bista0@gmail.com
- Phone: +1-318-350-8760 (or 3183508760 for numeric-only fields)
- Location: San Francisco, CA
- LinkedIn: https://www.linkedin.com/in/unika-bista-50139033a/
- GitHub: github.com/unikabista
- School: University of Louisiana - Monroe (Greenhouse) / University of Louisiana at Monroe (others)
- Degree: Bachelor's Degree / BS in Computer Science, Minor in Business
- GPA: (not listed — leave blank unless required)
- Graduation: May 2027 (Junior)
- Work authorized: **Yes** (F-1 student, eligible via CPT/OPT for internships)
- Require sponsorship: **No** (no sponsorship needed for the internship)
- Pronouns: She/her
- Gender: Female / Woman
- Race: Asian
- Veteran: No / Not a protected veteran
- Disability: No
- How heard: Job board

### Work Authorization Answer Strategy

For internships, you are authorized to work via **F-1 CPT/OPT**, and the internship itself does not require sponsorship.

- Work authorized: **Yes**
- Require sponsorship (for this internship): **No**
- If a text field asks about visa status: "F-1 student authorized to work via CPT/OPT for internships. No sponsorship required for this internship."
- Skip roles that require U.S. citizenship, security clearance, or that explicitly say "no CPT/OPT" (auto-filtered by `finder.py`).

## Phase 7: Tracking

### After Each Application

- The pipeline logs each attempt to `applications-log.csv` (date, company, role, ATS, URL, status, pay, tier, notes) and writes `application_info.md` inside the company folder.
- Add the company to the "do not re-apply" set (one app per company).
- Note any blockers (account needed, reCAPTCHA, transcript) for future reference.

### Status Categories

- **submitted** — went through successfully
- **REJECTED** — rejection email received
- **BLOCKED** — form filled but couldn't submit (captcha, account, transcript)
- **CLOSED** — role no longer open (404, redirect)
- **SKIPPED** — didn't apply (exclusion keyword, too senior, wrong location)
- **PENDING** — form loaded/documents ready but not yet submitted
- **OUTREACH SENT** — submitted + recruiter message sent
- **INTERVIEW** — interview invite received
- **DRY_RUN** — documents generated, submission skipped
- **ERROR** — pipeline crashed on this job

## Phase 8: Follow-Up and Outreach (HIGH PRIORITY)

### Why This Phase Matters

Applications alone are passive. A short, personal LinkedIn message to a recruiter within 48 hours of applying meaningfully raises your response rate for internships.

### When to Do Outreach

- **Always** for Tier 1 and Tier 1D roles (within 48 hours of submitting).
- **Always** where you can identify the recruiter or founder.
- **Selectively** for Tier 2 roles you genuinely want.
- **Never** for Tier 3.

### Who to Contact

1. **University / early-careers recruiter** — best target, they own the intern pipeline.
2. **Technical recruiter** for the team.
3. **Hiring manager** — only if identifiable and active on LinkedIn.

### LinkedIn Message Template (keep under 300 characters)

```
Hi [Name], I just applied for the [Role] internship at [Company]. I'm a CS junior at ULM (grad May 2027) currently building AI agents at Xerox, with award-winning AI project work (Dristi, SATHI). Would love to connect and learn more about the team!
```

### Outreach Tracking

- Update status to "OUTREACH SENT" in `applications-log.csv`; note who you messaged and when.
- If they respond, update the status to reflect next steps.

### Pending Applications (Phase 8b)

- Review PENDING applications weekly — highest ROI since most work is done.
- Resolve blockers (account creation, OTP, transcript) one by one.

## Phase 9: Weekly Review

### Every Sunday (or start of an application session)

1. **Conversion check**: interviews vs submitted this week, by channel (direct vs ATS).
2. **Rejection review**: check Gmail for new rejections; note fast auto-rejects vs human reviews and adjust targeting.
3. **Direct outreach count**: did you send 10–15 recruiter messages this week? If not, increase.
4. **Pending cleanup**: resolve or close stale PENDING applications.
5. **Outreach follow-up**: re-message contacts who haven't responded in 7 days.
6. **Source quality**: which sources yielded the most real (non-closed) roles?
7. **Resume audit**: do the current variants (`resume_sw`, `resume_ml`, `resume_leadership`) cover the roles you're seeing? Do you need a new variant?
8. **Blocker review**: any recurring blocker (reCAPTCHA, transcript) worth solving once?

### Key Metrics to Track

- **Response rate by channel**: direct outreach vs ATS.
- **Applications per company**: should be 1. If averaging >1, you're spraying.
- **Tailoring rate**: % of ATS apps that were keyword-mirrored vs sent generic.
- **Freshness**: % of apps sent within 48 hours of the posting going live.
