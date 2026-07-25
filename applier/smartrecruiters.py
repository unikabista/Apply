from playwright.sync_api import Page
from .base import BaseApplier


class SmartRecruitersApplier(BaseApplier):
    """
    SmartRecruiters ATS: careers.smartrecruiters.com or jobs.smartrecruiters.com
    """

    def _apply(self, page: Page, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        page.goto(url, wait_until="networkidle", timeout=30000)
        self._safe_timeout(page, 2000)

        p = self.profile

        # Click Apply Now on listing page
        self.click(page, [
            "button[data-qa='btn-apply-bottom']",
            "button[data-qa='btn-apply-top']",
            "a[data-qa='btn-apply-bottom']",
            "button:has-text('Apply Now')",
            "a:has-text('Apply Now')",
            "button:has-text('Apply')",
        ])
        self._safe_timeout(page, 2500)

        # Resume upload first (SR usually leads with resume)
        uploaded = self.upload_via_button(page, [
            "button[data-qa='upload-resume']",
            "label[data-qa='upload-resume']",
            "button:has-text('Upload')",
            "label:has-text('Resume')",
            "label:has-text('CV')",
        ], resume_pdf)
        if not uploaded:
            self.upload(page, ["input[type='file']"], resume_pdf)
        self._safe_timeout(page, 2000)

        # Personal info
        self.fill(page, ["input[name='firstName']", "input[data-qa='firstName']",
                          "input[placeholder*='First' i]"], p["first_name"])
        self.fill(page, ["input[name='lastName']", "input[data-qa='lastName']",
                          "input[placeholder*='Last' i]"], p["last_name"])
        self.fill(page, ["input[name='email']", "input[data-qa='email']",
                          "input[type='email']"], p["email"])
        self.fill(page, ["input[name='phoneNumber']", "input[data-qa='phone']",
                          "input[type='tel']"], p["phone_formatted"])

        # Location
        self.fill(page, ["input[name='city']", "input[data-qa='city']",
                          "input[placeholder*='City' i]",
                          "input[placeholder*='Location' i]"], p["city"])

        # LinkedIn / website
        self.fill(page, ["input[name='web-LinkedIn']", "input[placeholder*='LinkedIn' i]",
                          "input[data-qa='linkedInProfile']"], p["linkedin"])

        # Cover letter
        if coverletter_pdf:
            self.upload_via_button(page, [
                "button:has-text('Cover letter')",
                "button:has-text('Cover Letter')",
                "label:has-text('Cover letter')",
            ], coverletter_pdf)

        # Authorization questions
        self.answer_yes_no(page, ["authorized to work", "legally authorized"], answer_yes=True)
        self.answer_yes_no(page, ["sponsorship", "require sponsorship"], answer_yes=False)

        # Submit
        self._safe_timeout(page, 1000)
        submitted = self.click(page, [
            "button[data-qa='btn-submit']",
            "button:has-text('Send Application')",
            "button:has-text('Submit Application')",
            "button:has-text('Submit')",
            "button[type='submit']",
        ])
        if not submitted:
            return {"success": False, "status": "BLOCKED",
                    "notes": "SmartRecruiters: could not find submit button"}

        self._safe_timeout(page, 3000)
        try:
            page.wait_for_selector(
                "text=/thank you|application sent|successfully submitted|received/i",
                timeout=8000,
            )
            return {"success": True, "status": "submitted",
                    "notes": "SmartRecruiters application sent"}
        except Exception:
            return {"success": False, "status": "BLOCKED",
                    "notes": "SmartRecruiters: submitted but no confirmation — verify manually"}
