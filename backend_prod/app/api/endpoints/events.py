"""Event retrieval endpoints - READ ONLY."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.models.event import Event, DetectionMethod, EventSummary
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/")
async def get_events(
    method: Optional[DetectionMethod] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """
    Get detected events with summaries.

    Args:
        method: Filter by detection method
        limit: Maximum events to return
        offset: Pagination offset
    """
    try:
        query = db.query(Event)

        if method:
            query = query.filter(Event.detection_method == method)

        # Order by most recent first
        query = query.order_by(Event.detected_at.desc())

        # Paginate
        events = query.offset(offset).limit(limit).all()

        return {
            "count": len(events),
            "events": [event.to_dict(include_summary=True, db_session=db) for event in events]
        }
    except Exception as e:
        logger.error(f"Error retrieving events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{event_id}")
async def get_event(
    event_id: int,
    db: Session = Depends(get_db)
):
    """Get details for a specific event with summary."""
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return event.to_dict(include_summary=True, db_session=db)


@router.get("/{event_id}/posts")
async def get_event_posts(
    event_id: int,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db)
):
    """Get posts associated with an event."""
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    from app.models.post import Post

    # Get posts by IDs
    posts = db.query(Post).filter(
        Post.post_id.in_(event.post_ids[:limit])
    ).all()

    return {
        "event_id": event_id,
        "total_posts": event.num_posts,
        "returned_posts": len(posts),
        "posts": [post.to_dict() for post in posts]
    }
