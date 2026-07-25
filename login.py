"""
login.py - Save browser sessions for Google, LinkedIn, Indeed, and Handshake.

Run once. Browser windows open so you can log in (handles 2FA automatically).
Sessions are saved to sessions/ and reused by auto_apply.py forever.

Usage:
  python login.py all
  python login.py google
  python login.py linkedin
  python login.py indeed
  python login.py handshake
"""

import os
import sys
from playwright.sync_api import sync_playwright, Page
from dotenv import load_dotenv

load_dotenv()

SESSIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

GOOGLE_EMAIL    = os.getenv("GOOGLE_EMAIL",    "unika.bista0@gmail.com")
GOOGLE_PASSWORD = os.getenv("GOOGLE_PASSWORD", "")
LI_EMAIL        = os.getenv("LINKEDIN_EMAIL",  "unika.bista0@gmail.com")
LI_PASS         = os.getenv("LINKEDIN_PASSWORD", "")
IN_EMAIL        = os.getenv("INDEED_EMAIL",    "unika.bista0@gmail.com")
IN_PASS         = os.getenv("INDEED_PASSWORD",  "")
HS_EMAIL        = os.getenv("HANDSHAKE_EMAIL",  "")
HS_PASS         = os.getenv("HANDSHAKE_PASSWORD", "")


def _try_fill(page: Page, selector: str, value: str, timeout_ms: int = 4000):
    """Quick fill attempt — silently skips if field not found."""
    try:
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=timeout_ms)
        loc.clear()
        loc.fill(value)
    except Exception:
        pass


def _try_click(page: Page, selector: str, timeout_ms: int = 4000):
    """Quick click attempt — silently skips if element not found."""
    try:
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=timeout_ms)
        loc.click()
    except Exception:
        pass


def _save_and_close(context, browser, session_file: str, platform: str) -> bool:
    try:
        context.storage_state(path=session_file)
        print(f"  [{platform}] Session saved -> {session_file}")
        browser.close()
        return True
    except Exception as e:
        print(f"  [{platform}] Could not save session: {e}")
        return False


def _run_login(platform: str, url: str, session_file: str,
               autofill_fn, success_url_keywords: list) -> bool:
    """
    Generic login runner:
    1. Open browser at url
    2. Try autofill_fn (silently ignores failures)
    3. If not logged in, ask user to complete it in the browser
    4. Save session when done
    """
    print(f"\n=== {platform} Login ===")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page    = context.new_page()

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"  Could not open {url}: {e}")
            browser.close()
            return False

        # Try auto-fill (silently — doesn't matter if it fails)
        try:
            autofill_fn(page)
            page.wait_for_timeout(3000)
        except Exception:
            pass

        def _is_logged_in():
            try:
                return any(kw in page.url for kw in success_url_keywords)
            except Exception:
                return False

        if _is_logged_in():
            print(f"  Logged in automatically!")
            return _save_and_close(context, browser, session_file, platform)

        # Ask user to complete login
        print(f"  Browser is open. Log in with your credentials.")
        print(f"  (Handle 2FA, captcha, etc. in the browser window)")
        print(f"  When the browser shows your home/dashboard page, come back here.")

        while True:
            try:
                input(f"  Press Enter once you're logged into {platform}... ")
            except EOFError:
                break

            if _is_logged_in():
                break

            # Page might be at a different URL that still counts as logged in
            # Just save whatever session we have
            try:
                current_url = page.url
                print(f"  Current URL: {current_url}")
            except Exception:
                print("  (Browser may have closed)")
                browser.close()
                return False

            confirm = input("  Are you logged in? (y/n): ").strip().lower()
            if confirm == "y":
                break

        return _save_and_close(context, browser, session_file, platform)


# ------------------------------------------------------------------ #
# Google                                                               #
# ------------------------------------------------------------------ #

def login_google() -> bool:
    def autofill(page: Page):
        # Email step
        _try_fill(page, "input[type='email']", GOOGLE_EMAIL)
        page.wait_for_timeout(500)
        _try_click(page, "#identifierNext, button:has-text('Next')")
        page.wait_for_timeout(2500)
        # Password step (Google shows a NEW page — wait for it)
        _try_fill(page, "input[type='password']:not([aria-hidden='true']), "
                         "input[name='Passwd']", GOOGLE_PASSWORD)
        page.wait_for_timeout(500)
        _try_click(page, "#passwordNext, button:has-text('Next')")

    return _run_login(
        platform="Google",
        url="https://accounts.google.com/signin/v2/identifier",
        session_file=os.path.join(SESSIONS_DIR, "workday_google_session.json"),
        autofill_fn=autofill,
        success_url_keywords=["myaccount.google.com", "mail.google.com",
                               "google.com/u/0", "accounts.google.com/b/"],
    )


