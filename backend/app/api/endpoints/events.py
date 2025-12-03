"""Event detection and retrieval endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone

from app.db.session import get_db
from app.models.event import Event, DetectionMethod, EventSummary
from app.event_detection.keyword_spike import KeywordSpikeDetector
from app.event_detection.bertopic_detector import BERTopicDetector
from app.event_detection.lda_detector import LDADetector
from app.event_detection.chatgpt_summarizer import ChatGPTSummarizer, generate_event_summary
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/detect/keyword-spike")
async def detect_keyword_spikes(
    hours_back: int = Query(
        168, description="Hours of history to analyze (default: 7 days)"),
    db: Session = Depends(get_db)
):
    """
    Detect events using keyword spike analysis.

    Args:
        hours_back: Hours of historical data to analyze
    """
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)

        detector = KeywordSpikeDetector(db)
        events = detector.detect_events(start_time, end_time)

        # Save events to database
        for event in events:
            db.add(event)
        db.commit()

        return {
            "status": "success",
            "method": "keyword_spike",
            "events_detected": len(events),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error in keyword spike detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/bertopic")
async def detect_with_bertopic(
    hours_back: int = Query(168, description="Hours of history to analyze"),
    min_topic_size: int = Query(10, description="Minimum posts per topic"),
    db: Session = Depends(get_db)
):
    """
    Detect events using BERTopic clustering.

    Args:
        hours_back: Hours of historical data to analyze
        min_topic_size: Minimum posts per topic
    """
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)

        detector = BERTopicDetector(db)
        events = detector.detect_events(
            start_time,
            end_time,
            min_topic_size=min_topic_size
        )

        # Save events to database
        for event in events:
            db.add(event)
        db.commit()

        return {
            "status": "success",
            "method": "bertopic",
            "events_detected": len(events),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error in BERTopic detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/detect/lda")
async def detect_with_lda(
    hours_back: int = Query(168, description="Hours of history to analyze"),
    num_topics: int = Query(10, description="Number of topics to discover"),
    db: Session = Depends(get_db)
):
    """
    Detect events using LDA topic modeling.

    Args:
        hours_back: Hours of historical data to analyze
        num_topics: Number of topics to discover
    """
    try:
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)

        detector = LDADetector(db)
        events = detector.detect_events(
            start_time,
            end_time,
            num_topics=num_topics
        )

        # Save events to database
        for event in events:
            db.add(event)
        db.commit()

        return {
            "status": "success",
            "method": "lda",
            "events_detected": len(events),
            "time_range": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error in LDA detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


@router.get("/trends/keywords")
async def get_keyword_trends(
    hours_back: int = Query(168, description="Hours of history"),
    db: Session = Depends(get_db)
):
    """Get keyword trends over time."""
    try:
        detector = KeywordSpikeDetector(db)
        trends = detector.get_keyword_trends(hours_back)

        return {
            "hours_analyzed": hours_back,
            "trends": trends
        }
    except Exception as e:
        logger.error(f"Error getting keyword trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{event_id}")
async def delete_event(event_id: int, db: Session = Depends(get_db)):
    """Delete an event."""
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    db.delete(event)
    db.commit()

    return {"status": "deleted", "event_id": event_id}


@router.delete("/purge/all")
async def purge_all_events(db: Session = Depends(get_db)):
    """
    Purge all events from the database.

    WARNING: This will delete all events and their summaries permanently.
    """
    try:
        # Delete all event summaries first (due to foreign key constraints)
        summaries_deleted = db.query(EventSummary).delete()

        # Delete all events
        events_deleted = db.query(Event).delete()

        db.commit()

        logger.info(
            f"Purged {events_deleted} events and {summaries_deleted} summaries")

        return {
            "status": "success",
            "events_deleted": events_deleted,
            "summaries_deleted": summaries_deleted,
            "message": "All events and summaries have been purged"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error purging events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{event_id}/summary")
async def generate_summary(
    event_id: int,
    model: str = Query("gpt-3.5-turbo", description="OpenAI model to use"),
    regenerate: bool = Query(
        False, description="Force regenerate if summary exists"),
    db: Session = Depends(get_db)
):
    """
    Generate a ChatGPT summary for an event.

    Args:
        event_id: Event ID to summarize
        model: OpenAI model (gpt-3.5-turbo, gpt-4, etc.)
        regenerate: Force regeneration even if summary exists
    """
    try:
        summary = generate_event_summary(
            db, event_id, model=model, regenerate=regenerate)

        if not summary:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate summary. Check OpenAI API key configuration."
            )

        return {
            "status": "success",
            "event_id": event_id,
            "summary": summary.to_dict()
        }
    except Exception as e:
        logger.error(f"Error generating summary for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summaries/batch")
async def batch_generate_summaries(
    event_ids: Optional[List[int]] = None,
    model: str = Query("gpt-3.5-turbo", description="OpenAI model to use"),
    regenerate: bool = Query(
        False, description="Force regenerate existing summaries"),
    db: Session = Depends(get_db)
):
    """
    Generate summaries for multiple events in batch.

    Args:
        event_ids: List of event IDs (None = all events)
        model: OpenAI model to use
        regenerate: Force regeneration for events with existing summaries
    """
    try:
        summarizer = ChatGPTSummarizer(db)
        results = summarizer.batch_generate_summaries(
            event_ids=event_ids,
            regenerate=regenerate,
            model=model
        )

        return {
            "status": "success",
            **results
        }
    except Exception as e:
        logger.error(f"Error in batch summary generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{event_id}/summary")
async def get_event_summary(event_id: int, db: Session = Depends(get_db)):
    """
    Get the latest summary for an event.

    Args:
        event_id: Event ID
    """
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Get latest ChatGPT summary
    summary = db.query(EventSummary).filter(
        EventSummary.event_id == event_id
    ).order_by(EventSummary.created_at.desc()).first()

    if not summary:
        return {
            "event_id": event_id,
            "has_summary": False,
            "message": "No summary available. Use POST /{event_id}/summary to generate one."
        }

    return {
        "event_id": event_id,
        "has_summary": True,
        "event": event.to_dict(),
        "summary": summary.to_dict()
    }
