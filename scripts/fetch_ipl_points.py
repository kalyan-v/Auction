"""Fetch IPL Fantasy Points System using Playwright screenshots.

Opens a visible browser for manual login, then captures
the fantasy points system page with screenshots.
"""

import os
from playwright.sync_api import sync_playwright

SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "screenshots", "ipl_fantasy")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

URL = "https://fantasy.iplt20.com/classic/more/fantasypointsystem"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        page.goto(URL, wait_until="domcontentloaded", timeout=30000)

        print("Please log in to the IPL Fantasy website in the browser.")
        print("Once you can see the Fantasy Point System page, press ENTER here...")
        input()

        # Re-navigate in case login redirected elsewhere
        page.goto(URL, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        # The page uses accordions - only one open at a time.
        # Batting is open by default. Capture each section one at a time.
        sections = [
            "Batting", "Bowling", "Fielding",
            "Economy Rate", "Strike Rate (Except Bowlers)", "Others"
        ]

        all_text = {}
        for section in sections:
            try:
                # Click the section header to expand it
                header = page.locator(f"text='{section}'").first
                if header.is_visible():
                    header.click()
                    page.wait_for_timeout(1000)

                    # Grab full text content of the page panel area
                    text = page.inner_text("body")
                    all_text[section] = text

                    # Take screenshot with this section expanded
                    safe_name = section.lower().replace(' ', '_').replace('(', '').replace(')', '')
                    path = os.path.join(SCREENSHOT_DIR, f"{safe_name}.png")
                    page.screenshot(path=path, full_page=True)
                    print(f"Captured: {section}")
            except Exception as e:
                print(f"Could not capture {section}: {e}")

        # Save all extracted text
        text_path = os.path.join(SCREENSHOT_DIR, "points_text.txt")
        with open(text_path, "w", encoding="utf-8") as f:
            for section, text in all_text.items():
                f.write(f"=== {section} ===\n{text}\n\n")
        print(f"Text saved to {text_path}")

        # Print all text for analysis
        for section, text in all_text.items():
            print(f"\n=== {section} ===")
            print(text)

        browser.close()


if __name__ == "__main__":
    main()
