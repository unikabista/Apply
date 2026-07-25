from playwright.sync_api import sync_playwright, Page, Browser
import os


class BaseApplier:
    """Shared Playwright helpers. Subclass per ATS platform."""

    HEADLESS = False  # keep visible so user can supervise or intervene

    def __init__(self, profile: dict):
        self.profile = profile

    # ------------------------------------------------------------------ #
    # Public entry point                                                   #
    # ------------------------------------------------------------------ #

    def apply(self, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        """
        Open the application URL, fill the form, and submit.
        Returns {"success": bool, "status": str, "notes": str}
        """
        if not os.path.exists(resume_pdf):
            return {"success": False, "status": "ERROR", "notes": f"Resume not found: {resume_pdf}"}

        with sync_playwright() as p:
            browser: Browser = p.chromium.launch(headless=self.HEADLESS)
            context = browser.new_context()
            page = context.new_page()
            try:
                result = self._apply(page, url, resume_pdf, coverletter_pdf)
            except Exception as e:
                result = {"success": False, "status": "ERROR", "notes": str(e)}
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
        return result

    # ------------------------------------------------------------------ #
    # Page health helper                                                   #
    # ------------------------------------------------------------------ #

    def _is_alive(self, page: Page) -> bool:
        """Return True if the page is still open and usable."""
        try:
            return not page.is_closed()
        except Exception:
            return False

    def _safe_timeout(self, page: Page, ms: int):
        """Wait ms milliseconds, silently ignoring any page-closed error."""
        try:
            if self._is_alive(page):
                page.wait_for_timeout(ms)
        except Exception:
            pass

    def _apply(self, page: Page, url: str, resume_pdf: str, coverletter_pdf: str) -> dict:
        raise NotImplementedError

    # ------------------------------------------------------------------ #
    # Shared helpers                                                       #
    # ------------------------------------------------------------------ #

    def fill(self, page: Page, selectors: list, value: str, clear: bool = True) -> bool:
        """Try each selector in order; fill the first visible match."""
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if loc.count() and loc.is_visible():
                    if clear:
                        loc.clear()
                    loc.fill(value)
                    return True
            except Exception:
                continue
        return False

    def click(self, page: Page, selectors: list) -> bool:
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if loc.count() and loc.is_visible():
                    loc.click(force=True)
                    return True
            except Exception:
                continue
        return False

    def select_option(self, page: Page, selectors: list, value: str) -> bool:
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if loc.count() and loc.is_visible():
                    loc.select_option(label=value)
                    return True
            except Exception:
                continue
        return False

    def upload(self, page: Page, selectors: list, file_path: str) -> bool:
        """Set file on a visible <input type=file>."""
        for sel in selectors:
            try:
                loc = page.locator(sel).first
                if loc.count():
                    loc.set_input_files(file_path)
                    return True
            except Exception:
                continue
        return False

    def upload_via_button(self, page: Page, button_selectors: list, file_path: str) -> bool:
        """Click a button that triggers a file chooser, then set the file."""
        for sel in button_selectors:
            if not self._is_alive(page):
                return False
            try:
                with page.expect_file_chooser(timeout=5000) as fc_info:
                    page.locator(sel).first.click()
                fc_info.value.set_files(file_path)
                return True
            except Exception:
                continue
        return False

    def click_radio_or_button(self, page: Page, container_text: str, option_text: str) -> bool:
        """
        Find a container whose text includes container_text, then click
        a child element whose text matches option_text.
        Handles both <button> and <label>/<input type=radio> patterns.
        """
        try:
            container = page.locator(
                f"*:has-text('{container_text}')"
            ).last
            # Try button children first
            btn = container.locator(f"button:has-text('{option_text}')").first
            if btn.count() and btn.is_visible():
                btn.click(force=True)
                return True
            # Try label children
            lbl = container.locator(f"label:has-text('{option_text}')").first
            if lbl.count() and lbl.is_visible():
                lbl.click(force=True)
                return True
        except Exception:
            pass
        return False

    def answer_yes_no(self, page: Page, question_keywords: list, answer_yes: bool) -> bool:
        target = "Yes" if answer_yes else "No"
        for kw in question_keywords:
            if self.click_radio_or_button(page, kw, target):
                return True
        return False

    def submit(self, page: Page) -> bool:
        return self.click(page, [
            "button[type='submit']",
            "button:has-text('Submit Application')",
            "button:has-text('Submit')",
            "input[type='submit']",
            "button:has-text('Apply')",
        ])
