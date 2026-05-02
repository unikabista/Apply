import os
from mcp.server.fastmcp import FastMCP as App
import yaml
from functools import lru_cache
from typing import Any, Dict, List, Optional

app = App()
resume_path = os.path.join(os.path.dirname(__file__), "about_unika_bista.yml")


@lru_cache(maxsize=1)
def load_resume_data():
    with open(resume_path, "r") as file:
        return yaml.safe_load(file)


def get_section_from_resume(section: str) -> str:
    data = load_resume_data()
    if section.lower() == "all":
        return yaml.dump(data, default_flow_style=False)
    keys = section.split(".")
    for key in keys:
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return ""
    return yaml.dump(data, default_flow_style=False) if data else ""


# ------------------ Helper formatters ------------------


def _get(path: str) -> Any:
    """Return a value for a given dot-path from YAML, or None."""
    data: Any = load_resume_data()
    for key in path.split("."):
        if isinstance(data, dict) and key in data:
            data = data[key]
        else:
            return None
    return data


def _about_me_brief_text() -> str:
    personal = _get("resume.personal") or {}
    summary = (get_section_from_resume("resume.summary") or "").strip()
    name = personal.get("name", "")
    location = personal.get("location", "")
    email = personal.get("email", "")
    website = personal.get("website", "")
    linkedin = personal.get("linkedin", "")
    github = personal.get("github", "")
    lines = []
    if name:
        lines.append(f"Name: {name}")
    if location:
        lines.append(f"Location: {location}")
    if summary:
        lines.append(f"Summary: {summary}")
    contact_bits = [b for b in [email, website, linkedin, github] if b]
    if contact_bits:
        lines.append("Contact: " + " | ".join(contact_bits))
    return "\n".join(lines) if lines else "No personal information found."


def _about_me_detailed_text() -> str:
    personal = _get("resume.personal") or {}
    education = _get("resume.education") or []
    top_experience = get_section_from_resume("resume.experience").strip()
    skills = get_section_from_resume("resume.skills").strip()
    projects = get_section_from_resume("resume.projects").strip()
    lines = []
    if personal.get("name"):
        lines.append(f"Name: {personal['name']}")
    if personal.get("location"):
        lines.append(f"Location: {personal['location']}")
    summary = (get_section_from_resume("resume.summary") or "").strip()
    if summary:
        lines.append(f"Summary: {summary}")
    if isinstance(education, list) and education:
        edu = education[0]
        edu_line = ", ".join(
            p
            for p in [
                edu.get("name", ""),
                edu.get("degree", ""),
                f"GPA {edu.get('gpa', '')}" if edu.get("gpa") else "",
                edu.get("date", ""),
            ]
            if p
        )
        if edu_line:
            lines.append(f"Education: {edu_line}")
    if top_experience:
        lines.append("Experience (highlights):\n" + top_experience)
    if skills:
        lines.append("Skills:\n" + skills)
    if projects:
        lines.append("Projects (selected):\n" + projects)
    return "\n\n".join(lines) if lines else "No details found."


