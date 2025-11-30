"""Reddit data collector using PRAW."""
import praw
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedditCollector:
    """Collect posts from Reddit using PRAW."""
    
    def __init__(self):
        """Initialize Reddit API client."""
        self.reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT
        )
        logger.info("Reddit collector initialized")
    
    def collect_from_subreddit(
        self,
        subreddit_name: str,
        limit: int = None,
        time_filter: str = "day"
    ) -> List[Dict[str, Any]]:
        """
        Collect posts from a specific subreddit.
        
        Args:
            subreddit_name: Name of the subreddit (e.g., 'Economics')
            limit: Maximum number of posts to fetch
            time_filter: Time filter ('hour', 'day', 'week', 'month', 'year', 'all')
            
        Returns:
            List of post dictionaries with standardized fields
        """
        if limit is None:
            limit = settings.MAX_POSTS_PER_SUBREDDIT
            
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            
            # Collect from hot posts
            for submission in subreddit.hot(limit=limit):
                post_data = self._extract_post_data(submission, subreddit_name)
                posts.append(post_data)
            
            logger.info(f"Collected {len(posts)} posts from r/{subreddit_name}")
            return posts
            
        except Exception as e:
            logger.error(f"Error collecting from r/{subreddit_name}: {e}")
            return []
    
    def collect_from_all_subreddits(self) -> List[Dict[str, Any]]:
        """
        Collect posts from all configured subreddits.
        
        Returns:
            Combined list of posts from all subreddits
        """
        all_posts = []
        
        for subreddit_name in settings.SUBREDDITS:
            posts = self.collect_from_subreddit(subreddit_name)
            all_posts.extend(posts)
        
        logger.info(f"Total posts collected from Reddit: {len(all_posts)}")
        return all_posts
    
    def search_keywords(
        self,
        subreddit_name: str,
        keywords: List[str],
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Search for posts containing specific keywords in a subreddit.
        
        Args:
            subreddit_name: Name of the subreddit
            keywords: List of keywords to search for
            limit: Maximum number of posts per keyword
            
        Returns:
            List of matching posts
        """
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            seen_ids = set()
            
            for keyword in keywords:
                try:
                    for submission in subreddit.search(
                        keyword,
                        limit=limit,
                        time_filter="week"
                    ):
                        # Avoid duplicates
                        if submission.id not in seen_ids:
                            post_data = self._extract_post_data(submission, subreddit_name)
                            post_data['matched_keyword'] = keyword
                            posts.append(post_data)
                            seen_ids.add(submission.id)
                except Exception as e:
                    logger.error(f"Error searching for '{keyword}': {e}")
                    continue
            
            logger.info(f"Found {len(posts)} posts matching keywords in r/{subreddit_name}")
            return posts
            
        except Exception as e:
            logger.error(f"Error in keyword search: {e}")
            return []
    
    def _extract_post_data(
        self,
        submission: praw.models.Submission,
        subreddit_name: str
    ) -> Dict[str, Any]:
        """
        Extract standardized data from a Reddit submission.
        
        Args:
            submission: PRAW submission object
            subreddit_name: Name of the subreddit
            
        Returns:
            Dictionary with standardized post data
        """
        # Convert UTC timestamp to datetime
        created_utc = datetime.fromtimestamp(
            submission.created_utc,
            tz=timezone.utc
        )
        
        return {
            'source': 'reddit',
            'post_id': submission.id,
            'subreddit': subreddit_name,
            'title': submission.title,
            'text': submission.selftext,
            'author': str(submission.author) if submission.author else '[deleted]',
            'score': submission.score,
            'upvote_ratio': submission.upvote_ratio,
            'num_comments': submission.num_comments,
            'created_at': created_utc,
            'url': f"https://reddit.com{submission.permalink}",
            'is_self': submission.is_self,
            'link_flair_text': submission.link_flair_text,
            'collected_at': datetime.now(timezone.utc)
        }
    
    def get_post_comments(self, post_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get comments from a specific post.
        
        Args:
            post_id: Reddit post ID
            limit: Maximum number of comments to fetch
            
        Returns:
            List of comment dictionaries
        """
        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)
            
            comments = []
            for comment in submission.comments.list()[:limit]:
                if hasattr(comment, 'body'):
                    created_utc = datetime.fromtimestamp(
                        comment.created_utc,
                        tz=timezone.utc
                    )
                    comments.append({
                        'comment_id': comment.id,
                        'post_id': post_id,
                        'text': comment.body,
                        'author': str(comment.author) if comment.author else '[deleted]',
                        'score': comment.score,
                        'created_at': created_utc
                    })
            
            logger.info(f"Collected {len(comments)} comments from post {post_id}")
            return comments
            
        except Exception as e:
            logger.error(f"Error collecting comments for post {post_id}: {e}")
            return []
