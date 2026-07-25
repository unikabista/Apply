import yaml
import os
import subprocess
from generators.base import DocumentGenerator


class ResumeGenerator(DocumentGenerator):
    def __init__(self, yaml_file):
        super().__init__(yaml_file)
        self.yaml_file = yaml_file
        with open(yaml_file, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

    def escape_latex(self, text):
        """Escape special LaTeX characters, protecting already-escaped sequences.

        Why placeholders? Some YAML values already contain pre-escaped LaTeX like backslash-&
        or backslash-%. Without placeholders, escape_latex would double-escape them which breaks LaTeX.
        """
        if not isinstance(text, str):
            text = str(text)

        replacements = [
            ("#", "\\#"),
            ("\\&", "AMP_PLACEHOLDER"),      # protect already-escaped &
            ("&", "\\&"),                     # escape bare &
            ("AMP_PLACEHOLDER", "\\&"),       # restore
            ("\\%", "PERCENT_PLACEHOLDER"),   # protect already-escaped %
            ("%", "\\%"),                     # escape bare %
            ("PERCENT_PLACEHOLDER", "\\%"),   # restore
            ("_", "\\_"),
            ("~", "\\textasciitilde{}"),
            ("<", "\\textless{}"),
            (">", "\\textgreater{}"),
            ('"', "''"),
            ("−", "--"),
            ("–", "--"),
        ]

        for old, new in replacements:
            text = text.replace(old, new)

        return text

    def get_latex_preamble(self):
        """Returns the LaTeX preamble matching the Overleaf template exactly."""
        return r"""\documentclass[letterpaper,11pt]{article}

\usepackage[top=0.4in, bottom=0.4in, left=0.5in, right=0.5in]{geometry}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{titlesec}
\usepackage{parskip}
\usepackage[T1]{fontenc}
\usepackage{lmodern}

% Remove paragraph indent
\setlength{\parindent}{0pt}

% Tighten vertical spacing to keep resume on 1 page
\setlength{\parskip}{1pt}
\setlength{\medskipamount}{2pt}

% Section formatting: bold, with horizontal rule underneath
\titleformat{\section}
  {\bfseries\normalsize}{}{0em}{}[\titlerule]
\titlespacing{\section}{0pt}{2pt}{1pt}

% Hyperlink styling
\hypersetup{
  colorlinks=true,
  urlcolor=blue,
  linkcolor=blue
}

% List settings — tight spacing to keep resume on 1 page
\setlist[itemize]{noitemsep, topsep=1pt, parsep=0pt, partopsep=0pt, leftmargin=1.5em}"""

    def generate_header(self, personal):
        """Header: large bold name centered, then one contact line."""
        name = personal.get("name", "").upper()
        location = personal.get("location", "")
        phone = personal.get("phone", "")
        email = personal.get("email", "")
        linkedin = personal.get("linkedin", "")

        return (
            f"\\begin{{center}}\n"
            f"  {{\\Large\\bfseries {name}}}\\\\[4pt]\n"
            f"  {location} \\textbar{{}} {phone} \\textbar{{}}"
            f" \\href{{mailto:{email}}}{{{email}}} \\textbar{{}}\n"
            f"  \\href{{{linkedin}}}{{{linkedin}}}\n"
            f"\\end{{center}}"
        )

    def generate_summary(self, summary):
        return f"\\section{{Summary}}\n{self.escape_latex(summary.strip())}"

    def generate_education(self, education):
        lines = ["\\section{Education}"]
        for i, school in enumerate(education or []):
            if not isinstance(school, dict):
                continue
            name = school.get("name", "")
            degree = school.get("degree", "")
            date = school.get("date", "").replace("–", "--")
            gpa = school.get("GPA", "")

            lines.append(f"\n\\textbf{{{name}}} \\hfill {date}\\\\")
            if gpa:
                lines.append(f"{degree} \\hfill GPA: {gpa}")
            else:
                lines.append(degree)

            if i < len(education) - 1:
                lines.append("\\medskip")

        return "\n".join(lines)

    def generate_experience(self, experience):
        lines = ["\\section{Experience}"]
        for i, job in enumerate(experience or []):
            if not isinstance(job, dict):
                continue
            company = self.escape_latex(job.get("company", ""))
            title = self.escape_latex(job.get("title", ""))
            date = job.get("date", "").replace("–", "--")

            lines.append(f"\n\\textbf{{{company}}} \\textbar{{}} {title} \\hfill {date}")
            lines.append("\\begin{itemize}")
            for achievement in (job.get("achievements") or []):
                clean = achievement.lstrip("- ").strip()
                lines.append(f"  \\item {clean}")
            lines.append("\\end{itemize}")

            if i < len(experience) - 1:
                lines.append("\\medskip")

        return "\n".join(lines)

    def generate_projects(self, projects):
        lines = ["\\section{Projects and Research}"]
        for i, project in enumerate(projects or []):
            if not isinstance(project, dict):
                continue
            name = self.escape_latex(project.get("name", ""))
            bullets = project.get("bullets", [])
            description = project.get("description", "")
            link = project.get("link", "")

            if link:
                lines.append(f"\n\\href{{{link}}}{{\\textbf{{{name}}}}}")
            else:
                lines.append(f"\n\\textbf{{{name}}}")

            # Why bullets over description? Multiple focused bullet points are easier
            # for ATS to parse and for humans to scan quickly
            lines.append("\\begin{itemize}")
            if bullets:
                for bullet in bullets:
                    lines.append(f"  \\item {bullet.lstrip('- ').strip()}")
            elif description:
                lines.append(f"  \\item {description}")
            lines.append("\\end{itemize}")

            if i < len(projects) - 1:
                lines.append("\\medskip")

        return "\n".join(lines)

    def generate_skills(self, skills):
        lines = ["\\section{Technical Skills}", "", "\\begin{itemize}"]
        for category in (skills or []):
            if not isinstance(category, dict):
                continue
            # Why replace \\\\&? YAML pre-escaped \& gets double-escaped by escape_latex
            # in some edge cases; this is a safety net.
            name = self.escape_latex(category.get("name", "")).replace("\\\\&", "\\&")
            items = self.escape_latex(category.get("items", "")).replace("\\\\&", "\\&")
            lines.append(f"  \\item \\textbf{{{name}:}} {items}")
        lines.append("\\end{itemize}")
        return "\n".join(lines)

    def generate_achievements_leadership(self, leadership, awards=None):
        lines = ["\\section{Achievements and Leadership}", "", "\\begin{itemize}"]

        # Combine all leadership roles into one bullet separated by |
        if leadership:
            parts = []
            for item in leadership:
                name = item.get("name", "")
                date = item.get("date", "").replace("–", "--")
                parts.append(f"{name} ({date})")
            leadership_line = " \\textbar{{}} ".join(parts)
            lines.append(f"  \\item \\textbf{{Leadership:}} {leadership_line}")

        # Each award as its own bullet
        for award in (awards or []):
            if not isinstance(award, dict):
                continue
            title = self.escape_latex(award.get("title", "")).replace("–", "--")
            issuer = self.escape_latex(award.get("issuer", ""))
            date = award.get("date", "")
            lines.append(f"  \\item \\textbf{{{title}, {date}:}} {issuer}")

        lines.append("\\end{itemize}")
        return "\n".join(lines)

    def generate_resume(self, yaml_file):
        """Assemble the full LaTeX document from YAML data."""
        data = self.data
        personal = data.get("personal", {})
        summary = data.get("summary", "")
        education = data.get("education", [])
        experience = data.get("experience", [])
        projects = data.get("projects", [])
        skills = data.get("skills", [])
        leadership = data.get("leadership", [])
        awards = data.get("awards", [])

        sections = [
            self.get_latex_preamble(),
            "\\begin{document}",
            self.generate_header(personal),
        ]

        if summary:
            sections.append(self.generate_summary(summary))
        if education:
            sections.append(self.generate_education(education))
        if experience:
            sections.append(self.generate_experience(experience))
        if projects:
            sections.append(self.generate_projects(projects))
        if skills:
            sections.append(self.generate_skills(skills))
        if leadership or awards:
            sections.append(self.generate_achievements_leadership(leadership, awards))

        sections.append("\\end{document}")
        return "\n\n".join(sections)

    def compile_pdf(self, tex_file):
        """Compile LaTeX to PDF using pdflatex.

        Why not check=True? pdflatex exits with code 1 even on non-fatal warnings
        while still producing a valid PDF. We check for the PDF file instead.
        """
        output_dir = os.path.dirname(tex_file)

        pdflatex_paths = [
            "pdflatex",
            "/usr/local/texlive/2024/bin/universal-darwin/pdflatex",
            "/usr/local/texlive/2024/bin/x86_64-darwin/pdflatex",
            "/Library/TeX/texbin/pdflatex",
        ]

        pdflatex_cmd = None
        for path in pdflatex_paths:
            try:
                subprocess.run([path, "--version"], check=True, capture_output=True)
                pdflatex_cmd = path
                break
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        if not pdflatex_cmd:
            raise Exception("pdflatex not found. Please install MiKTeX or add it to PATH.")

        # Run twice so cross-references and hyperlinks resolve correctly
        for _ in range(2):
            result = subprocess.run(
                [pdflatex_cmd, "-interaction=nonstopmode", "-output-directory=" + output_dir, tex_file],
                capture_output=True,
            )
            pdf_check = os.path.splitext(tex_file)[0] + ".pdf"
            if result.returncode != 0 and not os.path.exists(pdf_check):
                raise subprocess.CalledProcessError(
                    result.returncode, result.args, result.stdout, result.stderr
                )

        # Clean up auxiliary files
        base = os.path.splitext(tex_file)[0]
        for ext in [".aux", ".log", ".out"]:
            if os.path.exists(base + ext):
                os.remove(base + ext)

        pdf_file = base + ".pdf"
        if not os.path.exists(pdf_file):
            raise Exception("PDF file was not generated.")
        return pdf_file

    def generate_pdf(self, output_file_path, output_dir="output"):
        """Generate LaTeX then compile to PDF."""
        base = os.path.splitext(output_file_path)[0]
        tex_file = base + ".tex"

        latex_content = self.generate_resume(self.yaml_file)
        with open(tex_file, "w", encoding="utf-8") as f:
            f.write(latex_content)

        pdf_file = self.compile_pdf(tex_file)

        if os.path.exists(tex_file):
            os.remove(tex_file)

        return pdf_file

    def save_resume(self, yaml_file, output_file_path):
        output_dir = os.path.dirname(output_file_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        latex_content = self.generate_resume(yaml_file)
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write(latex_content)
        return output_file_path

    def generate_tex(self):
        return self.generate_resume(self.yaml_file)