@app.tool(
    name="export_plain_resume",
    description="Export a clean, plain-text resume assembled from the YAML knowledge source.",
)
def export_plain_resume() -> str:
    """Return a plain-text resume formatted with header, summary, education, skills, experience and projects."""
    r = (_get("resume") or {})

    personal = r.get("personal", {})
    name = personal.get("name", "")
    location = personal.get("location", "")
    phone = personal.get("phone", "")
    email = personal.get("email", "")
    website = personal.get("website", "")
    linkedin = personal.get("linkedin", "")

    lines: List[str] = []
    # Header
    contact = " | ".join([p for p in [phone, email, website, linkedin, location] if p])
    if name:
        lines.append(name)
    if contact:
        lines.append(contact)
    lines.append("")

    # Summary
    summary = (r.get("summary") or "").strip()
    if summary:
        lines.append("SUMMARY")
        lines.append(summary)
        lines.append("")

    # Education
    education = r.get("education", [])
    if isinstance(education, list) and education:
        lines.append("EDUCATION")
        for edu in education:
            if isinstance(edu, dict):
                edu_parts = [
                    edu.get("name", ""),
                    edu.get("degree", ""),
                    edu.get("date", ""),
                ]
                lines.append(". ".join(p for p in edu_parts if p))
        lines.append("")

    # Skills
    skills = r.get("skills", [])
    if isinstance(skills, list) and skills:
        lines.append("SKILLS")
        for cat in skills:
            cat_name = cat.get("name", "")
            items = cat.get("items", [])
            if cat_name and items:
                lines.append(f"{cat_name}: {', '.join(items)}")
        lines.append("")

    # Experience
    exp = r.get("experience", [])
    if isinstance(exp, list) and exp:
        lines.append("EXPERIENCE")
        for job in exp:
            title = job.get("title", "")
            company = job.get("company", "")
            date = job.get("date", "")
            loc = job.get("location", "")
            header = ", ".join([p for p in [title, company, loc, date] if p])
            if header:
                lines.append(header)
            achievements = job.get("achievements", [])
            if isinstance(achievements, list):
                for a in achievements:
                    lines.append(f"- {a.strip()}")
            lines.append("")

    # Projects
    projects = r.get("projects", [])
    if isinstance(projects, list) and projects:
        lines.append("PROJECTS")
        for p in projects:
            proj_name = p.get("name", "")
            desc = p.get("description", "")
            if proj_name:
                lines.append(f"• {proj_name} — {desc}" if desc else f"• {proj_name}")
        lines.append("")

    return "\n".join(lines)


# ------------------ Basic Tools ------------------


@app.tool(
    name="get_personal_section",
    description="Get the personal/contact section from the YAML knowledge source.",
)
def get_personal_section():
    content = get_section_from_resume("resume.personal")
    return (
        f"Personal Section:\n{content}"
        if content
        else "No content found for personal section."
    )


@app.tool(
    name="get_education_section",
    description="Get the education section from the resume YAML file, including institution, degree, GPA, dates, and courses.",
)
def get_education_section():
    content = get_section_from_resume("resume.education")
    return (
        f"Education Section:\n{content}"
        if content
        else "No content found for education section."
    )


@app.tool(
    name="get_experience_section",
    description="Retrieve the 'experience' section from the resume YAML file. This section includes detailed information about the user's professional work experience, including roles, companies, dates, and achievements.",
)
def get_experience_section():
    content = get_section_from_resume("resume.experience")
    return (
        f"Experience Section:\n{content}"
        if content
        else "No content found for experience section."
    )


@app.tool(
    name="get_projects_section",
    description="Retrieve the 'projects' section from the resume YAML file. This section highlights the user's key projects, including descriptions, accomplishments, and technologies used.",
)
def get_projects_section():
    content = get_section_from_resume("resume.projects")
    return (
        f"Projects Section:\n{content}"
        if content
        else "No content found for projects section."
    )


@app.tool(
    name="get_skills_section",
    description="Get the skills section from the resume YAML file.",
)
def get_skills_section():
    content = get_section_from_resume("resume.skills")
    return (
        f"Skills Section:\n{content}"
        if content
        else "No content found for skills section."
    )


@app.tool(
    name="get_summary_section",
    description="Get the summary section from the resume YAML file.",
)
def get_summary_section():
    content = get_section_from_resume("resume.summary")
    return (
        f"Summary Section:\n{content}"
        if content
        else "No content found for summary section."
    )


@app.tool(
    name="get_research_section",
    description="Get the research section from the resume YAML file, including research focus areas and topics.",
)
def get_research_section():
    content = get_section_from_resume("resume.research")
    return (
        f"Research Section:\n{content}"
        if content
        else "No content found for research section."
    )


@app.tool(
    name="get_leadership_section",
    description="Get the leadership and involvements section from the resume YAML file, including organizations and roles.",
)
def get_leadership_section():
    content = get_section_from_resume("resume.leadership")
    return (
        f"Leadership Section:\n{content}"
        if content
        else "No content found for leadership section."
    )


@app.tool(
    name="get_awards_section",
    description="Get the awards section from the resume YAML file.",
)
def get_awards_section():
    content = get_section_from_resume("resume.awards")
    return (
        f"Awards Section:\n{content}"
        if content
        else "No content found for awards section."
    )


