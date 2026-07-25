import re
from playwright.sync_api import Page
from .base import BaseApplier


class AshbyApplier(BaseApplier):
    """
    Fills and submits Ashby ATS application forms.
    Ashby URLs: jobs.ashbyhq.com/company/role-id  (or .../application)
    """

    def _apply(self, page: Page, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        if not url.rstrip("/").endswith("/application"):
            url = url.rstrip("/") + "/application"
        page.goto(url, wait_until="networkidle", timeout=30000)
        self._safe_wait(page, 2000)

        # Bail out if the page redirected away from Ashby (job closed / 404)
        if not self._is_alive(page):
            return {"success": False, "status": "CLOSED",
                    "notes": "Page closed after navigation"}
        current_url = page.url.lower()
        if "ashbyhq.com" not in current_url:
            return {"success": False, "status": "CLOSED",
                    "notes": f"Redirected away from Ashby: {page.url[:120]}"}

        p = self.profile

        # Upload resume first — Ashby can autofill name/email from it
        uploaded = self._upload_resume(page, resume_pdf)
        if not uploaded:
            return {"success": False, "status": "BLOCKED",
                    "notes": "Could not upload resume — no file input found"}
        if not self._is_alive(page):
            return {"success": False, "status": "ERROR",
                    "notes": "Page closed after resume upload"}
        self._safe_wait(page, 2500)  # let Ashby parse and autofill

        # Text fields — match by accessible name (Ashby sets aria-label = label text)
        # Fill first/last before full name so the generic "name" pattern hits the right field
        self._fill_labeled(page, r"first.?name", p["first_name"])
        self._fill_labeled(page, r"last.?name", p["last_name"])
        self._fill_labeled(page, r"^name\b", p["name"])  # matches "Name*" not "First Name*"
        self._fill_labeled(page, r"email", p["email"])
        self._fill_labeled(page, r"phone", p["phone_formatted"])
        self._fill_labeled(page, r"linkedin", p["linkedin"])

        # Personal website — required on many Ashby forms; fall back to LinkedIn
        website = p.get("website") or p.get("github") or p["linkedin"]
        self._fill_labeled(page, r"website|portfolio|personal.{0,15}project|video", website)

        # Location combobox typeahead
        self._fill_location(page, p.get("city", "Dallas"))

        # Yes / No toggles
        self.answer_yes_no(page, [
            "sponsorship", "require sponsorship",
            "visa sponsorship", "will you now or in the future",
        ], answer_yes=False)
        self.answer_yes_no(page, [
            "relocate", "willing to relocate", "open to relocation",
        ], answer_yes=True)
        self.answer_yes_no(page, [
            "authorized", "legally authorized", "work authorization",
        ], answer_yes=True)

        # Optional project blurb ("Share something cool you've built")
        blurb = p.get("project_blurb", "")
        if blurb:
            self._fill_labeled(page, r"share.{0,20}built|cool|project|describe", blurb)

        # Cover letter (best-effort second file upload)
        if coverletter_pdf:
            uploaded_cl = self.upload_via_button(page, [
                "button:has-text('Cover Letter')",
                "label:has-text('Cover Letter')",
                "*[data-testid='coverLetter-upload']",
            ], coverletter_pdf)
            if not uploaded_cl:
                self._upload_file_fallback(page, coverletter_pdf, skip_first=True)

        # Demographics (best-effort, non-blocking)
        self._fill_demographics(page, p)

        # Submit
        self._safe_wait(page, 1000)
        if not self.submit(page):
            return {"success": False, "status": "BLOCKED",
                    "notes": "Could not find or click Submit button"}

        return self._verify_submission(page)

    # ------------------------------------------------------------------ #
    # Field helpers                                                        #
    # ------------------------------------------------------------------ #

    def _safe_wait(self, page: Page, ms: int):
        self._safe_timeout(page, ms)

    def _fill_labeled(self, page: Page, label_regex: str, value: str) -> bool:
        """Fill the first visible textbox whose accessible name matches label_regex."""
        if not value:
            return False
        pattern = re.compile(label_regex, re.I)

        # Primary: Playwright role-based lookup — matches Ashby's aria-label structure
        try:
            loc = page.get_by_role("textbox", name=pattern).first
            if loc.count() and loc.is_visible():
                loc.clear()
                loc.fill(value)
                return True
        except Exception:
            pass

        # Fallback: scan aria-label attributes directly
        try:
            for loc in page.locator("input, textarea").all():
                try:
                    lbl = loc.get_attribute("aria-label") or ""
                    if pattern.search(lbl) and loc.is_visible():
                        loc.clear()
                        loc.fill(value)
                        return True
                except Exception:
                    continue
        except Exception:
            pass

        return False

    def _fill_location(self, page: Page, city: str) -> bool:
        """Type into Ashby's location combobox and select the first suggestion."""
        try:
            combo = page.locator("[role='combobox']").first
            if combo.count() and combo.is_visible():
                combo.click()
                combo.fill(city)
                self._safe_wait(page, 1500)
                option = page.locator("[role='option']").first
                if option.count() and option.is_visible():
                    option.click()
                    return True
        except Exception:
            pass
        # Fallback: plain text fill (some Ashby forms use a regular input)
        return self.fill(page, [
            "input[placeholder*='Start typing' i]",
            "input[placeholder*='location' i]",
            "input[placeholder*='city' i]",
            "input[placeholder*='based' i]",
        ], city)

    def _upload_resume(self, page: Page, resume_pdf: str) -> bool:
        uploaded = self.upload_via_button(page, [
            "button:has-text('Upload File')",
            "button:has-text('Upload file')",
            "button:has-text('Upload')",
            "label:has-text('Resume')",
            "*[data-testid='resume-upload']",
        ], resume_pdf)
        if not uploaded:
            uploaded = self.upload(page, ["input[type='file']"], resume_pdf)
        return uploaded

    def _upload_file_fallback(self, page: Page, file_path: str, skip_first: bool = False):
        try:
            inputs = page.locator("input[type='file']").all()
            idx = 1 if skip_first else 0
            if len(inputs) > idx:
                inputs[idx].set_input_files(file_path)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Submission verification                                              #
    # ------------------------------------------------------------------ #

    def _verify_submission(self, page: Page) -> dict:
        confirmed = False
        try:
            page.wait_for_url("**/confirmation**", timeout=10000)
            confirmed = True
        except Exception:
            pass

        if not confirmed:
            try:
                page.wait_for_selector(
                    "text=/thank you|application received|successfully submitted|application submitted/i",
                    timeout=8000,
                )
                confirmed = True
            except Exception:
                pass

        if not confirmed:
            try:
                errors = page.locator("[class*='error' i], [aria-invalid='true']").all()
                visible = [e for e in errors if e.is_visible()]
                if visible:
                    err_text = "; ".join(
                        e.inner_text() for e in visible[:3] if e.inner_text().strip()
                    )
                    return {"success": False, "status": "BLOCKED",
                            "notes": f"Validation errors: {err_text}"}
            except Exception:
                pass
            return {"success": False, "status": "BLOCKED",
                    "notes": "Submit clicked but no confirmation page or message detected"}

        return {"success": True, "status": "submitted",
                "notes": "Ashby confirmation page reached"}

    # ------------------------------------------------------------------ #
    # Demographics                                                         #
    # ------------------------------------------------------------------ #

    def _fill_demographics(self, page: Page, p: dict):
        if p.get("pronouns"):
            self._fill_labeled(page, r"pronoun", p["pronouns"])
            self.select_option(page, [
                "select[name*='pronoun' i]", "select[id*='pronoun' i]",
            ], p["pronouns"])
        self.select_option(page, [
            "select[name*='gender' i]", "select[id*='gender' i]",
        ], p["gender"])
        self.select_option(page, [
            "select[name*='race' i]", "select[name*='ethnicity' i]", "select[id*='race' i]",
        ], "Asian")
        self.answer_yes_no(page, ["veteran"], answer_yes=p["veteran"])
        self.answer_yes_no(page, ["disability", "disabled"], answer_yes=p["disability"])
