"""Data export and import endpoints for posts and events."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime

from app.db.session import get_db
from app.models.post import Post
from app.models.event import Event, DetectionMethod, EventSummary
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/export")
async def export_data(db: Session = Depends(get_db)):
    """
    Export all posts and events from the database.

    Returns:
        JSON containing all posts and events with their full data
    """
    try:
        # Fetch all posts
        posts = db.query(Post).all()
        posts_data = []

        for post in posts:
            post_dict = {
                'id': post.id,
                'source': post.source,
                'post_id': post.post_id,
                'title': post.title,
                'text': post.text,
                'author': post.author,
                'author_id': post.author_id,
                'subreddit': post.subreddit,
                'score': post.score,
                'upvote_ratio': post.upvote_ratio,
                'num_comments': post.num_comments,
                'is_self': post.is_self,
                'link_flair_text': post.link_flair_text,
                'retweet_count': post.retweet_count,
                'reply_count': post.reply_count,
                'like_count': post.like_count,
                'quote_count': post.quote_count,
                'matched_keyword': post.matched_keyword,
                'url': post.url,
                'created_at': post.created_at.isoformat() if post.created_at is not None else None,
                'collected_at': post.collected_at.isoformat() if post.collected_at is not None else None,
            }
            posts_data.append(post_dict)

        # Fetch all events
        events = db.query(Event).all()
        events_data = []

        for event in events:
            event_dict = {
                'id': event.id,
                'event_name': event.event_name,
                'event_type': event.event_type,
                'detection_method': event.detection_method.value if event.detection_method is not None else None,
                'confidence_score': event.confidence_score,
                'description': event.description,
                'keywords': event.keywords,
                'post_ids': event.post_ids,
                'num_posts': event.num_posts,
                'reddit_count': event.reddit_count,
                'twitter_count': event.twitter_count,
                'event_start': event.event_start.isoformat() if event.event_start is not None else None,
                'event_end': event.event_end.isoformat() if event.event_end is not None else None,
                'peak_time': event.peak_time.isoformat() if event.peak_time is not None else None,
                'total_engagement': event.total_engagement,
                'avg_sentiment': event.avg_sentiment,
                'topic_id': event.topic_id,
                'topic_words': event.topic_words,
                'detected_at': event.detected_at.isoformat() if event.detected_at is not None else None,
                'updated_at': event.updated_at.isoformat() if event.updated_at is not None else None,
            }
            events_data.append(event_dict)

        # Fetch all event summaries
        summaries = db.query(EventSummary).all()
        summaries_data = []

        for summary in summaries:
            summary_dict = {
                'id': summary.id,
                'event_id': summary.event_id,
                'summary_text': summary.summary_text,
                'summary_method': summary.summary_method,
                'rouge_1': summary.rouge_1,
                'rouge_2': summary.rouge_2,
                'rouge_l': summary.rouge_l,
                'bleu_score': summary.bleu_score,
                'num_source_posts': summary.num_source_posts,
                'created_at': summary.created_at.isoformat() if summary.created_at is not None else None,
            }
            summaries_data.append(summary_dict)

        export_data = {
            'export_timestamp': datetime.utcnow().isoformat(),
            'posts_count': len(posts_data),
            'events_count': len(events_data),
            'summaries_count': len(summaries_data),
            'posts': posts_data,
            'events': events_data,
            'summaries': summaries_data,
        }

        logger.info(
            f"Exported {len(posts_data)} posts, {len(events_data)} events, and {len(summaries_data)} summaries")
        return JSONResponse(content=export_data)

    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.post("/import")
async def import_data(
    data: Dict[str, Any],
    replace_existing: bool = False,
    db: Session = Depends(get_db)
):
    """
    Import posts and events into the database.

    Args:
        data: Dictionary containing 'posts' and 'events' arrays
        replace_existing: If True, replace existing records with same IDs

    Returns:
        Summary of import operation
    """
    try:
        posts_imported = 0
        posts_skipped = 0
        events_imported = 0
        events_skipped = 0
        summaries_imported = 0
        summaries_skipped = 0
        errors = []

        # Import posts
        if 'posts' in data:
            for post_data in data['posts']:
                try:
                    # Check if post already exists
                    existing_post = db.query(Post).filter(
                        Post.post_id == post_data.get('post_id')
                    ).first()

                    if existing_post:
                        if replace_existing:
                            # Update existing post
                            for key, value in post_data.items():
                                if key not in ['id', 'created_at', 'collected_at']:
                                    setattr(existing_post, key, value)
                                elif key in ['created_at', 'collected_at'] and value:
                                    setattr(existing_post, key,
                                            datetime.fromisoformat(value))
                            posts_imported += 1
                        else:
                            posts_skipped += 1
                            continue
                    else:
                        # Create new post
                        post_dict = {k: v for k,
                                     v in post_data.items() if k != 'id'}

                        # Convert datetime strings to datetime objects
                        if post_dict.get('created_at'):
                            post_dict['created_at'] = datetime.fromisoformat(
                                post_dict['created_at'])
                        if post_dict.get('collected_at'):
                            post_dict['collected_at'] = datetime.fromisoformat(
                                post_dict['collected_at'])

                        new_post = Post(**post_dict)
                        db.add(new_post)
                        posts_imported += 1

                except Exception as e:
                    error_msg = f"Error importing post {post_data.get('post_id', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue

        # Import events
        if 'events' in data:
            for event_data in data['events']:
                try:
                    # Check if event already exists (by event_name and time range)
                    existing_event = None
                    if event_data.get('event_name') and event_data.get('event_start'):
                        existing_event = db.query(Event).filter(
                            Event.event_name == event_data['event_name'],
                            Event.event_start == datetime.fromisoformat(
                                event_data['event_start'])
                        ).first()

                    if existing_event:
                        if replace_existing:
                            # Update existing event
                            for key, value in event_data.items():
                                if key not in ['id', 'detected_at', 'updated_at']:
                                    if key == 'detection_method' and value:
                                        setattr(existing_event, key,
                                                DetectionMethod(value))
                                    elif key in ['event_start', 'event_end', 'peak_time'] and value:
                                        setattr(existing_event, key,
                                                datetime.fromisoformat(value))
                                    else:
                                        setattr(existing_event, key, value)
                            events_imported += 1
                        else:
                            events_skipped += 1
                            continue
                    else:
                        # Create new event
                        event_dict = {k: v for k, v in event_data.items() if k not in [
                            'id', 'detected_at', 'updated_at']}

                        # Convert datetime strings to datetime objects
                        if event_dict.get('event_start'):
                            event_dict['event_start'] = datetime.fromisoformat(
                                event_dict['event_start'])
                        if event_dict.get('event_end'):
                            event_dict['event_end'] = datetime.fromisoformat(
                                event_dict['event_end'])
                        if event_dict.get('peak_time'):
                            event_dict['peak_time'] = datetime.fromisoformat(
                                event_dict['peak_time'])

                        # Convert detection_method string to enum
                        if event_dict.get('detection_method'):
                            event_dict['detection_method'] = DetectionMethod(
                                event_dict['detection_method'])

                        new_event = Event(**event_dict)
                        db.add(new_event)
                        events_imported += 1

                except Exception as e:
                    error_msg = f"Error importing event {event_data.get('event_name', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue

        # Import event summaries
        if 'summaries' in data:
            for summary_data in data['summaries']:
                try:
                    # Check if summary already exists
                    existing_summary = db.query(EventSummary).filter(
                        EventSummary.event_id == summary_data.get('event_id'),
                        EventSummary.summary_method == summary_data.get(
                            'summary_method')
                    ).first()

                    if existing_summary:
                        if replace_existing:
                            # Update existing summary
                            for key, value in summary_data.items():
                                if key not in ['id', 'created_at']:
                                    if key == 'created_at' and value:
                                        setattr(existing_summary, key,
                                                datetime.fromisoformat(value))
                                    else:
                                        setattr(existing_summary, key, value)
                            summaries_imported += 1
                        else:
                            summaries_skipped += 1
                            continue
                    else:
                        # Create new summary
                        summary_dict = {k: v for k, v in summary_data.items() if k not in [
                            'id', 'created_at']}

                        new_summary = EventSummary(**summary_dict)
                        db.add(new_summary)
                        summaries_imported += 1

                except Exception as e:
                    error_msg = f"Error importing summary for event {summary_data.get('event_id', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    continue

        # Commit all changes
        db.commit()

        result = {
            'status': 'success',
            'posts': {
                'imported': posts_imported,
                'skipped': posts_skipped,
            },
            'events': {
                'imported': events_imported,
                'skipped': events_skipped,
            },
            'summaries': {
                'imported': summaries_imported,
                'skipped': summaries_skipped,
            },
            'errors': errors if errors else None,
        }

        logger.info(
            f"Import completed: {posts_imported} posts, {events_imported} events, {summaries_imported} summaries")
        return result

    except Exception as e:
        db.rollback()
        logger.error(f"Error importing data: {e}")
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