@app.tool(
    name="get_certifications_section",
    description="Get all the certifications from the resume YAML file.",
)
def get_certifications_section():
    content = get_section_from_resume("resume.certifications")
    return (
        f"Certifications Section:\n{content}"
        if content
        else "No content found for certifications section."
    )


@app.tool(
    name="get_references_section",
    description="Get the professional references from the resume YAML file.",
)
def get_references_section():
    content = get_section_from_resume("resume.references")
    return (
        f"References Section:\n{content}"
        if content
        else "No content found for references section."
    )


# ------------------ Additional Sections ------------------


@app.tool(
    name="get_open_source_contributions_section",
    description="Get the open source contributions section from the resume YAML file.",
)
def get_open_source_contributions_section():
    content = get_section_from_resume("resume.open_source_contributions")
    return (
        f"Open Source Contributions Section:\n{content}"
        if content
        else "No content found for open source contributions section."
    )


@app.tool(
    name="get_kaggle_competitions_section",
    description="Get the Kaggle competitions section from the resume YAML file.",
)
def get_kaggle_competitions_section():
    content = get_section_from_resume("resume.kaggle_competitions")
    return (
        f"Kaggle Competitions Section:\n{content}"
        if content
        else "No content found for Kaggle competitions section."
    )


@app.tool(
    name="get_competitive_programming_section",
    description="Get the competitive programming section from the resume YAML file.",
)
def get_competitive_programming_section():
    content = get_section_from_resume("resume.competitive_programming")
    return (
        f"Competitive Programming Section:\n{content}"
        if content
        else "No content found for competitive programming section."
    )


@app.tool(
    name="get_scholarships_section",
    description="Get the scholarships section from the resume YAML file.",
)
def get_scholarships_section():
    content = get_section_from_resume("resume.scholarships")
    return (
        f"Scholarships Section:\n{content}"
        if content
        else "No content found for scholarships section."
    )


# ------------------ About Me Tools (YAML as source of truth) ------------------


@app.tool(
    name="about_me_brief",
    description="Return a short, easy bio about Unika Bista (name, location, one-line summary, and key contacts) from YAML.",
)
def about_me_brief():
    return _about_me_brief_text()


@app.tool(
    name="about_me_detailed",
    description="Return a detailed overview about Unika Bista with education, highlights of experience, skills, and selected projects from YAML.",
)
def about_me_detailed():
    return _about_me_detailed_text()


@app.tool(
    name="about_me_answer",
    description="Answer natural-language questions about Dinesh using the YAML knowledge source. Routes to relevant sections automatically.",
)
def about_me_answer(question: str):
    q = (question or "").lower()
    # Simple routing based on keywords; YAML is the source of truth.
    if any(
        k in q
        for k in [
            "contact",
            "email",
            "phone",
            "linkedin",
            "github",
            "website",
            "where are you",
            "location",
        ]
    ):
        return get_personal_section()
    if any(
        k in q
        for k in [
            "summary",
            "bio",
            "about you",
            "about me",
            "who is dinesh",
            "who are you",
            "dinesh chhantyal",
        ]
    ):
        return about_me_brief()
    if any(k in q for k in ["education", "degree", "gpa", "university", "school"]):
        return get_education_section()
    if any(k in q for k in ["experience", "work", "intern", "job", "employment"]):
        return get_experience_section()
    if any(k in q for k in ["project", "projects", "portfolio", "built"]):
        return get_projects_section()
    if any(k in q for k in ["skill", "skills", "tech", "stack"]):
        return get_skills_section()
    if any(k in q for k in ["research", "paper", "thesis", "number theory", "embryo"]):
        return get_research_section()
    if any(k in q for k in ["award", "awards", "honor", "recognition"]):
        return get_awards_section()
    if any(k in q for k in ["cert", "certification", "certifications"]):
        return get_certifications_section()
    if any(k in q for k in ["leadership", "involvement", "club", "organization", "president"]):
        return get_leadership_section()
    if any(k in q for k in ["reference", "references", "recommend"]):
        return get_references_section()
    if any(k in q for k in ["kaggle", "leaderboard"]):
        return get_kaggle_competitions_section()
    if any(k in q for k in ["competitive programming", "icpc", "coding contest"]):
        return get_competitive_programming_section()
    if any(k in q for k in ["scholarship", "scholarships", "financial aid"]):
        return get_scholarships_section()
    if any(k in q for k in ["open source", "contribution", "oss"]):
        return get_open_source_contributions_section()
    # Fallback to generic QA over YAML dump
    return ask_resume_question(question)


