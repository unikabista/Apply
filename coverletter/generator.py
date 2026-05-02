from datetime import datetime
import os
import subprocess
from generators.base import DocumentGenerator


def latex_escape(text: str) -> str:
    """Escape LaTeX special characters in plain text."""
    if text is None:
        return ""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    out = []
    for ch in str(text):
        out.append(replacements.get(ch, ch))
    return "".join(out)


class CoverLetterGenerator(DocumentGenerator):
    def __init__(self, yaml_file):
        super().__init__(yaml_file)

    def format_body_paragraphs(self, body_text: str) -> str:
        """Ensure paragraphs are separated by a blank line and flush-left (full block)."""
        paragraphs = [p.strip().replace("\n", " ") for p in body_text.strip().split("\n\n") if p.strip()]
        return "\n\n".join(latex_escape(p) for p in paragraphs)

    def replace_placeholders(self, company_name: str):
        """Fill placeholders and normalize fields from YAML data, including date format."""
        data = self.data.copy()

        # Date: use long US format (e.g., October 15, 2025)
        data["letter"]["date"] = datetime.now().strftime("%B %d, %Y")

        # Replace company placeholders in opening/body
        for key in ("opening", "body"):
            if key in data["letter"] and data["letter"][key]:
                data["letter"][key] = data["letter"][key].replace("[Company Name]", company_name)

        # Basic escaping for recipient/title
        if "title" in data.get("recipient", {}):
            data["recipient"]["title"] = data["recipient"]["title"].replace("&", "\\&")

        self.data = data
        return data

    def generate_tex(self, company_name: str):
        self.replace_placeholders(company_name)
        personal = self.data["personal_information"]
        recipient = self.data["recipient"]
        letter = self.data["letter"]

        # Sender block: address and contact only (no name), flush left
        addr_line = personal['address'].get('line', '')
        postal = personal['address'].get('postal_code', '')
        # Format like: "Monroe, LA 71203" (no country)
        address_first_line = f"{addr_line} {postal}".strip()

        email = personal.get('email', '')
        phone = personal.get('phone', {}).get('mobile', '')
        homepage = personal.get('homepage', '')
        linkedin = personal.get('linkedin', '')

        # Prepare display URLs without scheme for readability
        def display_url(url: str) -> str:
            return url.replace('https://www.', 'www.').replace('http://www.', 'www.').replace('https://', '').replace('http://', '')

        sender_plain_lines = []
        if address_first_line:
            sender_plain_lines.append(f"{latex_escape(address_first_line)}")
        if phone:
            sender_plain_lines.append(f"{latex_escape(phone)}")
        if email:
            sender_plain_lines.append(f"\\href{{mailto:{email}}}{{{latex_escape(email)}}}")
        # Prefer LinkedIn if provided; also include homepage if present
        if linkedin:
            sender_plain_lines.append(f"\\href{{{linkedin}}}{{{latex_escape(display_url(linkedin))}}}")
        if homepage:
            sender_plain_lines.append(f"\\href{{{homepage}}}{{{latex_escape(display_url(homepage))}}}")

        if sender_plain_lines:
            # Add \noindent to first line, then break lines with \\
            first = "\\noindent " + sender_plain_lines[0]
            rest = sender_plain_lines[1:]
            if rest:
                sender_block = first + "\\\\\n" + "\\\\\n".join(rest)
            else:
                sender_block = first
        else:
            sender_block = ""

        # Recipient block with explicit line breaks (\\) between lines
        recipient_lines = [
            recipient.get('name', ''),
            recipient.get('title', ''),
            recipient.get('company', ''),
            recipient.get('address', ''),
        ]
        recipient_items = [latex_escape(line) for line in recipient_lines if line]
        if recipient_items:
            recipient_block = "\\\\\n".join(recipient_items)
        else:
            recipient_block = ""

        opening = letter.get('opening', 'Dear Hiring Manager')
        # Ensure colon after salutation
        if not opening.endswith(":"):
            opening_with_colon = opening.rstrip(' ,:') + ":"
        else:
            opening_with_colon = opening

        body_formatted = self.format_body_paragraphs(letter.get('body', ''))

        typed_name = latex_escape(personal["name"])

        latex_content = f"""\\documentclass[12pt, letterpaper]{{article}}
\\usepackage[utf8]{{inputenc}}
            \\usepackage[margin=0.75in]{{geometry}}
\\usepackage{{helvet}}
\\usepackage{{calligra}}
\\renewcommand{{\\familydefault}}{{\\sfdefault}}
\\usepackage[hidelinks]{{hyperref}}
\\usepackage{{setspace}}

% Black-and-white, full-block format
\\pagenumbering{{gobble}}
\\setlength{{\\parindent}}{{0pt}}
\\setlength{{\\parskip}}{{12pt}}
\\singlespacing
\\raggedright

\\begin{{document}}

% Date
\\noindent {latex_escape(letter['date'])}

\\vspace{{12pt}}

% Sender address and contact (no name)
{sender_block}

\\vspace{{12pt}}

% Recipient block
\\noindent {recipient_block}

\\vspace{{12pt}}

% Salutation with colon
\\noindent {latex_escape(opening_with_colon)}

% Body paragraphs (single spaced, blank line between)
{body_formatted}

\\vspace{{12pt}}

% Complimentary close with comma
Sincerely,

% Digital signature line
\\vspace{{6pt}}
{{\\fontsize{{20}}{{24}}\\selectfont\\calligra Unika Bista}}
\\vspace{{4pt}}

% Typed name
{typed_name}

\\end{{document}}
"""
        return latex_content

    def save_cover_letter(self, output_file_path, company_name: str):
        output_dir = os.path.dirname(output_file_path)
        os.makedirs(output_dir, exist_ok=True)

        tex_content = self.generate_tex(company_name)
        base_name = os.path.splitext(output_file_path)[0]
        tex_file = base_name + ".tex"

        with open(tex_file, "w", encoding="utf-8") as tex:
            tex.write(tex_content)
        return tex_file

    def generate_pdf(self, output_file_path, output_dir, company_name: str):
        try:
            tex_file = self.save_cover_letter(output_file_path, company_name)
            pdf_file = self.compile_pdf(tex_file, output_dir)
            os.remove(tex_file)
            return pdf_file
        except Exception as e:
            print(f"Failed to generate PDF: {str(e)}")
            raise

    def compile_pdf(self, tex_file, output_dir):
        try:
            output_dir = os.path.dirname(tex_file)
            # Try to find pdflatex in common locations
            pdflatex_paths = [
                "pdflatex",  # If it's in PATH
                "/usr/local/texlive/2024/bin/universal-darwin/pdflatex",
                "/usr/local/texlive/2024/bin/x86_64-darwin/pdflatex",
                "/Library/TeX/texbin/pdflatex",
            ]

            pdflatex_cmd = None
            for path in pdflatex_paths:
                if os.path.exists(path) or path == "pdflatex":
                    try:
                        subprocess.run(
                            [path, "--version"], check=True, capture_output=True
                        )
                        pdflatex_cmd = path
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue

            if not pdflatex_cmd:
                raise Exception(
                    "pdflatex not found. Please install LaTeX (MacTeX) or add it to PATH"
                )

            for _ in range(2):
                result = subprocess.run(
                    [
                        pdflatex_cmd,
                        "-interaction=nonstopmode",
                        "-output-directory=" + output_dir,
                        tex_file,
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0:
                    print(result.stdout)
                    print(result.stderr)
            base_name = os.path.splitext(tex_file)[0]
            for ext in [".aux", ".log", ".out"]:
                aux_file = base_name + ext
                if os.path.exists(aux_file):
                    os.remove(aux_file)
            pdf_file = base_name + ".pdf"
            if os.path.exists(pdf_file):
                return pdf_file
            raise Exception("PDF file was not generated")
        except Exception as e:
            raise Exception(f"Failed to generate PDF: {str(e)}")
