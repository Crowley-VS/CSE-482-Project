"""
Example script demonstrating how to use Selenium collectors for Reddit and Twitter.

This script shows how to:
1. Use the Reddit Selenium collector with authentication
2. Use the Twitter Selenium collector with authentication
3. Collect data from both platforms without API access
"""

from app.collectors.reddit_selenium_collector import RedditSeleniumCollector
from app.collectors.twitter_selenium_collector import TwitterSeleniumCollector
from app.core.logging import get_logger

logger = get_logger(__name__)


def example_reddit_collection():
    """Example: Collect posts from Reddit using Selenium."""
    logger.info("=" * 60)
    logger.info("Reddit Selenium Collection Example")
    logger.info("=" * 60)

    # Initialize collector (headless=False to see browser, useful for debugging)
    with RedditSeleniumCollector(headless=True) as collector:
        # Login is automatic when collecting if credentials are set
        # Or you can manually login first:
        # collector.login()

        # Collect from a single subreddit
        posts = collector.collect_from_subreddit(
            subreddit_name="Economics",
            limit=10,
            sort_by="hot"
        )

        logger.info(f"\nCollected {len(posts)} posts from r/Economics")

        # Display first post
        if posts:
            first_post = posts[0]
            logger.info(f"\nExample post:")
            logger.info(f"  Title: {first_post['title'][:80]}...")
            logger.info(f"  Author: {first_post['author']}")
            logger.info(f"  Score: {first_post['score']}")
            logger.info(f"  Comments: {first_post['num_comments']}")
            logger.info(f"  URL: {first_post['url']}")

        # Collect from multiple subreddits
        all_posts = collector.collect_from_multiple_subreddits(
            subreddit_names=["Economics", "Finance"],
            limit_per_subreddit=5
        )

        logger.info(
            f"\nCollected {len(all_posts)} total posts from multiple subreddits")

    # Driver is automatically closed when exiting context manager


def example_twitter_collection():
    """Example: Collect tweets from Twitter using Selenium."""
    logger.info("\n" + "=" * 60)
    logger.info("Twitter Selenium Collection Example")
    logger.info("=" * 60)

    # Initialize collector
    with TwitterSeleniumCollector(headless=True) as collector:
        # Login is automatic when searching if credentials are set
        # Or you can manually login first:
        # collector.login()

        # Search for specific query
        tweets = collector.collect_by_search(
            query="inflation",
            limit=10,
            filter_type="Latest"
        )

        logger.info(f"\nCollected {len(tweets)} tweets about inflation")

        # Display first tweet
        if tweets:
            first_tweet = tweets[0]
            logger.info(f"\nExample tweet:")
            logger.info(f"  Text: {first_tweet['text'][:80]}...")
            logger.info(f"  Author: @{first_tweet['author']}")
            logger.info(f"  Likes: {first_tweet['like_count']}")
            logger.info(f"  Retweets: {first_tweet['retweet_count']}")
            logger.info(f"  URL: {first_tweet['url']}")

        # Collect by multiple keywords
        keyword_tweets = collector.collect_by_keywords(
            keywords=["CPI", "Federal Reserve", "interest rates"],
            max_results=20
        )

        logger.info(
            f"\nCollected {len(keyword_tweets)} tweets from multiple keywords")

    # Driver is automatically closed when exiting context manager


def example_combined_collection():
    """Example: Collect from both platforms."""
    logger.info("\n" + "=" * 60)
    logger.info("Combined Collection Example")
    logger.info("=" * 60)

    all_data = {
        'reddit_posts': [],
        'tweets': []
    }

    # Collect from Reddit
    with RedditSeleniumCollector(headless=True) as reddit_collector:
        all_data['reddit_posts'] = reddit_collector.collect_from_multiple_subreddits(
            limit_per_subreddit=5
        )

    # Collect from Twitter
    with TwitterSeleniumCollector(headless=True) as twitter_collector:
        all_data['tweets'] = twitter_collector.collect_by_keywords(
            max_results=20
        )

    logger.info(f"\nTotal collected:")
    logger.info(f"  Reddit posts: {len(all_data['reddit_posts'])}")
    logger.info(f"  Tweets: {len(all_data['tweets'])}")

    return all_data


if __name__ == "__main__":
    # Make sure to set your credentials in .env file:
    # REDDIT_USERNAME=your_username
    # REDDIT_PASSWORD=your_password
    # TWITTER_USERNAME=your_username
    # TWITTER_PASSWORD=your_password

    try:
        # Run individual examples
        example_reddit_collection()
        example_twitter_collection()

        # Or run combined collection
        # data = example_combined_collection()

    except Exception as e:
        logger.error(f"Error in example: {e}", exc_info=True)