# ------------------ Refinement Tools ------------------


@app.tool(
    name="experience_tool",
    description="Refine experience section based on job description",
)
def experience_tool(job_description: str, resume_experience: str) -> str:
    return f"""
You are a professional resume editor. Your task is to rewrite the candidate's experience section to align with the following job description:

Job Description:
{job_description}

Candidate's Experience:
{resume_experience}

Instructions:
- Emphasize experience that directly relates to the role.
- Highlight accomplishments using metrics, technologies, or business outcomes.
- Use strong action verbs and concise bullet points.
- Remove unrelated or redundant content.
- Maintain professional tone.

Return ONLY the improved experience section.
"""


@app.tool(
    name="summary_tool", description="Refine summary section based on job description"
)
def summary_tool(job_description: str, summary: str) -> str:
    return f"""
You are a resume summary specialist. Improve the candidate's professional summary based on this job description:

Job Description:
{job_description}

Current Summary:
{summary}

Instructions:
- Keep it concise and impactful (2-3 sentences).
- Align it with the job's key qualifications.
- Emphasize key skills or experiences.

Return ONLY the improved summary.
"""


@app.tool(
    name="projects_tool", description="Refine projects section based on job description"
)
def projects_tool(job_description: str, projects: str) -> str:
    return f"""
Revise the following projects section to better match the job description below:

Job Description:
{job_description}

Projects:
{projects}

Instructions:
- Highlight relevant technologies and outcomes.
- Focus on relevance to the job.
- Keep it action- and impact-oriented.

Return ONLY the revised projects section.
"""


@app.tool(
    name="leadership_tool",
    description="Refine leadership/involvements section based on job description",
)
def leadership_tool(job_description: str, leadership: str) -> str:
    return f"""
You are refining the candidate's leadership section for the job below:

Job Description:
{job_description}

Leadership & Involvements:
{leadership}

Instructions:
- Focus on leadership, teamwork, or initiatives that match the job's values.
- Emphasize transferable skills and impact.

Return ONLY the improved leadership section.
"""


@app.tool(
    name="skills_tool", description="Refine skills section based on job description"
)
def skills_tool(job_description: str, skills: str) -> str:
    return f"""
Update the skills section to prioritize skills listed in the job description:

Job Description:
{job_description}

Current Skills:
{skills}

Instructions:
- Prioritize hard/technical skills relevant to the job.
- Maintain readability (comma-separated or bulleted).
- Remove outdated or irrelevant skills.

Return ONLY the revised skills list.
"""


# ------------------ Generic QA Tool ------------------


@app.tool(
    name="ask_resume_question",
    description="Ask any question about the resume and get an answer.",
)
def ask_resume_question(question: str):
    full_text = get_section_from_resume("all")
    return f"""
You are a resume assistant. Here's the full resume:

{full_text}

Question: {question}

Please answer concisely and based only on the resume.
"""


# ------------------ Refine All ------------------


@app.tool(
    name="refine_all",
    description="Refine multiple resume sections using a job description.",
)
def refine_all(
    job_description: str,
    experience: str = "",
    projects: str = "",
    leadership: str = "",
    skills: str = "",
    summary: str = "",
):
    output = {}
    if summary:
        output["summary"] = summary_tool(job_description, summary)
    if experience:
        output["experience"] = experience_tool(job_description, experience)
    if projects:
        output["projects"] = projects_tool(job_description, projects)
    if leadership:
        output["leadership"] = leadership_tool(job_description, leadership)
    if skills:
        output["skills"] = skills_tool(job_description, skills)
    return output


if __name__ == "__main__":
    app.run(transport="stdio")
