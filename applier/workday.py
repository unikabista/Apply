import os
import re
from playwright.sync_api import Page, sync_playwright
from .base import BaseApplier
from dotenv import load_dotenv

load_dotenv()

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sessions")

GOOGLE_EMAIL    = os.getenv("GOOGLE_EMAIL",    "unika.bista0@gmail.com")
GOOGLE_PASSWORD = os.getenv("GOOGLE_PASSWORD", "")
WORKDAY_PASSWORD = os.getenv("WORKDAY_PASSWORD", "")


class WorkdayApplier(BaseApplier):
    """
    Workday ATS applier.

    Login strategy (tried in order):
      1. Sign in with Google (SSO popup) — preferred, no email verification needed
      2. Sign in with existing Workday account (email + WORKDAY_PASSWORD)
      3. Create new Workday account (email + WORKDAY_PASSWORD)
      4. Guest apply if the instance allows it
    """

    def _session_file(self):
        os.makedirs(SESSIONS_DIR, exist_ok=True)
        return os.path.join(SESSIONS_DIR, "workday_google_session.json")

    def apply(self, url: str, resume_pdf: str, coverletter_pdf: str = None) -> dict:
        if not os.path.exists(resume_pdf):
            return {"success": False, "status": "ERROR", "notes": f"Resume not found: {resume_pdf}"}

        session_file = self._session_file()
        has_session  = os.path.exists(session_file)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # visible — user can help if CAPTCHA hits
            context = browser.new_context(
                storage_state=session_file if has_session else None
            ) if has_session else browser.new_context()
            page = context.new_page()
            try:
                result = self._apply(page, url, resume_pdf, coverletter_pdf)
                # Persist any new Google session cookies
                try:
                    context.storage_state(path=session_file)
                except Exception:
                    pass
            except Exception as e:
                result = {"success": False, "status": "ERROR", "notes": str(e)}
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
        return result

    # ------------------------------------------------------------------ #
    # Main flow                                                            #
    # ------------------------------------------------------------------ #

    def _apply(self, page: Page, url: str, resume_pdf: str, coverletter_pdf: str) -> dict:
        page.goto(url, wait_until="networkidle", timeout=30000)
        self._safe_timeout(page, 2000)

        p = self.profile

        if not self._click_apply(page):
            return {"success": False, "status": "BLOCKED", "notes": "Could not find Apply button"}
        self._safe_timeout(page, 3000)

        # Handle login / account creation
        if self._on_auth_page(page):
            auth_ok = (
                self._try_google_sso(page)
                or self._try_direct_login(page)
                or self._try_create_account(page)
                or self._try_guest_apply(page)
            )
            if not auth_ok:
                return {"success": False, "status": "BLOCKED",
                        "notes": "Workday: all login strategies failed — check credentials in .env"}
            self._safe_timeout(page, 3000)

        # Fill personal info on first step
        self._fill_personal(page, p)

        # Upload resume
        self._upload_resume(page, resume_pdf)
        if coverletter_pdf:
            self._upload_coverletter(page, coverletter_pdf)

        # Walk multi-step wizard
        return self._walk_wizard(page, p)

    # ------------------------------------------------------------------ #
    # Login strategies                                                     #
    # ------------------------------------------------------------------ #

    def _on_auth_page(self, page: Page) -> bool:
        url = page.url.lower()
        if any(k in url for k in ("login", "signin", "signon", "auth", "account/create")):
            return True
        heading = page.locator("h1, h2, h3").filter(
            has_text=re.compile(r"sign in|log in|create account|existing account|welcome back", re.I)
        ).first
        return bool(heading.count() and heading.is_visible())

    def _try_google_sso(self, page: Page) -> bool:
        """Click 'Sign in with Google', handle the OAuth popup, return True on success."""
        btn = page.locator(
            "button:has-text('Sign in with Google'), "
            "a:has-text('Sign in with Google'), "
            "button:has-text('Continue with Google'), "
            "a:has-text('Continue with Google'), "
            "[data-automation-id*='google' i]"
        ).first
        if not btn.count() or not btn.is_visible():
            return False

        print("  [workday] Trying Google SSO...")
        try:
            with page.expect_popup(timeout=12000) as popup_info:
                btn.click()
            popup = popup_info.value
            popup.wait_for_load_state("networkidle", timeout=15000)
            self._safe_timeout(page, 1000)

            if "accounts.google.com" in popup.url:
                self._handle_google_popup(popup)

            # Wait for popup to close (OAuth done) — up to 60s for 2FA/manual steps
            print("  [workday] Waiting for Google auth to complete (handle 2FA if needed)...")
            try:
                popup.wait_for_event("close", timeout=60000)
            except Exception:
                pass

            self._safe_timeout(page, 3000)
            return not self._on_auth_page(page)
        except Exception as e:
            print(f"  [workday] Google SSO failed: {e}")
            return False

    def _handle_google_popup(self, popup: Page):
        """Auto-fill Google credentials in the OAuth popup."""
        try:
            # If account chooser shows, click our account
            account = popup.locator(
                f"[data-email='{GOOGLE_EMAIL}'], "
                f"div[aria-label*='{GOOGLE_EMAIL}']"
            ).first
            if account.count() and account.is_visible():
                account.click()
                popup.wait_for_timeout(2000)
                return
        except Exception:
            pass

        # Email step
        try:
            email_inp = popup.locator("input[type='email']").first
            if email_inp.count() and email_inp.is_visible():
                email_inp.fill(GOOGLE_EMAIL)
                popup.locator("button:has-text('Next'), #identifierNext").first.click()
                popup.wait_for_timeout(2500)
        except Exception:
            pass

        # Password step
        if not GOOGLE_PASSWORD:
            print("  [workday] GOOGLE_PASSWORD not set — please complete login manually in the popup.")
            return
        try:
            pass_inp = popup.locator("input[type='password']").first
            if pass_inp.count() and pass_inp.is_visible():
                pass_inp.fill(GOOGLE_PASSWORD)
                popup.locator("button:has-text('Next'), #passwordNext").first.click()
                popup.wait_for_timeout(3000)
        except Exception:
            pass

        # Allow / Continue button (Google consent screen)
        try:
            allow = popup.locator("button:has-text('Allow'), button:has-text('Continue')").first
            if allow.count() and allow.is_visible():
                allow.click()
                popup.wait_for_timeout(2000)
        except Exception:
            pass

    def _try_direct_login(self, page: Page) -> bool:
        """Sign in with an existing Workday account using email + WORKDAY_PASSWORD."""
        if not WORKDAY_PASSWORD:
            return False

        email_inp = page.locator(
            "input[type='email'], input[data-automation-id='email'], "
            "input[placeholder*='Email' i], input[name*='email' i]"
        ).first
        if not email_inp.count() or not email_inp.is_visible():
            return False

        # Check we're on a sign-in form (not create-account form)
        heading = page.locator("h1, h2").filter(
            has_text=re.compile(r"sign in|log in|existing|welcome back", re.I)
        ).first
        if not heading.count():
            return False

        print("  [workday] Trying direct email login...")
        try:
            email_inp.fill(GOOGLE_EMAIL)
            pass_inp = page.locator("input[type='password']").first
            if pass_inp.count() and pass_inp.is_visible():
                pass_inp.fill(WORKDAY_PASSWORD)
            self.click(page, [
                "button[type='submit']",
                "button:has-text('Sign In')",
                "button:has-text('Log In')",
            ])
            self._safe_timeout(page, 3000)
            return not self._on_auth_page(page)
        except Exception as e:
            print(f"  [workday] Direct login failed: {e}")
            return False

    def _try_create_account(self, page: Page) -> bool:
        """Create a new Workday account with Gmail + WORKDAY_PASSWORD."""
        if not WORKDAY_PASSWORD:
            print("  [workday] WORKDAY_PASSWORD not set — cannot create account automatically.")
            return False

        print("  [workday] Trying to create Workday account...")
        # Click "Create Account" link if present
        create_link = page.locator(
            "a:has-text('Create Account'), button:has-text('Create Account'), "
            "a:has-text('Register'), a:has-text('Don\\'t have an account')"
        ).first
        if create_link.count() and create_link.is_visible():
            create_link.click()
            self._safe_timeout(page, 2500)

        try:
            # Fill creation form
            self.fill(page, [
                "input[data-automation-id='email']",
                "input[type='email']",
                "input[placeholder*='Email' i]",
            ], GOOGLE_EMAIL)

            self.fill(page, [
                "input[data-automation-id='password']",
                "input[type='password'][placeholder*='Password' i]",
                "input[id*='password' i]",
            ], WORKDAY_PASSWORD)

            # Confirm password field
            confirm = page.locator(
                "input[data-automation-id='confirmPassword'], "
                "input[placeholder*='Confirm' i], "
                "input[id*='confirm' i]"
            ).first
            if confirm.count() and confirm.is_visible():
                confirm.fill(WORKDAY_PASSWORD)

            # Accept terms if checkbox present
            terms = page.locator("input[type='checkbox']").first
            if terms.count() and terms.is_visible() and not terms.is_checked():
                terms.click()

            self.click(page, [
                "button[type='submit']",
                "button:has-text('Create Account')",
                "button:has-text('Register')",
                "button:has-text('Continue')",
            ])
            self._safe_timeout(page, 3000)

            # Check for email verification prompt
            if page.locator("text=/verify|verification|check your email/i").count():
                print("  [workday] Email verification required — check unika.bista0@gmail.com and click the link, then press Enter.")
                input("  Press Enter once verified...")
                self._safe_timeout(page, 2000)

            return not self._on_auth_page(page)
        except Exception as e:
            print(f"  [workday] Account creation failed: {e}")
            return False

    def _try_guest_apply(self, page: Page) -> bool:
        """Some Workday instances allow applying without an account."""
        guest = page.locator(
            "a:has-text('Continue as Guest'), button:has-text('Continue as Guest'), "
            "a:has-text('Apply without account'), a:has-text('Skip sign in')"
        ).first
        if guest.count() and guest.is_visible():
            print("  [workday] Trying guest apply...")
            guest.click()
            self._safe_timeout(page, 2000)
            return True
        return False

    # ------------------------------------------------------------------ #
    # Field filling                                                        #
    # ------------------------------------------------------------------ #

    def _click_apply(self, page: Page) -> bool:
        return self.click(page, [
            "a[data-automation-id='applyNowButton']",
            "button[data-automation-id='applyNowButton']",
            "a:has-text('Apply Now')",
            "button:has-text('Apply Now')",
            "a:has-text('Apply for Job')",
            "button:has-text('Apply for Job')",
            "a:has-text('Apply')",
            "button:has-text('Apply')",
        ])

    def _fill_wd(self, page: Page, automation_id: str, value: str) -> bool:
        if not value:
            return False
        return self.fill(page, [
            f"input[data-automation-id='{automation_id}']",
            f"[data-automation-id='{automation_id}'] input",
            f"textarea[data-automation-id='{automation_id}']",
        ], value)

    def _fill_personal(self, page: Page, p: dict):
        self._fill_wd(page, "legalNameSection_firstName", p["first_name"])
        self._fill_wd(page, "legalNameSection_lastName",  p["last_name"])
        self._fill_wd(page, "firstName",  p["first_name"])
        self._fill_wd(page, "lastName",   p["last_name"])
        self._fill_wd(page, "email",      p["email"])
        self._fill_wd(page, "phone-number",  p["phone_formatted"])
        self._fill_wd(page, "phoneNumber",   p["phone_formatted"])
        self._fill_wd(page, "addressSection_city", p["city"])
        # Generic fallbacks
        self.fill(page, ["input[autocomplete='given-name']",  "input[placeholder*='First' i]"], p["first_name"])
        self.fill(page, ["input[autocomplete='family-name']", "input[placeholder*='Last' i]"],  p["last_name"])
        self.fill(page, ["input[type='tel']", "input[autocomplete='tel']"], p["phone_formatted"])

    def _upload_resume(self, page: Page, resume_pdf: str) -> bool:
        uploaded = self.upload_via_button(page, [
            "[data-automation-id='file-upload-drop-zone']",
            "button[data-automation-id='file-upload-drop-zone']",
            "button:has-text('Attach')",
            "button:has-text('Upload My Resume')",
            "button:has-text('Upload Resume')",
            "button:has-text('Upload')",
            "label:has-text('Resume')",
            "label:has-text('CV')",
        ], resume_pdf)
        if not uploaded:
            uploaded = self.upload(page, ["input[type='file']"], resume_pdf)
        return uploaded

    def _upload_coverletter(self, page: Page, coverletter_pdf: str):
        self.upload_via_button(page, [
            "button:has-text('Cover Letter')",
            "label:has-text('Cover Letter')",
        ], coverletter_pdf)

    def _fill_step(self, page: Page, p: dict):
        self.fill(page, [
            "input[data-automation-id='linkedIn']",
            "input[placeholder*='linkedin' i]",
        ], p["linkedin"])
        self.fill(page, [
            "input[data-automation-id='howDidYouHearAboutUs']",
            "input[placeholder*='hear about' i]",
        ], p.get("how_heard", "Job board"))
        self.answer_yes_no(page, ["authorized to work", "legally authorized",
                                   "authorized to work in"], answer_yes=True)
        self.answer_yes_no(page, ["sponsorship", "require sponsorship",
                                   "will you require"], answer_yes=False)
        self.answer_yes_no(page, ["relocate", "willing to relocate"], answer_yes=True)
        self.select_option(page, [
            "select[data-automation-id='Gender']",
            "select[data-automation-id='gender']",
        ], p["gender"])

    # ------------------------------------------------------------------ #
    # Wizard walker                                                        #
    # ------------------------------------------------------------------ #

    def _walk_wizard(self, page: Page, p: dict) -> dict:
        for step in range(15):
            self._safe_timeout(page, 1500)
            self._fill_step(page, p)

            # Submit present?
            submit = page.locator(
                "button[data-automation-id='bottom-navigation-next-button']:has-text('Submit'), "
                "button:has-text('Submit Application'), "
                "button[data-automation-id='submitButton']"
            ).first
            if submit.count() and submit.is_visible():
                submit.click()
                self._safe_timeout(page, 4000)
                return self._verify(page)

            # Next / Save and Continue
            nexted = self.click(page, [
                "button[data-automation-id='bottom-navigation-next-button']",
                "button:has-text('Next')",
                "button:has-text('Save and Continue')",
                "button:has-text('Continue')",
                "button[data-automation-id='wd-CommandButton_uwft']",
            ])
            if not nexted:
                if self.submit(page):
                    self._safe_timeout(page, 4000)
                    return self._verify(page)
                return {"success": False, "status": "BLOCKED",
                        "notes": f"Workday wizard stuck at step {step + 1}"}

        return {"success": False, "status": "BLOCKED", "notes": "Exceeded max wizard steps"}

    def _verify(self, page: Page) -> dict:
        try:
            page.wait_for_selector(
                "text=/thank you|application submitted|successfully submitted|application received/i",
                timeout=8000,
            )
            return {"success": True, "status": "submitted", "notes": "Workday submission confirmed"}
        except Exception:
            pass
        return {"success": False, "status": "BLOCKED",
                "notes": "Workday: submitted but no confirmation — verify manually"}
