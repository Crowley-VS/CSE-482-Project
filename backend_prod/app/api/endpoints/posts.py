"""Post retrieval endpoints - READ ONLY."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.models.post import Post
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/")
async def get_posts(
    source: Optional[str] = None,
    subreddit: Optional[str] = None,
    keyword: Optional[str] = None,
    hours_back: int = Query(168, description="Hours of history to retrieve"),
    limit: int = Query(100, le=1000),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get posts with optional filtering.

    Args:
        source: Filter by source ('reddit' or 'twitter')
        subreddit: Filter by subreddit
        keyword: Filter by matched keyword
        hours_back: Hours of historical data to retrieve
        limit: Maximum posts to return
        offset: Pagination offset
    """
    try:
        query = db.query(Post)

        # Time filter
        if hours_back:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
            query = query.filter(Post.created_at >= cutoff_time)

        # Source filter
        if source:
            query = query.filter(Post.source == source)

        # Subreddit filter
        if subreddit:
            query = query.filter(Post.subreddit == subreddit)

        # Keyword filter
        if keyword:
            query = query.filter(Post.matched_keyword == keyword)

        # Order by most recent first
        query = query.order_by(Post.created_at.desc())

        # Paginate
        posts = query.offset(offset).limit(limit).all()

        return {
            "count": len(posts),
            "posts": [post.to_dict() for post in posts]
        }
    except Exception as e:
        logger.error(f"Error retrieving posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{post_id}")
async def get_post(
    post_id: str,
    db: Session = Depends(get_db)
):
    """Get details for a specific post."""
    post = db.query(Post).filter(Post.post_id == post_id).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return post.to_dict()
