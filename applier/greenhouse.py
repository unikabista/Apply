from playwright.sync_api import Page
from .base import BaseApplier
import time


class GreenhouseApplier(BaseApplier):
    """
    Fills and submits Greenhouse ATS application forms.
    Greenhouse URLs: boards.greenhouse.io/company/jobs/id
    """

    def _apply(self, page: Page, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        page.goto(url, wait_until="networkidle", timeout=30000)
        self._safe_timeout(page, 2000)

        p = self.profile

        # -- Name --------------------------------------------------------
        self.fill(page, [
            "input#first_name",
            "input[name='job_application[first_name]']",
            "input[placeholder*='First' i]",
        ], p["first_name"])
        self.fill(page, [
            "input#last_name",
            "input[name='job_application[last_name]']",
            "input[placeholder*='Last' i]",
        ], p["last_name"])

        # -- Contact -----------------------------------------------------
        self.fill(page, [
            "input#email",
            "input[name='job_application[email]']",
            "input[type='email']",
        ], p["email"])
        self.fill(page, [
            "input#phone",
            "input[name='job_application[phone]']",
            "input[type='tel']",
        ], p["phone_formatted"])

        # -- Location ----------------------------------------------------
        self.fill(page, [
            "input#job_application_location",
            "input[placeholder*='City' i]",
            "input[placeholder*='Location' i]",
        ], p["city"])

        # -- Resume upload -----------------------------------------------
        uploaded = self.upload(page, [
            "input#resume",
            "input[name='job_application[resume]']",
            "input[data-source='resume']",
        ], resume_pdf)
        if not uploaded:
            self.upload_via_button(page, [
                "button:has-text('Upload')",
                "label:has-text('Resume')",
            ], resume_pdf)

        # -- Cover letter (optional) -------------------------------------
        if coverletter_pdf:
            uploaded_cl = self.upload(page, [
                "input#cover_letter",
                "input[name='job_application[cover_letter]']",
            ], coverletter_pdf)
            if not uploaded_cl:
                self.upload_via_button(page, [
                    "label:has-text('Cover Letter')",
                    "button:has-text('Cover Letter')",
                ], coverletter_pdf)

        # -- LinkedIn ----------------------------------------------------
        self.fill(page, [
            "input#job_application_linkedin_profile_url",
            "input[placeholder*='linkedin' i]",
            "input[label*='LinkedIn' i]",
        ], p["linkedin"])

        # -- Education ---------------------------------------------------
        self._fill_education(page, p)

        # -- Work authorization ------------------------------------------
        self._fill_authorization(page, p)

        # -- EEO / demographics ------------------------------------------
        self._fill_eeo(page, p)

        # -- Submit ------------------------------------------------------
        self._safe_timeout(page, 1000)
        if self.submit(page):
            self._safe_timeout(page, 3000)
            return {"success": True, "status": "submitted", "notes": "Greenhouse form submitted"}

        return {"success": False, "status": "BLOCKED", "notes": "Could not find or click submit button"}

    def _fill_education(self, page: Page, p: dict):
        # School — Greenhouse uses a combobox with typeahead
        school_sel = "input#job_application_school_name_text, input[placeholder*='school' i], input[placeholder*='School' i]"
        try:
            school_input = page.locator(school_sel).first
            if school_input.count() and school_input.is_visible():
                school_input.fill(p["school_greenhouse"])
                self._safe_timeout(page, 800)
                # Pick first suggestion
                suggestion = page.locator("li:has-text('Louisiana')").first
                if suggestion.count():
                    suggestion.click()
                else:
                    school_input.press("Enter")
        except Exception:
            pass

        # Degree dropdown
        self.select_option(page, [
            "select#job_application_degree",
            "select[name*='degree' i]",
        ], "Bachelor's Degree")

        # Discipline / major
        self.fill(page, [
            "input#job_application_discipline",
            "input[placeholder*='Discipline' i]",
            "input[placeholder*='Major' i]",
        ], p["discipline"])
        self.select_option(page, [
            "select#job_application_discipline",
        ], "Computer Science")

        # Graduation year
        self.fill(page, [
            "input#job_application_end_date",
            "input[placeholder*='graduation' i]",
            "input[placeholder*='Graduation' i]",
        ], p["graduation_year"])
        self.select_option(page, [
            "select#job_application_end_date",
        ], p["graduation_year"])

    def _fill_authorization(self, page: Page, p: dict):
        # Greenhouse uses radio groups for work authorization
        auth_answer = "Yes" if p["work_authorized"] else "No"
        sponsor_answer = "No" if not p["requires_sponsorship"] else "Yes"

        for question_hint in ["authorized to work", "legally authorized", "work in the united states"]:
            self.click_radio_or_button(page, question_hint, auth_answer)

        for question_hint in ["sponsorship", "require sponsorship", "will you require"]:
            self.click_radio_or_button(page, question_hint, sponsor_answer)

        # Greenhouse radio buttons sometimes need DOM manipulation
        try:
            page.evaluate("""
                document.querySelectorAll('input[type="radio"]').forEach(r => {
                    const label = r.closest('label') || document.querySelector(`label[for="${r.id}"]`);
                    const text = (label ? label.textContent : r.value || '').trim().toLowerCase();
                    const q = r.closest('.field, .question, [class*="question"]');
                    const qText = q ? q.textContent.toLowerCase() : '';
                    if ((qText.includes('authorized') || qText.includes('authorization')) && text === 'yes') {
                        r.checked = true; r.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                    if (qText.includes('sponsorship') && text === 'no') {
                        r.checked = true; r.dispatchEvent(new Event('change', {bubbles: true}));
                    }
                });
            """)
        except Exception:
            pass

    def _fill_eeo(self, page: Page, p: dict):
        # Gender
        self.select_option(page, [
            "select#job_application_gender",
            "select[name*='gender' i]",
        ], "Female")
        self.click_radio_or_button(page, "gender", "Female")
        self.click_radio_or_button(page, "gender", "Woman")

        # Race
        self.select_option(page, [
            "select#job_application_race",
            "select[name*='race' i]",
            "select[name*='ethnicity' i]",
        ], "Asian")
        self.click_radio_or_button(page, "race", "Asian")

        # Veteran
        self.select_option(page, [
            "select#job_application_veteran_status",
        ], "I am not a protected veteran")
        self.click_radio_or_button(page, "veteran", "No")

        # Disability
        self.select_option(page, [
            "select#job_application_disability_status",
        ], "No, I don't have a disability")
        self.click_radio_or_button(page, "disability", "No")
