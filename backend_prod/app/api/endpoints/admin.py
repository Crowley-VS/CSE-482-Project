"""Administrative endpoints for database management."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.event import Event, EventSummary
from app.models.post import Post
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.delete("/purge")
async def purge_database(
    confirm: bool = False,
    db: Session = Depends(get_db)
):
    """
    Purge all data from the database.

    WARNING: This will delete ALL events, event summaries, and posts.
    This action cannot be undone.

    Args:
        confirm: Must be set to True to execute the purge

    Returns:
        Summary of deleted records
    """
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail="Must set confirm=true to purge database. This will delete ALL data."
        )

    try:
        # Count records before deletion
        event_count = db.query(Event).count()
        summary_count = db.query(EventSummary).count()
        post_count = db.query(Post).count()

        # Delete all records
        db.query(EventSummary).delete()
        db.query(Event).delete()
        db.query(Post).delete()

        # Commit the transaction
        db.commit()

        logger.warning(
            f"Database purged: {event_count} events, "
            f"{summary_count} summaries, {post_count} posts deleted"
        )

        return {
            "status": "success",
            "message": "Database purged successfully",
            "deleted": {
                "events": event_count,
                "event_summaries": summary_count,
                "posts": post_count,
                "total": event_count + summary_count + post_count
            }
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error purging database: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to purge database: {str(e)}")
