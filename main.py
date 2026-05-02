from datetime import datetime
import os
from resume.generator import ResumeGenerator
from coverletter.generator import CoverLetterGenerator


def get_user_choice():
    while True:
        print("\nWhat would you like to generate?")
        print("1. Resume only")
        print("2. Cover Letter only")
        print("3. Both Resume and Cover Letter")
        choice = input("Enter your choice (1-3): ")

        if choice in ['1', '2', '3']:
            return choice


def get_company_name():
    return input("\nEnter company name: ").strip()


def get_role_name():
    return input("\nEnter role name (e.g. Software Engineer Intern): ").strip()


def get_job_description():
    """Accept a job URL or pasted text. If a URL is given, scrape it automatically."""
    print("\nEnter job URL or paste job description (type END on a new line when done, press Enter to skip):")
    first_line = input().strip()

    # If the user gave a URL, scrape it automatically
    # Why check for http? That's how all web URLs start — it's a reliable signal
    if first_line.startswith("http://") or first_line.startswith("https://"):
        print("  URL detected — scraping job description...")
        try:
            from jobdescription.scraptor import JobDescriptionScraper
            scraper = JobDescriptionScraper()
            return scraper.scrape(first_line)
        except Exception as e:
            print(f"  Warning: Could not scrape URL ({e}). Please paste the job description manually.")
            return ""

    # Otherwise treat it as pasted text
    if first_line == "":
        return ""

    lines = [first_line]
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def create_output_structure(base_dir, company_name, role_name):
    """Create simplified output directory structure: applications/COMPANY/"""
    company_dir = company_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
    output_path = os.path.join(base_dir, "applications", company_dir)
    os.makedirs(output_path, exist_ok=True)
    return output_path


def generate_filename(role_name, file_type):
    """Generate filename following convention: Unika_Bista_Resume_PositionTitle.pdf"""
    position_title = role_name.replace(' ', '').replace('/', '').replace('\\', '').replace('&', 'and')

    if file_type.lower() == 'resume':
        return f"Unika_Bista_Resume_{position_title}.pdf"
    elif file_type.lower() == 'coverletter':
        return f"Unika_Bista_CoverLetter_{position_title}.pdf"
    else:
        return f"Unika_Bista_{file_type}_{position_title}.pdf"


def cli_main():
    base_dir = os.getcwd()
    company_name = get_company_name()
    role_name = get_role_name()
    job_description = get_job_description()

    # Create organized output directory
    output_dir = create_output_structure(base_dir, company_name, role_name)

    # Save job description if provided
    if job_description:
        with open(os.path.join(output_dir, 'job_description.txt'), 'w') as f:
            f.write(job_description)

    choice = get_user_choice()

    # Tailor resume data if job description was provided
    tailored_resume_data = None
    tailored_coverletter_data = None

    if job_description:
        print("\nTailoring documents to job description...")
        import yaml

        if choice in ['1', '3']:
            from tailoring.tailor import tailor_resume
            with open(os.path.join(base_dir, "resume", "resume.yml"), "r", encoding="utf-8") as f:
                resume_data = yaml.safe_load(f)
            try:
                tailored_resume_data = tailor_resume(resume_data, job_description)
            except Exception as e:
                print(f"  Warning: AI tailoring failed ({e}). Using base resume.")

        if choice in ['2', '3']:
            from tailoring.tailor import tailor_cover_letter
            with open(os.path.join(base_dir, "coverletter", "coverletter.yml"), "r", encoding="utf-8") as f:
                coverletter_data = yaml.safe_load(f)
            try:
                tailored_coverletter_data = tailor_cover_letter(coverletter_data, job_description, company_name, role_name)
            except Exception as e:
                print(f"  Warning: AI cover letter tailoring failed ({e}). Using base cover letter.")
    else:
        print("\nNo job description provided. Generating with base resume.")

    # Generate documents
    if choice in ['1', '3']:
        resume_filename = generate_filename(role_name, 'resume')
        resume_file = os.path.join(output_dir, resume_filename)
        resume_generator = ResumeGenerator(os.path.join(base_dir, "resume", "resume.yml"))
        if tailored_resume_data:
            resume_generator.data = tailored_resume_data
        output_file = resume_generator.generate_pdf(resume_file, output_dir)
        print(f"\nResume generated: {output_file}")

    if choice in ['2', '3']:
        coverletter_filename = generate_filename(role_name, 'coverletter')
        cover_letter_file = os.path.join(output_dir, coverletter_filename)
        coverletter_generator = CoverLetterGenerator(os.path.join(base_dir, "coverletter", "coverletter.yml"))
        if tailored_coverletter_data:
            coverletter_generator.data = tailored_coverletter_data
        output_file = coverletter_generator.generate_pdf(cover_letter_file, output_dir, company_name)
        print(f"\nCover letter generated: {output_file}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--ui', action='store_true', help='Launch GUI version')
    args = parser.parse_args()

    if args.ui:
        try:
            from ui import main as ui_main
            ui_main()
        except ImportError as e:
            print("\nError: PyQt6 is not properly installed.")
            print("Please run: pip install PyQt6 PyQt6-Qt6 PyQt6-sip")
            print(f"Original error: {str(e)}")
        except Exception as e:
            print(f"\nFailed to start UI: {str(e)}")
    else:
        cli_main()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
