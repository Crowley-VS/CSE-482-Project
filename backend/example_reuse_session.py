"""
Example: Using existing Chrome session for Reddit scraping

SETUP:
1. First, open Chrome with debugging enabled in a terminal:
   google-chrome --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_dev_session"

2. Manually log into Reddit in that browser

3. Run this script - it will take over that Chrome session

The scraper will use your already-logged-in session, skipping the login process entirely.
"""

from app.collectors.reddit_selenium_collector import RedditSeleniumCollector
from app.core.logging import get_logger

logger = get_logger(__name__)


def main():
    print("\n" + "="*70)
    print("Reddit Scraper - Reusing Existing Chrome Session")
    print("="*70)
    print("\nMAKE SURE you have Chrome running with debugging enabled:")
    print("  google-chrome --remote-debugging-port=9222 --user-data-dir=\"/tmp/chrome_dev_session\"")
    print("\nAnd that you're already logged into Reddit in that browser.")
    print("="*70 + "\n")

    input("Press Enter when ready to continue...")

    # Create collector that connects to existing Chrome session
    # use_existing_session=True tells it to connect to the running Chrome
    # headless=False is ignored when use_existing_session=True
    collector = RedditSeleniumCollector(
        use_existing_session=True,
        debug_port=9222
    )

    try:
        # The scraper will take over your existing Chrome browser
        # No login needed - it will use your existing session
        print("\n✓ Taking over existing Chrome session...")

        # Check if already authenticated by looking for user menu
        collector._setup_driver()
        collector.driver.get("https://www.reddit.com")

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        import time

        time.sleep(2)

        try:
            WebDriverWait(collector.driver, 5).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[aria-label='User Menu']"))
            )
            collector.is_authenticated = True
            print("✓ Already logged in! Ready to scrape.")
        except:
            print(
                "⚠️  Not logged in. Please log in manually in the browser, then press Enter.")
            input()
            collector.is_authenticated = True

        # Now scrape from subreddits
        print("\nCollecting posts from r/Economics...")
        posts = collector.collect_from_subreddit("Economics", limit=5)

        print(f"\n✓ Collected {len(posts)} posts:")
        for i, post in enumerate(posts[:3], 1):
            print(f"\n{i}. {post['title'][:80]}...")
            print(
                f"   Author: {post['author']} | Score: {post['score']} | Comments: {post['num_comments']}")

    finally:
        # Close the connection (this won't close the Chrome window itself)
        collector.close()
        print("\n✓ Done! The Chrome window will stay open.")


if __name__ == "__main__":
    main()
