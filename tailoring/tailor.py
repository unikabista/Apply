import os
import yaml
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.Anthropic(api_key=os.getenv("Anthropic_API_KEY"))
MODEL = "claude-haiku-4-5-20251001"


def _ask(prompt: str) -> str:
    message = _client.messages.create(
        model=MODEL,
        max_tokens=4096,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def tailor_resume(resume_data: dict, job_description: str) -> dict:
    resume_yaml = yaml.dump(resume_data, default_flow_style=False, allow_unicode=True)

    print(f"  Tailoring resume with Claude ({MODEL})...")
    result = _ask(f"""You are a professional resume tailoring expert. Tailor this resume for the job description below.

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
- Do NOT add any tool, software, or skill that does not already appear in the resume
- Do NOT change personal info, company names, job titles, dates, or GPA

Return ONLY valid YAML with no markdown code fences and no explanation.""")

    # Strip markdown fences if Claude adds them
    if result.startswith("```"):
        result = "\n".join(result.split("\n")[1:])
    if result.endswith("```"):
        result = result[:-3].strip()

    tailored = yaml.safe_load(result)

    # Always restore original personal info
    if "personal" in resume_data:
        tailored["personal"] = resume_data["personal"]

    return tailored


def tailor_cover_letter(cover_letter_data: dict, job_description: str, company_name: str, role_name: str) -> dict:
    print(f"  Tailoring cover letter with Claude ({MODEL})...")
    body_text = _ask(f"""You are a professional cover letter writer. Write a tailored cover letter body.

Applicant: Unika Bista
- CS Junior at University of Louisiana at Monroe (Aug 2023 - May 2027)
- Technology & UX Insights Intern at Design Arts Seminars, Inc (Jan 2026 - Present): AI automation, HubSpot API workflows, Figma prototypes, UX research for 1,000+ students
- AI Intern at ULM Information Technology (May 2024 - Present): JavaScript/HTML front-end (25% engagement boost), Python/SQL ETL (10,000+ records), Docker/AWS/CI/CD deployment
- Projects: Dristi (AI accessibility app, Flask/Qwen2-VL/Whisper AI, 99% uptime, 40% task improvement, 2nd ULM Hawkathon, 3rd Nexus Cup statewide), SATHI (Next.js/Gemini career assistant), Athlyze (MediaPipe/React injury prevention)
- Skills: Python, JavaScript, React, TypeScript, FastAPI, Flask, Docker, AWS, Firebase, PostgreSQL, AI/ML, Claude, GPT-4o, Prompt Engineering
- Leadership: President Girls Who Code, Treasurer NSA, Campus Ambassador Intern Insider
- Certifications: AWS AI Practitioner, AWS Cloud Practitioner

Company: {company_name}
Role: {role_name}

Job Description:
{job_description}

Write exactly 3 paragraphs:
1. Catchy opening: mention the position and company, include a compelling hook that sells Unika immediately
2. Body: connect her specific experience and projects to what the job requires; be concrete and specific to the JD
3. Closing: express appreciation, request an interview, include phone +1-318-350-8760 and email unika.bista0@gmail.com

Rules:
- Do NOT use dashes (-) or em-dashes in sentences; use commas, periods, or restructure instead
- Be specific to the job description; reference actual requirements from the JD
- Sound human and enthusiastic, not generic
- Return ONLY the 3 paragraphs separated by a blank line, with no labels or extra text""")

    data = cover_letter_data.copy()
    data["letter"] = cover_letter_data["letter"].copy()
    data["letter"]["body"] = body_text
    data["recipient"] = cover_letter_data["recipient"].copy()
    data["recipient"]["company"] = company_name
    data["recipient"]["title"] = role_name
    return data
