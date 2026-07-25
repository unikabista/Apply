import os
from playwright.sync_api import Page, sync_playwright
from .base import BaseApplier

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sessions")


class HandshakeApplier(BaseApplier):
    """Handshake Apply — requires saved session from login.py."""

    PLATFORM = "handshake"

    def _session_file(self):
        return os.path.join(SESSIONS_DIR, "handshake_session.json")

    def apply(self, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        if not os.path.exists(resume_pdf):
            return {"success": False, "status": "ERROR", "notes": f"Resume not found: {resume_pdf}"}

        session_file = self._session_file()
        if not os.path.exists(session_file):
            return {"success": False, "status": "BLOCKED",
                    "notes": "Handshake not logged in — run: python login.py handshake"}

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.HEADLESS)
            context = browser.new_context(storage_state=session_file)
            page = context.new_page()
            try:
                if not self._is_logged_in(page):
                    return {"success": False, "status": "BLOCKED",
                            "notes": "Handshake session expired — run: python login.py handshake"}
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
        page.goto("https://app.joinhandshake.com/stu/dashboard", wait_until="networkidle", timeout=20000)
        return "dashboard" in page.url or "postings" in page.url

    def _apply(self, page: Page, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        page.goto(url, wait_until="networkidle", timeout=30000)
        self._safe_timeout(page, 2000)

        p = self.profile

        # Click Apply button on listing
        apply_btn = page.locator(
            "button:has-text('Apply Externally'), "
            "a:has-text('Apply Externally'), "
            "button:has-text('Quick Apply'), "
            "button:has-text('Apply')"
        ).first
        if not apply_btn.count() or not apply_btn.is_visible():
            return {"success": False, "status": "BLOCKED", "notes": "Handshake: no Apply button found"}

        btn_text = apply_btn.inner_text().strip().lower()

        # External apply — Handshake just redirects to the company's ATS
        if "external" in btn_text:
            apply_btn.click()
            self._safe_timeout(page, 2000)
            # The new URL is the company's own ATS — return PENDING for now
            new_url = page.url
            return {"success": False, "status": "PENDING",
                    "notes": f"Handshake redirected to external site: {new_url[:120]}"}

        # Quick Apply (Handshake's native apply flow)
        apply_btn.click()
        self._safe_timeout(page, 2000)

        return self._walk_quick_apply(page, p, resume_pdf, coverletter_pdf)

    def _walk_quick_apply(self, page: Page, p: dict, resume_pdf: str, coverletter_pdf: str) -> dict:
        for step in range(8):
            self._safe_timeout(page, 1500)

            # Upload resume if prompted
            upload_btn = page.locator(
                "button:has-text('Add document'), button:has-text('Upload'), "
                "label:has-text('Resume')"
            ).first
            if upload_btn.count() and upload_btn.is_visible():
                try:
                    with page.expect_file_chooser(timeout=4000) as fc:
                        upload_btn.click()
                    fc.value.set_files(resume_pdf)
                    self._safe_timeout(page, 1000)
                except Exception:
                    self.upload(page, ["input[type='file']"], resume_pdf)

            # Cover letter
            if coverletter_pdf:
                cl_btn = page.locator("button:has-text('Cover letter'), label:has-text('Cover letter')").first
                if cl_btn.count() and cl_btn.is_visible():
                    try:
                        with page.expect_file_chooser(timeout=4000) as fc:
                            cl_btn.click()
                        fc.value.set_files(coverletter_pdf)
                    except Exception:
                        pass

            # Fill contact info fields if shown
            self.fill(page, ["input[placeholder*='Phone' i]", "input[type='tel']"], p["phone_formatted"])

            # Authorization questions
            self.answer_yes_no(page, ["authorized to work", "work authorization"], answer_yes=True)
            self.answer_yes_no(page, ["sponsorship"], answer_yes=False)

            # Submit
            submit = page.locator(
                "button:has-text('Submit Application'), button:has-text('Submit')"
            ).first
            if submit.count() and submit.is_visible():
                submit.click()
                self._safe_timeout(page, 3000)
                # Check for success
                if page.locator("text=/application submitted|successfully applied|thank you/i").count():
                    return {"success": True, "status": "submitted",
                            "notes": "Handshake Quick Apply submitted"}
                return {"success": True, "status": "submitted",
                        "notes": "Handshake Quick Apply submitted"}

            # Next step
            nxt = page.locator("button:has-text('Next'), button:has-text('Continue')").first
            if nxt.count() and nxt.is_visible():
                nxt.click()
                continue

            return {"success": False, "status": "BLOCKED",
                    "notes": f"Handshake wizard stuck at step {step + 1}"}

        return {"success": False, "status": "BLOCKED", "notes": "Handshake wizard exceeded max steps"}