# ------------------------------------------------------------------ #
# LinkedIn                                                             #
# ------------------------------------------------------------------ #

def login_linkedin() -> bool:
    def autofill(page: Page):
        _try_fill(page, "input#username", LI_EMAIL)
        _try_fill(page, "input#password", LI_PASS)
        _try_click(page, "button[type='submit']")

    return _run_login(
        platform="LinkedIn",
        url="https://www.linkedin.com/login",
        session_file=os.path.join(SESSIONS_DIR, "linkedin_session.json"),
        autofill_fn=autofill,
        success_url_keywords=["linkedin.com/feed", "linkedin.com/in/",
                               "linkedin.com/jobs", "linkedin.com/messaging"],
    )


# ------------------------------------------------------------------ #
# Indeed                                                               #
# ------------------------------------------------------------------ #

def login_indeed() -> bool:
    def autofill(page: Page):
        # Indeed: email then Continue, then password on next page
        _try_fill(page, "input[name='__email'], input[type='email']", IN_EMAIL)
        _try_click(page, "button[type='submit'], button:has-text('Continue')")
        page.wait_for_timeout(2000)
        _try_fill(page, "input[type='password']", IN_PASS)
        _try_click(page, "button[type='submit'], button:has-text('Sign in')")

    return _run_login(
        platform="Indeed",
        url="https://secure.indeed.com/auth?hl=en&co=US",
        session_file=os.path.join(SESSIONS_DIR, "indeed_session.json"),
        autofill_fn=autofill,
        success_url_keywords=["indeed.com/myjobs", "indeed.com/account",
                               "indeed.com/jobs", "indeed.com/resumes",
                               "indeed.com/?", "indeed.com/#"],
    )


# ------------------------------------------------------------------ #
# Handshake                                                            #
# ------------------------------------------------------------------ #

def login_handshake() -> bool:
    def autofill(page: Page):
        if not HS_EMAIL:
            return
        _try_fill(page, "input[type='email'], input[name='email']", HS_EMAIL)
        _try_click(page, "button[type='submit'], button:has-text('Next'), "
                          "button:has-text('Continue')")
        page.wait_for_timeout(2000)
        _try_fill(page, "input[type='password']", HS_PASS)
        _try_click(page, "button[type='submit'], button:has-text('Sign in')")

    print("\n  Tip: In the Handshake browser, click 'Sign in with Google' for easiest login.")

    return _run_login(
        platform="Handshake",
        url="https://app.joinhandshake.com/login",
        session_file=os.path.join(SESSIONS_DIR, "handshake_session.json"),
        autofill_fn=autofill,
        success_url_keywords=["joinhandshake.com/stu", "joinhandshake.com/dashboard",
                               "joinhandshake.com/edu", "joinhandshake.com/users"],
    )


# ------------------------------------------------------------------ #
# Entry point                                                          #
# ------------------------------------------------------------------ #

def main():
    args = sys.argv[1:]
    if not args or "all" in args:
        platforms = ["google", "linkedin", "indeed", "handshake"]
    else:
        platforms = args

    results = {}
    for platform in platforms:
        if platform == "google":
            results["google"]    = login_google()
        elif platform == "linkedin":
            results["linkedin"]  = login_linkedin()
        elif platform == "indeed":
            results["indeed"]    = login_indeed()
        elif platform == "handshake":
            results["handshake"] = login_handshake()
        else:
            print(f"Unknown platform '{platform}'. Options: google, linkedin, indeed, handshake, all")

    print("\n=== Login Summary ===")
    for plat, ok in results.items():
        print(f"  {plat:<12} {'SAVED' if ok else 'FAILED'}")

    saved = [k for k, v in results.items() if v]
    if saved:
        print(f"\nReady to apply on: {', '.join(saved)}")
        print("Run:  python auto_apply.py --limit 20")


if __name__ == "__main__":
    main()
