from playwright.sync_api import Page
from .base import BaseApplier


class LeverApplier(BaseApplier):
    """
    Fills and submits Lever ATS application forms.
    Lever URLs: jobs.lever.co/company/job-id
    """

    def _apply(self, page: Page, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        page.goto(url, wait_until="networkidle", timeout=30000)
        self._safe_timeout(page, 2000)

        p = self.profile

        # Lever has an "Apply" button on the job listing page that opens the form
        apply_btn = page.locator("a:has-text('Apply'), button:has-text('Apply for this job')").first
        if apply_btn.count() and apply_btn.is_visible():
            apply_btn.click()
            try:
                page.wait_for_load_state("networkidle")
            except Exception:
                pass
            self._safe_timeout(page, 1500)

        # -- Name --------------------------------------------------------
        # Lever uses a single full-name field
        self.fill(page, [
            "input[name='name']",
            "input[placeholder='Full name *']",
            "input[placeholder*='name' i]",
            "input[id*='name' i]",
        ], p["name"])

        # -- Contact -----------------------------------------------------
        self.fill(page, [
            "input[name='email']",
            "input[type='email']",
            "input[placeholder*='email' i]",
        ], p["email"])
        self.fill(page, [
            "input[name='phone']",
            "input[type='tel']",
            "input[placeholder*='phone' i]",
        ], p["phone_formatted"])

        # -- Location ----------------------------------------------------
        self.fill(page, [
            "input[name='location']",
            "input[placeholder*='location' i]",
            "input[placeholder*='city' i]",
        ], p["location"])

        # -- Resume upload -----------------------------------------------
        uploaded = self.upload_via_button(page, [
            "label[for='resume-upload']",
            "label:has-text('Resume')",
            "button:has-text('Upload resume')",
            "*[class*='resume'] input[type='file']",
        ], resume_pdf)
        if not uploaded:
            self.upload(page, [
                "input[name='resume']",
                "input[type='file']",
            ], resume_pdf)

        # -- Cover letter (optional) -------------------------------------
        if coverletter_pdf:
            uploaded_cl = self.upload_via_button(page, [
                "label:has-text('Cover letter')",
                "label:has-text('Cover Letter')",
                "button:has-text('Upload cover letter')",
            ], coverletter_pdf)
            if not uploaded_cl:
                inputs = page.locator("input[type='file']").all()
                if len(inputs) > 1:
                    try:
                        inputs[1].set_input_files(coverletter_pdf)
                    except Exception:
                        pass

        # -- LinkedIn / links --------------------------------------------
        self.fill(page, [
            "input[name='urls[LinkedIn]']",
            "input[placeholder*='linkedin' i]",
        ], p["linkedin"])

        # -- Custom questions: work authorization ------------------------
        self._fill_authorization(page, p)

        # -- Submit ------------------------------------------------------
        self._safe_timeout(page, 1000)
        if self.submit(page):
            self._safe_timeout(page, 3000)
            return {"success": True, "status": "submitted", "notes": "Lever form submitted"}

        return {"success": False, "status": "BLOCKED", "notes": "Could not find or click submit button"}

    def _fill_authorization(self, page: Page, p: dict):
        auth_answer = "Yes" if p["work_authorized"] else "No"
        sponsor_answer = "No" if not p["requires_sponsorship"] else "Yes"

        for hint in ["authorized to work", "legally authorized", "work authorization"]:
            self.click_radio_or_button(page, hint, auth_answer)

        for hint in ["sponsorship", "require sponsorship", "will you require"]:
            self.click_radio_or_button(page, hint, sponsor_answer)

        # Lever radio DOM fallback
        try:
            page.evaluate("""
                document.querySelectorAll('input[type="radio"]').forEach(r => {
                    const label = r.closest('label') || document.querySelector(`label[for="${r.id}"]`);
                    const text = (label ? label.textContent : r.value || '').trim().toLowerCase();
                    const card = r.closest('[class*="card"], [class*="question"], .application-question');
                    const qText = card ? card.textContent.toLowerCase() : '';
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
