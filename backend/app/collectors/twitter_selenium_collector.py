"""Twitter/X data collector using Selenium for web scraping."""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import time
import re
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TwitterSeleniumCollector:
    """Collect tweets from Twitter/X using Selenium web scraping."""

    def __init__(self, headless: bool = True):
        """
        Initialize Selenium WebDriver for Twitter/X.

        Args:
            headless: Run browser in headless mode (no GUI)
        """
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None
        self.is_authenticated = False
        logger.info("Twitter Selenium collector initialized")

    def _setup_driver(self):
        """Setup Chrome WebDriver with appropriate options."""
        chrome_options = Options()

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
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

        # Selenium Manager will automatically download the right driver
        self.driver = webdriver.Chrome(options=chrome_options)
        logger.info("Chrome WebDriver initialized")

    def login(self) -> bool:
        """
        Authenticate with Twitter/X using username and password.

        Returns:
            True if login successful, False otherwise
        """
        if not settings.TWITTER_USERNAME or not settings.TWITTER_PASSWORD:
            logger.warning("Twitter credentials not found in settings")
            return False

        try:
            if not self.driver:
                self._setup_driver()

            logger.info("Attempting to login to Twitter/X")
            self.driver.get("https://twitter.com/i/flow/login")

            wait = WebDriverWait(self.driver, 15)

            # Wait for and fill username/email
            username_input = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[autocomplete='username']")
                )
            )
            username_input.send_keys(settings.TWITTER_USERNAME)
            username_input.send_keys(Keys.RETURN)

            time.sleep(2)

            # Sometimes Twitter asks for phone/email verification
            # Try to detect if we need additional verification step
            try:
                # Check if there's an additional verification input
                verify_input = self.driver.find_element(
                    By.CSS_SELECTOR, "input[data-testid='ocfEnterTextTextInput']"
                )
                # If username is email, try phone number or vice versa
                logger.warning(
                    "Additional verification step detected - you may need to handle this manually")
                # For now, we'll skip or you can add logic to handle phone/email
            except:
                pass

            # Wait for and fill password
            password_input = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "input[name='password']")
                )
            )
            password_input.send_keys(settings.TWITTER_PASSWORD)
            password_input.send_keys(Keys.RETURN)

            # Wait for login to complete
            time.sleep(5)

            # Check if login was successful by looking for home timeline
            try:
                wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "[data-testid='primaryColumn']")
                    )
                )
                self.is_authenticated = True
                logger.info("Successfully logged into Twitter/X")
                return True
            except:
                logger.error("Login may have failed - home timeline not found")
                return False

        except Exception as e:
            logger.error(f"Error during Twitter login: {e}")
            return False

    def collect_by_search(
        self,
        query: str,
        limit: int = None,
        filter_type: str = "Latest"
    ) -> List[Dict[str, Any]]:
        """
        Collect tweets by search query.

        Args:
            query: Search query string
            limit: Maximum number of tweets to fetch
            filter_type: 'Top' or 'Latest'

        Returns:
            List of tweet dictionaries with standardized fields
        """
        if limit is None:
            limit = settings.MAX_TWEETS_PER_QUERY

        try:
            if not self.driver:
                self._setup_driver()

            if not self.is_authenticated:
                login_success = self.login()
                if not login_success:
                    logger.warning(
                        "Continuing without authentication - may have limited results")

            # Navigate to search
            search_url = f"https://twitter.com/search?q={query}&src=typed_query"
            if filter_type == "Latest":
                search_url += "&f=live"

            logger.info(f"Searching Twitter for: {query}")
            self.driver.get(search_url)

            # Wait for tweets to load
            time.sleep(3)

            tweets = []
            seen_tweet_ids = set()
            scroll_attempts = 0
            max_scrolls = 50

            while len(tweets) < limit and scroll_attempts < max_scrolls:
                # Find all tweet articles
                tweet_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "article[data-testid='tweet']"
                )

                # Extract data from new tweets
                for tweet_element in tweet_elements:
                    if len(tweets) >= limit:
                        break

                    try:
                        tweet_data = self._extract_tweet_data(
                            tweet_element, query)
                        if tweet_data and tweet_data['id'] not in seen_tweet_ids:
                            tweets.append(tweet_data)
                            seen_tweet_ids.add(tweet_data['id'])
                    except Exception as e:
                        logger.warning(f"Error extracting tweet: {e}")
                        continue

                # Scroll to load more
                self.driver.execute_script(
                    "window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                scroll_attempts += 1

            logger.info(
                f"Successfully scraped {len(tweets)} tweets for query: {query}")
            return tweets

        except Exception as e:
            logger.error(f"Error scraping Twitter search '{query}': {e}")
            return []

    def collect_by_keywords(
        self,
        keywords: List[str] = None,
        max_results: int = None
    ) -> List[Dict[str, Any]]:
        """
        Collect tweets containing economic keywords.

        Args:
            keywords: List of keywords to search for (uses config if None)
            max_results: Maximum tweets to collect total

        Returns:
            List of tweet dictionaries with standardized fields
        """
        if keywords is None:
            keywords = settings.ECONOMIC_KEYWORDS
        if max_results is None:
            max_results = settings.MAX_TWEETS_PER_QUERY

        all_tweets = []
        tweets_per_keyword = max(max_results // len(keywords), 10)

        for keyword in keywords:
            logger.info(f"Collecting tweets for keyword: {keyword}")
            tweets = self.collect_by_search(
                query=keyword,
                limit=tweets_per_keyword,
                filter_type="Latest"
            )
            all_tweets.extend(tweets)
            time.sleep(3)  # Be polite between searches

            if len(all_tweets) >= max_results:
                break

        # Remove duplicates and limit
        seen_ids = set()
        unique_tweets = []
        for tweet in all_tweets:
            if tweet['id'] not in seen_ids:
                unique_tweets.append(tweet)
                seen_ids.add(tweet['id'])

        logger.info(
            f"Collected {len(unique_tweets)} unique tweets from {len(keywords)} keywords")
        return unique_tweets[:max_results]

    def _extract_tweet_data(
        self,
        tweet_element,
        search_query: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Extract data from a tweet element.

        Args:
            tweet_element: Selenium WebElement for the tweet
            search_query: The search query used

        Returns:
            Dictionary with tweet data or None if extraction fails
        """
        try:
            # Get tweet link to extract ID and timestamp
            link_element = tweet_element.find_element(
                By.CSS_SELECTOR, "a[href*='/status/']"
            )
            tweet_url = link_element.get_attribute("href")

            # Extract tweet ID from URL
            tweet_id_match = re.search(r'/status/(\d+)', tweet_url)
            tweet_id = tweet_id_match.group(
                1) if tweet_id_match else f"selenium_{int(time.time() * 1000)}"

            # Get author username
            try:
                author_element = tweet_element.find_element(
                    By.CSS_SELECTOR, "[data-testid='User-Name'] a"
                )
                author = author_element.get_attribute("href").split('/')[-1]
            except:
                author = "unknown"

            # Get tweet text
            try:
                text_element = tweet_element.find_element(
                    By.CSS_SELECTOR, "[data-testid='tweetText']"
                )
                text = text_element.text
            except:
                text = ""

            # Get timestamp
            try:
                time_element = tweet_element.find_element(
                    By.CSS_SELECTOR, "time")
                datetime_str = time_element.get_attribute("datetime")
                created_at = datetime.fromisoformat(
                    datetime_str.replace('Z', '+00:00'))
            except:
                created_at = datetime.now(timezone.utc)

            # Get engagement metrics (likes, retweets, replies)
            metrics = {
                'replies': 0,
                'retweets': 0,
                'likes': 0
            }

            try:
                # Try to get reply count
                reply_element = tweet_element.find_element(
                    By.CSS_SELECTOR, "[data-testid='reply']"
                )
                reply_text = reply_element.get_attribute("aria-label") or ""
                metrics['replies'] = self._parse_count_from_aria(reply_text)
            except:
                pass

            try:
                # Try to get retweet count
                retweet_element = tweet_element.find_element(
                    By.CSS_SELECTOR, "[data-testid='retweet']"
                )
                retweet_text = retweet_element.get_attribute(
                    "aria-label") or ""
                metrics['retweets'] = self._parse_count_from_aria(retweet_text)
            except:
                pass

            try:
                # Try to get like count
                like_element = tweet_element.find_element(
                    By.CSS_SELECTOR, "[data-testid='like']"
                )
                like_text = like_element.get_attribute("aria-label") or ""
                metrics['likes'] = self._parse_count_from_aria(like_text)
            except:
                pass

            return {
                "post_id": tweet_id,
                "text": text,
                "author": author,
                "created_at": created_at,
                "url": tweet_url,
                "retweet_count": metrics['retweets'],
                "reply_count": metrics['replies'],
                "like_count": metrics['likes'],
                "matched_keyword": search_query,
                "source": "twitter_selenium",
                "collected_at": datetime.now(timezone.utc)
            }

        except Exception as e:
            logger.warning(f"Error extracting tweet data: {e}")
            return None

    def _parse_count_from_aria(self, aria_text: str) -> int:
        """Parse count from aria-label like '5 replies' or '1.2K likes'."""
        try:
            # Extract number from text
            match = re.search(r'([\d,.]+[KMB]?)', aria_text)
            if not match:
                return 0

            count_str = match.group(1).replace(',', '')

            if 'K' in count_str:
                return int(float(count_str.replace('K', '')) * 1000)
            elif 'M' in count_str:
                return int(float(count_str.replace('M', '')) * 1000000)
            elif 'B' in count_str:
                return int(float(count_str.replace('B', '')) * 1000000000)
            else:
                return int(float(count_str))
        except:
            return 0

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
