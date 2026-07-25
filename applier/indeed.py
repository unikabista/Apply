import os
from playwright.sync_api import Page, sync_playwright
from .base import BaseApplier

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sessions")


class IndeedApplier(BaseApplier):
    """Indeed Apply — requires saved session from login.py."""

    PLATFORM = "indeed"

    def _session_file(self):
        return os.path.join(SESSIONS_DIR, "indeed_session.json")

    def apply(self, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        if not os.path.exists(resume_pdf):
            return {"success": False, "status": "ERROR", "notes": f"Resume not found: {resume_pdf}"}

        session_file = self._session_file()
        if not os.path.exists(session_file):
            return {"success": False, "status": "BLOCKED",
                    "notes": "Indeed not logged in — run: python login.py indeed"}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.HEADLESS)
            context = browser.new_context(storage_state=session_file)
            page = context.new_page()
            try:
                if not self._is_logged_in(page):
                    return {"success": False, "status": "BLOCKED",
                            "notes": "Indeed session expired — run: python login.py indeed"}
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
        page.goto("https://www.indeed.com/", wait_until="networkidle", timeout=20000)
        self._safe_timeout(page, 1500)
        # If logged in, the sign-in button is replaced with account menu
        sign_in = page.locator("a[href*='login'], a:has-text('Sign in')").first
        return not (sign_in.count() and sign_in.is_visible())

    def _apply(self, page: Page, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        page.goto(url, wait_until="networkidle", timeout=30000)
        self._safe_timeout(page, 2000)

        p = self.profile

        # Click "Apply now" — Indeed Apply opens an iframe or same-page form
        apply_btn = page.locator(
            "button[id*='indeedApplyButton'], "
            "button:has-text('Apply now'), "
            "a:has-text('Apply now')"
        ).first
        if not apply_btn.count() or not apply_btn.is_visible():
            return {"success": False, "status": "BLOCKED",
                    "notes": "No Indeed Apply button — job may redirect to external site"}

        apply_btn.click()
        self._safe_timeout(page, 2500)

        # Indeed Apply opens in an iframe or new tab
        # Check for iframe first
        frame = page.frame_locator("iframe[title*='apply' i], iframe[src*='indeedapply' i]").first
        if frame:
            return self._fill_indeed_iframe(page, frame, p, resume_pdf, coverletter_pdf)

        # Otherwise fill on the page directly
        return self._fill_indeed_page(page, p, resume_pdf, coverletter_pdf)

    def _fill_indeed_iframe(self, page: Page, frame, p: dict, resume_pdf: str, coverletter_pdf: str) -> dict:
        """Fill the Indeed Apply iframe form."""
        for step in range(10):
            self._safe_timeout(page, 1500)

            # Resume upload
            try:
                upload_btn = frame.locator("button:has-text('Upload resume'), label:has-text('Resume')").first
                if upload_btn.count() and upload_btn.is_visible():
                    with page.expect_file_chooser(timeout=5000) as fc:
                        upload_btn.click()
                    fc.value.set_files(resume_pdf)
                    self._safe_timeout(page, 1000)
            except Exception:
                pass

            # Fill contact fields inside iframe
            self._iframe_fill(frame, ["input[name='applicant.name']",
                                       "input[placeholder*='Full name' i]"], p["name"])
            self._iframe_fill(frame, ["input[name='applicant.email']",
                                       "input[type='email']"], p["email"])
            self._iframe_fill(frame, ["input[name='applicant.phoneNumber']",
                                       "input[type='tel']"], p["phone_formatted"])

            # Screening questions
            self._iframe_answer_yes_no(frame, ["authorized", "work authorization"], True)
            self._iframe_answer_yes_no(frame, ["sponsorship"], False)

            # Check for success
            if frame.locator("text=/application submitted|thank you/i").count():
                return {"success": True, "status": "submitted", "notes": "Indeed Apply submitted"}

            # Submit button
            submit = frame.locator("button:has-text('Submit your application'), "
                                    "button:has-text('Submit')").first
            if submit.count() and submit.is_visible():
                submit.click()
                self._safe_timeout(page, 3000)
                return {"success": True, "status": "submitted", "notes": "Indeed Apply submitted"}

            # Continue / Next
            nxt = frame.locator("button:has-text('Continue'), button:has-text('Next')").first
            if nxt.count() and nxt.is_visible():
                nxt.click()
                continue

            return {"success": False, "status": "BLOCKED",
                    "notes": f"Indeed iframe stuck at step {step + 1}"}

        return {"success": False, "status": "BLOCKED", "notes": "Indeed wizard exceeded max steps"}

    def _fill_indeed_page(self, page: Page, p: dict, resume_pdf: str, coverletter_pdf: str) -> dict:
        """Fill Indeed Apply when it renders directly on the page."""
        self.fill(page, ["input[name='applicant.name']", "input[placeholder*='Full name' i]"], p["name"])
        self.fill(page, ["input[type='email']"], p["email"])
        self.fill(page, ["input[type='tel']"], p["phone_formatted"])
        self.upload(page, ["input[type='file']"], resume_pdf)
        self.answer_yes_no(page, ["authorized", "work authorization"], answer_yes=True)
        self.answer_yes_no(page, ["sponsorship"], answer_yes=False)
        self._safe_timeout(page, 1000)
        if self.submit(page):
            self._safe_timeout(page, 3000)
            return {"success": True, "status": "submitted", "notes": "Indeed Apply submitted"}
        return {"success": False, "status": "BLOCKED", "notes": "Could not find submit button"}

    def _iframe_fill(self, frame, selectors: list, value: str) -> bool:
        for sel in selectors:
            try:
                loc = frame.locator(sel).first
                if loc.count() and loc.is_visible():
                    loc.clear()
                    loc.fill(value)
                    return True
            except Exception:
                continue
        return False

    def _iframe_answer_yes_no(self, frame, keywords: list, answer_yes: bool):
        target = "Yes" if answer_yes else "No"
        for kw in keywords:
            try:
                container = frame.locator(f"*:has-text('{kw}')").last
                btn = container.locator(f"button:has-text('{target}'), label:has-text('{target}')").first
                if btn.count() and btn.is_visible():
                    btn.click()
                    return
            except Exception:
                continue
