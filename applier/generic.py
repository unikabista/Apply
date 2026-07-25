from playwright.sync_api import Page
from .base import BaseApplier


class GenericApplier(BaseApplier):
    """
    Best-effort applier for unknown / miscellaneous ATS platforms.
    Uses broad common-pattern selectors. Success is best-effort — not guaranteed.
    """

    def _apply(self, page: Page, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        page.goto(url, wait_until="networkidle", timeout=30000)
        self._safe_timeout(page, 2000)

        p = self.profile

        # Try to click Apply button if we're on a listing page
        self.click(page, [
            "a:has-text('Apply Now')",
            "button:has-text('Apply Now')",
            "a:has-text('Apply for this Job')",
            "button:has-text('Apply for this Job')",
            "a:has-text('Apply for this Position')",
            "button:has-text('Apply for this Position')",
            "a:has-text('Apply')",
            "button:has-text('Apply')",
        ])
        self._safe_timeout(page, 2000)

        # Fill fields
        self._fill_name(page, p)
        self._fill_contact(page, p)
        self._fill_resume(page, resume_pdf)
        if coverletter_pdf:
            self._fill_coverletter(page, coverletter_pdf)
        self._fill_auth(page, p)

        # Submit
        self._safe_timeout(page, 1000)
        submitted = self.submit(page)
        if not submitted:
            return {"success": False, "status": "BLOCKED",
                    "notes": "Generic applier: could not find submit button"}

        self._safe_timeout(page, 3000)
        try:
            page.wait_for_selector(
                "text=/thank you|submitted|received|success|application sent/i",
                timeout=6000,
            )
            return {"success": True, "status": "submitted", "notes": "Generic form submitted"}
        except Exception:
            return {"success": False, "status": "BLOCKED",
                    "notes": "Generic applier: submitted but no confirmation — verify manually"}

    def _fill_name(self, page: Page, p: dict):
        self.fill(page, [
            "input[name='first_name']", "input[id*='first' i]",
            "input[placeholder*='First name' i]", "input[autocomplete='given-name']",
        ], p["first_name"])
        self.fill(page, [
            "input[name='last_name']", "input[id*='last' i]",
            "input[placeholder*='Last name' i]", "input[autocomplete='family-name']",
        ], p["last_name"])
        # Full name fallback (only if first/last not filled separately)
        self.fill(page, [
            "input[name='name']", "input[id='name']",
            "input[placeholder*='Full name' i]", "input[autocomplete='name']",
        ], p["name"])

    def _fill_contact(self, page: Page, p: dict):
        self.fill(page, [
            "input[type='email']", "input[name='email']",
            "input[id*='email' i]", "input[placeholder*='Email' i]",
            "input[autocomplete='email']",
        ], p["email"])
        self.fill(page, [
            "input[type='tel']", "input[name='phone']",
            "input[id*='phone' i]", "input[placeholder*='Phone' i]",
            "input[autocomplete='tel']",
        ], p["phone_formatted"])
        self.fill(page, [
            "input[name='location']", "input[id*='location' i]",
            "input[placeholder*='Location' i]", "input[placeholder*='City' i]",
        ], p["location"])
        self.fill(page, [
            "input[name='linkedin']", "input[id*='linkedin' i]",
            "input[placeholder*='LinkedIn' i]",
        ], p["linkedin"])

    def _fill_resume(self, page: Page, resume_pdf: str):
        uploaded = self.upload_via_button(page, [
            "button:has-text('Upload Resume')",
            "button:has-text('Upload CV')",
            "button:has-text('Upload')",
            "label:has-text('Resume')",
            "label:has-text('CV')",
            "label:has-text('Attach')",
        ], resume_pdf)
        if not uploaded:
            self.upload(page, ["input[type='file']"], resume_pdf)

    def _fill_coverletter(self, page: Page, coverletter_pdf: str):
        self.upload_via_button(page, [
            "button:has-text('Cover Letter')",
            "button:has-text('Cover letter')",
            "label:has-text('Cover Letter')",
            "label:has-text('Cover letter')",
        ], coverletter_pdf)

    def _fill_auth(self, page: Page, p: dict):
        self.answer_yes_no(page, ["authorized to work", "legally authorized",
                                   "authorized to work in the united states"], answer_yes=True)
        self.answer_yes_no(page, ["sponsorship", "require sponsorship",
                                   "will you require sponsorship"], answer_yes=False)
        self.answer_yes_no(page, ["relocate", "willing to relocate"], answer_yes=True)
