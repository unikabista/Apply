import os
from playwright.sync_api import Page, sync_playwright
from .base import BaseApplier

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sessions")


class LinkedInApplier(BaseApplier):
    """LinkedIn Easy Apply — requires saved session from login.py."""

    PLATFORM = "linkedin"

    def _session_file(self):
        return os.path.join(SESSIONS_DIR, "linkedin_session.json")

    # Override apply() to use persistent session context
    def apply(self, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        if not os.path.exists(resume_pdf):
            return {"success": False, "status": "ERROR", "notes": f"Resume not found: {resume_pdf}"}

        session_file = self._session_file()
        if not os.path.exists(session_file):
            return {"success": False, "status": "BLOCKED",
                    "notes": "LinkedIn not logged in — run: python login.py linkedin"}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.HEADLESS)
            context = browser.new_context(storage_state=session_file)
            page = context.new_page()
            try:
                if not self._is_logged_in(page):
                    return {"success": False, "status": "BLOCKED",
                            "notes": "LinkedIn session expired — run: python login.py linkedin"}
                result = self._apply(page, url, resume_pdf, coverletter_pdf)
            except Exception as e:
                result = {"success": False, "status": "ERROR", "notes": str(e)}
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
        return result

    def _is_logged_in(self, page: Page) -> bool:
        page.goto("https://www.linkedin.com/feed/", wait_until="networkidle", timeout=20000)
        return "linkedin.com/feed" in page.url or "linkedin.com/in/" in page.url

    def _apply(self, page: Page, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        page.goto(url, wait_until="networkidle", timeout=30000)
        self._safe_timeout(page, 2000)

        # Check for Easy Apply button
        easy_apply = page.locator(
            "button.jobs-apply-button:has-text('Easy Apply'), "
            "button:has-text('Easy Apply')"
        ).first
        if not easy_apply.count() or not easy_apply.is_visible():
            return {"success": False, "status": "BLOCKED",
                    "notes": "No Easy Apply button — job requires external site application"}

        easy_apply.click()
        self._safe_timeout(page, 2000)

        return self._walk_wizard(page, self.profile, resume_pdf, coverletter_pdf)

    def _walk_wizard(self, page: Page, p: dict, resume_pdf: str, coverletter_pdf: str) -> dict:
        for step in range(12):
            self._safe_timeout(page, 1500)

            # Fill anything visible on this step
            self._fill_step(page, p, resume_pdf)

            # Dismiss "Your application is on its way" / success
            if page.locator("text=/application sent|on its way/i").count():
                return {"success": True, "status": "submitted",
                        "notes": "LinkedIn Easy Apply submitted"}

            # Error dialog check
            err = page.locator("[data-test-modal-id='easy-apply-error-modal']").first
            if err.count() and err.is_visible():
                return {"success": False, "status": "BLOCKED",
                        "notes": "LinkedIn Easy Apply error modal appeared"}

            # Review → Submit sequence
            review = page.locator("button:has-text('Review')").first
            if review.count() and review.is_visible():
                review.click()
                self._safe_timeout(page, 1500)

            submit = page.locator(
                "button:has-text('Submit application'), button[aria-label*='Submit application']"
            ).first
            if submit.count() and submit.is_visible():
                submit.click()
                self._safe_timeout(page, 3000)
                return {"success": True, "status": "submitted",
                        "notes": "LinkedIn Easy Apply submitted"}

            # Next
            nxt = page.locator("button:has-text('Next')").first
            if nxt.count() and nxt.is_visible():
                nxt.click()
                continue

            # Continue (some steps use this label)
            cont = page.locator("button:has-text('Continue to next step')").first
            if cont.count() and cont.is_visible():
                cont.click()
                continue

            return {"success": False, "status": "BLOCKED",
                    "notes": f"LinkedIn wizard stuck at step {step + 1}"}

        return {"success": False, "status": "BLOCKED", "notes": "LinkedIn wizard exceeded max steps"}

    def _fill_step(self, page: Page, p: dict, resume_pdf: str):
        # Phone (often pre-filled but sometimes blank)
        self.fill(page, [
            "input[name='phoneNumber']",
            "input[id*='phoneNumber' i]",
            "input[placeholder*='Phone' i]",
        ], p["phone_formatted"])

        # Resume: prefer "Upload resume" tab → upload file
        upload_tab = page.locator("label:has-text('Upload resume'), button:has-text('Upload resume')").first
        if upload_tab.count() and upload_tab.is_visible():
            upload_tab.click()
            self._safe_timeout(page, 500)
        self.upload(page, ["input[type='file'][name*='resume' i], input[type='file']"], resume_pdf)

        # Screening questions: text inputs
        for inp in page.locator("input[type='text']:visible, input[type='number']:visible").all():
            try:
                label_id = inp.get_attribute("id") or ""
                lbl = page.locator(f"label[for='{label_id}']").first
                lbl_text = lbl.inner_text().lower() if lbl.count() else ""
                if not inp.input_value() and lbl_text:
                    if "year" in lbl_text and "experience" in lbl_text:
                        inp.fill("2")
                    elif "gpa" in lbl_text:
                        inp.fill(p.get("gpa", "3.8"))
            except Exception:
                continue

        # Yes/No screening
        self.answer_yes_no(page, ["authorized to work", "legally authorized",
                                   "work in the united states"], answer_yes=True)
        self.answer_yes_no(page, ["sponsorship", "require sponsorship",
                                   "will you require"], answer_yes=False)
        self.answer_yes_no(page, ["relocate", "willing to relocate"], answer_yes=True)

        # Dropdowns
        self._handle_dropdowns(page, p)

    def _handle_dropdowns(self, page: Page, p: dict):
        for sel in page.locator("select:visible").all():
            try:
                sel_id = sel.get_attribute("id") or ""
                lbl = page.locator(f"label[for='{sel_id}']").first
                lbl_text = lbl.inner_text().lower() if lbl.count() else ""
                if "gender" in lbl_text:
                    sel.select_option(label="Female")
                elif "race" in lbl_text or "ethnicity" in lbl_text:
                    try:
                        sel.select_option(label="Asian")
                    except Exception:
                        pass
                elif "veteran" in lbl_text:
                    try:
                        sel.select_option(label="I am not a protected veteran")
                    except Exception:
                        pass
                elif "disability" in lbl_text:
                    try:
                        sel.select_option(label="No, I don't have a disability")
                    except Exception:
                        pass
            except Exception:
                continue
