"""Data collection endpoints."""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime, timezone

from app.db.session import get_db
from app.collectors.reddit_collector import RedditCollector
from app.collectors.twitter_collector import TwitterCollector
from app.models.post import Post
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


def save_posts_to_db(posts: List[Dict[str, Any]], db: Session):
    """
    Save collected posts to database.
    
    Args:
        posts: List of post dictionaries
        db: Database session
    """
    for post_data in posts:
        # Check if post already exists
        existing = db.query(Post).filter(
            Post.post_id == post_data['post_id']
        ).first()
        
        if existing:
            logger.debug(f"Post {post_data['post_id']} already exists, skipping")
            continue
        
        # Create new post
        post = Post(**post_data)
        db.add(post)
    
    db.commit()
    logger.info(f"Saved {len(posts)} new posts to database")


@router.post("/reddit/collect")
async def collect_reddit(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Collect posts from configured Reddit subreddits.
    
    Runs in background to avoid timeout on large collections.
    """
    def collect_and_save():
        try:
            collector = RedditCollector()
            posts = collector.collect_from_all_subreddits()
            save_posts_to_db(posts, db)
            logger.info(f"Reddit collection complete: {len(posts)} posts")
        except Exception as e:
            logger.error(f"Error in Reddit collection: {e}")
    
    background_tasks.add_task(collect_and_save)
    
    return {
        "status": "started",
        "message": "Reddit collection started in background"
    }


@router.post("/reddit/search")
async def search_reddit(
    keywords: List[str],
    subreddit: str = "Economics",
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Search Reddit for specific keywords.
    
    Args:
        keywords: List of keywords to search
        subreddit: Subreddit to search in
        limit: Max results per keyword
    """
    try:
        collector = RedditCollector()
        posts = collector.search_keywords(subreddit, keywords, limit)
        save_posts_to_db(posts, db)
        
        return {
            "status": "success",
            "subreddit": subreddit,
            "keywords": keywords,
            "posts_collected": len(posts)
        }
    except Exception as e:
        logger.error(f"Error searching Reddit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/twitter/collect")
async def collect_twitter(
    background_tasks: BackgroundTasks,
    keywords: List[str] = None,
    hours_back: int = 24,
    db: Session = Depends(get_db)
):
    """
    Collect tweets matching economic keywords.
    
    Args:
        keywords: Keywords to search (uses config if None)
        hours_back: How many hours back to search
    """
    def collect_and_save():
        try:
            collector = TwitterCollector()
            tweets = collector.collect_by_keywords(
                keywords=keywords,
                hours_back=hours_back
            )
            save_posts_to_db(tweets, db)
            logger.info(f"Twitter collection complete: {len(tweets)} tweets")
        except Exception as e:
            logger.error(f"Error in Twitter collection: {e}")
    
    background_tasks.add_task(collect_and_save)
    
    return {
        "status": "started",
        "message": "Twitter collection started in background",
        "hours_back": hours_back
    }


@router.post("/collect-all")
async def collect_all_sources(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Collect from all sources (Reddit + Twitter).
    """
    def collect_all():
        try:
            # Collect from Reddit
            reddit_collector = RedditCollector()
            reddit_posts = reddit_collector.collect_from_all_subreddits()
            save_posts_to_db(reddit_posts, db)
            
            # Collect from Twitter
            twitter_collector = TwitterCollector()
            tweets = twitter_collector.collect_by_keywords()
            save_posts_to_db(tweets, db)
            
            logger.info(
                f"Collection complete: {len(reddit_posts)} Reddit posts, "
                f"{len(tweets)} tweets"
            )
        except Exception as e:
            logger.error(f"Error in collection: {e}")
    
    background_tasks.add_task(collect_all)
    
    return {
        "status": "started",
        "message": "Collection from all sources started in background"
    }


@router.get("/stats")
async def get_collection_stats(db: Session = Depends(get_db)):
    """Get statistics about collected posts."""
    try:
        # Total posts
        total_posts = db.query(Post).count()
        
        # By source
        reddit_count = db.query(Post).filter(Post.source == 'reddit').count()
        twitter_count = db.query(Post).filter(Post.source == 'twitter').count()
        
        # Recent posts (last 24 hours)
        recent_cutoff = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        recent_posts = db.query(Post).filter(Post.created_at >= recent_cutoff).count()
        
        # By subreddit
        subreddit_counts = {}
        subreddits = db.query(Post.subreddit).filter(Post.subreddit.isnot(None)).distinct().all()
        for (subreddit,) in subreddits:
            count = db.query(Post).filter(Post.subreddit == subreddit).count()
            subreddit_counts[subreddit] = count
        
        return {
            "total_posts": total_posts,
            "reddit_posts": reddit_count,
            "twitter_posts": twitter_count,
            "recent_posts_24h": recent_posts,
            "subreddit_breakdown": subreddit_counts
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
