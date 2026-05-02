from playwright.sync_api import sync_playwright


class JobDescriptionScraper:
    def scrape(self, url: str) -> str:
        """Open the job URL in a real browser and extract the job description text.

        Why Playwright? Job sites use JavaScript to load content. A simple URL fetcher
        would get an empty page. Playwright runs a real browser so it sees the full page.
        """
        with sync_playwright() as p:
            # Why headless=True? Runs the browser invisibly in the background.
            # Set to False if you want to watch the browser open (useful for debugging)
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print(f"  Opening job URL...")
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Why wait_for_selector? Some job sites load the description after the page loads.
            # We wait up to 10 seconds for any main content container to appear.
            try:
                page.wait_for_selector("body", timeout=10000)
            except Exception:
                pass

            # Extract all visible text from the page
            # Why innerText and not innerHTML? innerText gives readable text only,
            # stripping out all HTML tags, scripts, and styling noise.
            text = page.inner_text("body")

            browser.close()

        return self._clean(text)

    def _clean(self, text: str) -> str:
        """Remove excessive blank lines and whitespace from scraped text."""
        lines = text.splitlines()
        cleaned = []
        blank_count = 0
        for line in lines:
            stripped = line.strip()
            if stripped == "":
                blank_count += 1
                # Why limit to 2 blank lines? Keeps sections readable without huge gaps
                if blank_count <= 2:
                    cleaned.append("")
            else:
                blank_count = 0
                cleaned.append(stripped)
        return "\n".join(cleaned).strip()
