"""Reddit data collector using Selenium for web scraping."""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import time
import re
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedditSeleniumCollector:
    """Collect posts from Reddit using Selenium web scraping."""

    def __init__(self, headless: bool = None, use_existing_session: bool = None, debug_port: int = None):
        """
        Initialize Selenium WebDriver for Reddit.

        Args:
            headless: Run browser in headless mode (no GUI). Defaults to settings.SELENIUM_HEADLESS
            use_existing_session: Connect to existing Chrome instance instead of creating new one. 
                                 Defaults to settings.USE_EXISTING_CHROME_SESSION
            debug_port: Port for Chrome remote debugging. Defaults to settings.CHROME_DEBUG_PORT
        """
        self.headless = headless if headless is not None else settings.SELENIUM_HEADLESS
        self.use_existing_session = use_existing_session if use_existing_session is not None else settings.USE_EXISTING_CHROME_SESSION
        self.debug_port = debug_port if debug_port is not None else settings.CHROME_DEBUG_PORT
        self.driver: Optional[webdriver.Chrome] = None
        self.is_authenticated = False
        logger.info("Reddit Selenium collector initialized")

    def _setup_driver(self):
        """Setup Chrome WebDriver with appropriate options."""
        chrome_options = Options()

        if self.use_existing_session:
            # Connect to existing Chrome instance
            chrome_options.add_experimental_option(
                "debuggerAddress", f"localhost:{self.debug_port}")
            logger.info(
                f"Connecting to existing Chrome instance on port {self.debug_port}")
        else:
            # Start new Chrome instance
            if self.headless:
                chrome_options.add_argument("--headless=new")

            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-setuid-sandbox")
            chrome_options.add_argument("--remote-debugging-port=9222")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(
                "--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option(
                'useAutomationExtension', False)
            chrome_options.add_argument(
                "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

        # Selenium Manager will automatically download the right driver
        self.driver = webdriver.Chrome(options=chrome_options)
        logger.info("Chrome WebDriver initialized")

    def wait_for_manual_intervention(self, timeout: int = 300):
        """
        Wait for manual intervention (e.g., humanity check, captcha).
        Ends when either user menu appears OR login form becomes available.

        Args:
            timeout: Maximum time to wait in seconds (default 5 minutes)
        """
        print("\n" + "="*60)
        print("⚠️  MANUAL INTERVENTION REQUIRED ⚠️")
        print("="*60)
        print("Please complete any humanity checks, captchas, or verification")
        print("in the browser window that just opened.")
        print(f"Waiting up to {timeout} seconds ({timeout//60} minutes)...")
        print("The script will automatically continue once the login form appears.")
        print("="*60 + "\n")

        logger.warning("="*60)
        logger.warning("MANUAL INTERVENTION REQUIRED")
        logger.warning(
            "Please complete any humanity checks, captchas, or verification in the browser window.")
        logger.warning(
            "The script will automatically continue once done.")
        logger.warning("Waiting up to {} seconds...".format(timeout))
        logger.warning("="*60)

        # Check every 2 seconds if user menu is present OR login form is visible
        start_time = time.time()
        while (time.time() - start_time) < timeout:

            try:
                # Check if user menu appeared (already logged in)
                self.driver.find_element(
                    By.CSS_SELECTOR, "[aria-label='User Menu']")
                logger.info(
                    "✓ Manual intervention completed - already logged in!")
                print("\n✓ Already logged in! Continuing...\n")
                return True
            except Exception:
                pass

            try:
                # Check if login form is available (humanity check completed)
                # Verify both username and password fields are present
                # New Reddit uses faceplate-text-input Web Components with Shadow DOM
                # We target the actual <input> element inside the custom component
                username_field = self.driver.find_element(
                    By.CSS_SELECTOR, "faceplate-text-input#login-username input")
                password_field = self.driver.find_element(
                    By.CSS_SELECTOR, "faceplate-text-input#login-password input")
                logger.info(username_field)
                logger.info(username_field.is_displayed())
                # Ensure fields are actually visible and interactable
                if username_field.is_displayed() and password_field.is_displayed():
                    logger.info(
                        "✓ Manual intervention completed - login form available!")
                    print("\n✓ Login form ready! Continuing...\n")
                    return True
            except Exception:
                pass

            time.sleep(2)  # Check every 2 seconds

        logger.warning("✗ Timeout waiting for manual intervention")
        print("\n✗ Timeout - continuing anyway...\n")
        return False

    def login(self) -> bool:
        """
        Authenticate with Reddit using username and password.

        Returns:
            True if login successful, False otherwise
        """
        if not settings.REDDIT_USERNAME or not settings.REDDIT_PASSWORD:
            logger.warning("Reddit credentials not found in settings")
            return False

        try:
            if not self.driver:
                self._setup_driver()

            logger.info("Attempting to login to Reddit")
            self.driver.get("https://www.reddit.com/login/")

            # Wait a bit for page to load
            time.sleep(2)

            # Check if "Prove your humanity" challenge appeared immediately
            humanity_check_on_load = False
            try:
                page_text = self.driver.page_source
                if "Prove your humanity" in page_text or "We're committed to safety and security" in page_text:
                    logger.warning(
                        "Humanity verification challenge detected on page load")
                    humanity_check_on_load = True
                    # Wait for manual intervention
                    if not self.wait_for_manual_intervention():
                        logger.error(
                            "Login failed - humanity check not completed")
                        return False
                    # After completing humanity check, navigate to login page again
                    logger.info(
                        "Navigating to login page after humanity check")
                    self.driver.get("https://www.reddit.com/login/")
                    time.sleep(2)
            except:
                pass

            # Wait for login form
            wait = WebDriverWait(self.driver, 10)

            # Find and fill username
            try:
                # New Reddit uses faceplate-text-input Web Components
                username_field = wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "faceplate-text-input#login-username input")
                    )
                )
                username_field.clear()
                username_field.send_keys(settings.REDDIT_USERNAME)
            except Exception as e:
                logger.error(f"Could not find username field: {e}")
                return False

            # Find and fill password
            try:
                password_field = self.driver.find_element(
                    By.CSS_SELECTOR, "faceplate-text-input#login-password input"
                )
                password_field.clear()
                password_field.send_keys(settings.REDDIT_PASSWORD)
            except Exception as e:
                logger.error(f"Could not find password field: {e}")
                return False

            # Submit login form
            try:
                login_button = self.driver.find_element(
                    By.XPATH, "//button[contains(text(), 'Log In')]"
                )
                login_button.click()
                logger.info("Login credentials submitted")
            except Exception as e:
                logger.error(f"Could not click login button: {e}")
                return False

            # Wait a bit for initial response
            time.sleep(3)

            # Check if login was successful by looking for user menu
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "[aria-label='User Menu']"))
                )
                self.is_authenticated = True
                logger.info("Successfully logged into Reddit")
                return True
            except:
                # Check one more time if humanity check appeared after login
                try:
                    page_text = self.driver.page_source
                    if "Prove your humanity" in page_text or "We're committed to safety and security" in page_text:
                        logger.warning(
                            "Humanity verification required after login attempt")
                        if self.wait_for_manual_intervention():
                            self.is_authenticated = True
                            logger.info(
                                "Successfully logged into Reddit after manual intervention")
                            return True
                except:
                    pass

                logger.error("Login may have failed - user menu not found")
                return False

        except Exception as e:
            logger.error(f"Error during Reddit login: {e}")
            return False

    def collect_from_subreddit(
        self,
        subreddit_name: str,
        limit: int = None,
        sort_by: str = "hot"
    ) -> List[Dict[str, Any]]:
        """
        Collect posts from a specific subreddit.

        Args:
            subreddit_name: Name of the subreddit (e.g., 'Economics')
            limit: Maximum number of posts to fetch
            sort_by: Sort order ('hot', 'new', 'top', 'rising')

        Returns:
            List of post dictionaries with standardized fields
        """
        if limit is None:
            limit = settings.MAX_POSTS_PER_SUBREDDIT

        try:
            # Only setup driver and login if not already done
            # This allows reusing the same session across multiple subreddits
            if not self.driver:
                self._setup_driver()

            if not self.is_authenticated:
                login_success = self.login()
                if not login_success:
                    logger.warning("Continuing without authentication")

            url = f"https://www.reddit.com/r/{subreddit_name}/{sort_by}/"
            logger.info(f"Scraping r/{subreddit_name} - {sort_by}")
            self.driver.get(url)

            # Wait for posts to load
            time.sleep(3)

            # Scroll to load more posts
            posts_loaded = 0
            scroll_attempts = 0
            max_scrolls = limit // 10 + 5  # Rough estimate

            while posts_loaded < limit and scroll_attempts < max_scrolls:
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                scroll_attempts += 1

                # Count loaded posts
                post_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "shreddit-post"
                )
                posts_loaded = len(post_elements)

            logger.info(f"Found {posts_loaded} posts to scrape")

            # Extract post data
            posts = []
            post_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "shreddit-post"
            )[:limit]

            for post_element in post_elements:
                try:
                    post_data = self._extract_post_data(
                        post_element, subreddit_name)
                    if post_data:
                        posts.append(post_data)
                except Exception as e:
                    logger.warning(f"Error extracting post data: {e}")
                    continue

            logger.info(
                f"Successfully scraped {len(posts)} posts from r/{subreddit_name}")
            return posts

        except Exception as e:
            logger.error(f"Error scraping subreddit r/{subreddit_name}: {e}")
            return []

    def _extract_post_data(
        self,
        post_element,
        subreddit_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Extract data from a post element.

        Args:
            post_element: Selenium WebElement for the post
            subreddit_name: Name of the subreddit

        Returns:
            Dictionary with post data or None if extraction fails
        """
        try:
            # Get post ID
            post_id = post_element.get_attribute("id")

            # Get title
            title = post_element.get_attribute("post-title") or ""

            # Get author
            author = post_element.get_attribute("author") or "unknown"

            # Get score (upvotes)
            score_text = post_element.get_attribute("score") or "0"
            score = self._parse_score(score_text)

            # Get comment count
            comment_text = post_element.get_attribute("comment-count") or "0"
            num_comments = int(comment_text) if comment_text.isdigit() else 0

            # Get permalink
            permalink = post_element.get_attribute("content-href") or ""
            if permalink and not permalink.startswith("http"):
                permalink = f"https://www.reddit.com{permalink}"

            # Get timestamp
            created_timestamp = post_element.get_attribute("created-timestamp")
            if created_timestamp:
                try:
                    # Try parsing as millisecond timestamp
                    created_utc = datetime.fromtimestamp(
                        int(created_timestamp) / 1000, tz=timezone.utc
                    )
                except (ValueError, TypeError):
                    # If that fails, try parsing as ISO format string
                    try:
                        created_utc = datetime.fromisoformat(
                            created_timestamp.replace('+0000', '+00:00')
                        )
                    except:
                        created_utc = datetime.now(timezone.utc)
            else:
                created_utc = datetime.now(timezone.utc)

            # Try to get post body/selftext
            try:
                body_element = post_element.find_element(
                    By.CSS_SELECTOR, "[slot='text-body']"
                )
                selftext = body_element.text
            except:
                selftext = ""

            return {
                "post_id": post_id or f"selenium_{int(time.time() * 1000)}",
                "title": title,
                "text": selftext or title,  # Use selftext, fall back to title if empty
                "author": author,
                "score": score,
                "num_comments": num_comments,
                "created_at": created_utc,
                "url": permalink,
                "subreddit": subreddit_name,
                "source": "reddit_selenium",
                "collected_at": datetime.now(timezone.utc)
            }

        except Exception as e:
            logger.warning(f"Error extracting post data: {e}")
            return None

    def _parse_score(self, score_text: str) -> int:
        """Parse score text like '12.3k' to integer."""
        try:
            score_text = score_text.lower().strip()
            if 'k' in score_text:
                return int(float(score_text.replace('k', '')) * 1000)
            elif 'm' in score_text:
                return int(float(score_text.replace('m', '')) * 1000000)
            else:
                return int(float(score_text))
        except:
            return 0

    def collect_from_multiple_subreddits(
        self,
        subreddit_names: List[str] = None,
        limit_per_subreddit: int = None
    ) -> List[Dict[str, Any]]:
        """
        Collect posts from multiple subreddits using the same browser session.

        Args:
            subreddit_names: List of subreddit names (uses config if None)
            limit_per_subreddit: Max posts per subreddit

        Returns:
            Combined list of posts from all subreddits
        """
        if subreddit_names is None:
            subreddit_names = settings.SUBREDDITS

        # Initialize driver and login once if not already done
        if not self.driver:
            self._setup_driver()

        if not self.is_authenticated:
            login_success = self.login()
            if not login_success:
                logger.warning(
                    "Continuing without authentication - may have limited results")

        all_posts = []

        for subreddit_name in subreddit_names:
            logger.info(
                f"Collecting from r/{subreddit_name} (session maintained)")
            posts = self.collect_from_subreddit(
                subreddit_name,
                limit=limit_per_subreddit
            )
            all_posts.extend(posts)
            time.sleep(2)  # Be polite between requests

        logger.info(
            f"Collected {len(all_posts)} total posts from {len(subreddit_names)} subreddits")
        return all_posts

    def close(self):
        """Close the WebDriver and cleanup."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.is_authenticated = False
            logger.info("WebDriver closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
