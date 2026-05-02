import os
import google.generativeai as genai
import yaml
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini with your API key from .env
# Why: genai needs to know your key before making any calls
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))


def tailor_resume(resume_data: dict, job_description: str) -> dict:
    """Use Gemini to tailor resume YAML data for a specific job description."""

    # Why "gemini-2.0-flash"? It's fast, free on student quota, and smart enough for resume tailoring
    model = genai.GenerativeModel("gemini-2.0-flash")

    resume_yaml = yaml.dump(resume_data, default_flow_style=False, allow_unicode=True)

    print("  Tailoring resume with AI...")
    response = model.generate_content(f"""You are a professional resume tailoring expert. Tailor this resume for the job description below.

JOB DESCRIPTION:
{job_description}

RESUME (YAML):
{resume_yaml}

Rules:
- Rewrite the summary (max 2 lines) to directly match the job's key requirements and keywords
- Rephrase experience bullet points to emphasize skills and technologies matching the job. Preserve ALL facts: company names, titles, dates, locations, numbers, and metrics.
- Reorder skills sections to put the most relevant skills first; keep all existing items
- Reorder projects to put the most relevant ones first
- Wrap key technical terms in bullet points with \\textbf{{term}} for ATS optimization
- Do NOT invent new experiences, technologies, metrics, or achievements
- Do NOT add any tool, software, or skill that does not already appear in the resume (e.g. do not add AutoCAD, Salesforce, or any other tool just because the job mentions it)
- Do NOT change personal info, company names, job titles, dates, or GPA
- The AI Processing Instructions comments at the top must be preserved exactly

Return ONLY valid YAML with no markdown code fences and no explanation.""")

    result = response.text.strip()

    # Strip markdown code fences if Gemini adds them anyway
    # Why: AI models sometimes wrap output in ```yaml ... ``` even when told not to
    if result.startswith("```"):
        result = "\n".join(result.split("\n")[1:])
    if result.endswith("```"):
        result = result[:-3].strip()

    tailored = yaml.safe_load(result)

    # Safety net: always restore original personal info
    # Why: we never want AI to accidentally change your name, email, phone
    if "personal" in resume_data:
        tailored["personal"] = resume_data["personal"]

    return tailored


def tailor_cover_letter(cover_letter_data: dict, job_description: str, company_name: str, role_name: str) -> dict:
    """Use Gemini to write a tailored cover letter body for the given job."""
    model = genai.GenerativeModel("gemini-2.0-flash")

    print("  Tailoring cover letter with AI...")
    response = model.generate_content(f"""You are a professional cover letter writer. Write a tailored cover letter body.

Applicant: Unika Bista
- CS Junior at University of Louisiana at Monroe (Aug 2023 – May 2027)
- Technology & UX Insights Intern at Design Arts Seminars, Inc (Jan 2026 – Present): AI automation, Zapier workflows, HubSpot, UX optimization
- Student Worker at ULM Information Technology (May 2024 – Present): front-end development, Python ETL, database work, web forms
- Projects: Dristi (AI accessibility app for the blind, 2nd ULM Hawkathon, 3rd Nexus Cup), Athlyze (ACL injury prevention using Google MediaPipe + React)
- Skills: Python, JavaScript, React, TypeScript, FastAPI, Flask, Docker, MongoDB, Firebase, AI/ML, GPT-4o, MediaPipe
- Leadership: VP & Founding Member Girls Who Code, Treasurer NSA, Campus Ambassador Intern Insider

Company: {company_name}
Role: {role_name}

Job Description:
{job_description}

Write exactly 3 paragraphs:
1. Catchy opening: mention the position and company, include a compelling hook that sells Unika immediately
2. Body: connect her specific experience and projects to what the job requires; be concrete and specific to the JD
3. Closing: express appreciation, request an interview, include phone +1-318-350-8760 and email unika.bista0@gmail.com

Rules:
- Do NOT use dashes (-) or em-dashes (—) inside sentences; use commas, periods, or restructure instead
- Be specific to the job description; reference actual requirements from the JD
- Sound human and enthusiastic, not generic
- Return ONLY the 3 paragraphs separated by a blank line, with no labels or extra text""")

    body_text = response.text.strip()

    # Update the cover letter data with AI-generated body
    # Why: we keep all personal info from the original file, only replace the body text
    data = cover_letter_data.copy()
    data["letter"] = cover_letter_data["letter"].copy()
    data["letter"]["body"] = body_text
    data["recipient"] = cover_letter_data["recipient"].copy()
    data["recipient"]["company"] = company_name
    data["recipient"]["title"] = role_name
    return data
