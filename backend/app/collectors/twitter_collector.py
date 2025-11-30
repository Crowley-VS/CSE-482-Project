"""Twitter data collector using tweepy."""
import tweepy
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TwitterCollector:
    """Collect tweets using Twitter API v2."""
    
    def __init__(self):
        """Initialize Twitter API client."""
        self.client = tweepy.Client(
            bearer_token=settings.TWITTER_BEARER_TOKEN,
            consumer_key=settings.TWITTER_API_KEY,
            consumer_secret=settings.TWITTER_API_SECRET,
            access_token=settings.TWITTER_ACCESS_TOKEN,
            access_token_secret=settings.TWITTER_ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
        logger.info("Twitter collector initialized")
    
    def collect_by_keywords(
        self,
        keywords: List[str] = None,
        max_results: int = None,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Collect tweets containing economic keywords.
        
        Args:
            keywords: List of keywords to search for (uses config if None)
            max_results: Maximum tweets to collect (uses config if None)
            hours_back: How many hours back to search
            
        Returns:
            List of tweet dictionaries with standardized fields
        """
        if keywords is None:
            keywords = settings.ECONOMIC_KEYWORDS
        if max_results is None:
            max_results = settings.MAX_TWEETS_PER_QUERY
            
        all_tweets = []
        
        for keyword in keywords:
            tweets = self._search_keyword(keyword, max_results, hours_back)
            all_tweets.extend(tweets)
        
        # Remove duplicates based on tweet_id
        unique_tweets = {tweet['post_id']: tweet for tweet in all_tweets}
        result = list(unique_tweets.values())
        
        logger.info(f"Total tweets collected: {len(result)} (from {len(all_tweets)} with duplicates)")
        return result
    
    def _search_keyword(
        self,
        keyword: str,
        max_results: int,
        hours_back: int
    ) -> List[Dict[str, Any]]:
        """
        Search for tweets containing a specific keyword.
        
        Args:
            keyword: Keyword to search for
            max_results: Maximum number of results
            hours_back: How many hours back to search
            
        Returns:
            List of tweet dictionaries
        """
        try:
            # Calculate start time
            start_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            
            # Build query (exclude retweets for cleaner data)
            query = f"{keyword} -is:retweet lang:en"
            
            # Search tweets
            response = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),  # API limit is 100
                tweet_fields=['created_at', 'public_metrics', 'author_id', 'lang'],
                start_time=start_time
            )
            
            tweets = []
            if response.data:
                for tweet in response.data:
                    tweet_data = self._extract_tweet_data(tweet, keyword)
                    tweets.append(tweet_data)
            
            logger.info(f"Collected {len(tweets)} tweets for keyword '{keyword}'")
            return tweets
            
        except tweepy.TweepyException as e:
            logger.error(f"Error searching for keyword '{keyword}': {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error searching for '{keyword}': {e}")
            return []
    
    def collect_by_hashtags(
        self,
        hashtags: List[str],
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Collect tweets by hashtags.
        
        Args:
            hashtags: List of hashtags (without #)
            max_results: Maximum tweets per hashtag
            
        Returns:
            List of tweet dictionaries
        """
        all_tweets = []
        
        for hashtag in hashtags:
            query = f"#{hashtag} -is:retweet lang:en"
            
            try:
                response = self.client.search_recent_tweets(
                    query=query,
                    max_results=min(max_results, 100),
                    tweet_fields=['created_at', 'public_metrics', 'author_id']
                )
                
                if response.data:
                    for tweet in response.data:
                        tweet_data = self._extract_tweet_data(tweet, f"#{hashtag}")
                        all_tweets.append(tweet_data)
                        
            except Exception as e:
                logger.error(f"Error collecting hashtag #{hashtag}: {e}")
                continue
        
        logger.info(f"Collected {len(all_tweets)} tweets from hashtags")
        return all_tweets
    
    def _extract_tweet_data(
        self,
        tweet: tweepy.Tweet,
        matched_keyword: str
    ) -> Dict[str, Any]:
        """
        Extract standardized data from a tweet.
        
        Args:
            tweet: Tweepy Tweet object
            matched_keyword: The keyword that matched this tweet
            
        Returns:
            Dictionary with standardized tweet data
        """
        metrics = tweet.public_metrics if hasattr(tweet, 'public_metrics') else {}
        
        return {
            'source': 'twitter',
            'post_id': tweet.id,
            'text': tweet.text,
            'author_id': tweet.author_id if hasattr(tweet, 'author_id') else None,
            'created_at': tweet.created_at,
            'retweet_count': metrics.get('retweet_count', 0),
            'reply_count': metrics.get('reply_count', 0),
            'like_count': metrics.get('like_count', 0),
            'quote_count': metrics.get('quote_count', 0),
            'matched_keyword': matched_keyword,
            'url': f"https://twitter.com/i/web/status/{tweet.id}",
            'collected_at': datetime.now(timezone.utc)
        }
    
    def get_user_timeline(
        self,
        username: str,
        max_results: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent tweets from a specific user.
        
        Args:
            username: Twitter username (without @)
            max_results: Maximum number of tweets
            
        Returns:
            List of tweet dictionaries
        """
        try:
            # Get user ID first
            user = self.client.get_user(username=username)
            if not user.data:
                logger.error(f"User {username} not found")
                return []
            
            user_id = user.data.id
            
            # Get user's tweets
            response = self.client.get_users_tweets(
                id=user_id,
                max_results=min(max_results, 100),
                tweet_fields=['created_at', 'public_metrics']
            )
            
            tweets = []
            if response.data:
                for tweet in response.data:
                    tweet_data = self._extract_tweet_data(tweet, f"@{username}")
                    tweets.append(tweet_data)
            
            logger.info(f"Collected {len(tweets)} tweets from @{username}")
            return tweets
            
        except Exception as e:
            logger.error(f"Error collecting tweets from @{username}: {e}")
            return []
