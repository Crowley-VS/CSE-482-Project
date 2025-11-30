"""Scheduled tasks for data collection and event detection."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.collectors.reddit_collector import RedditCollector
from app.collectors.twitter_collector import TwitterCollector
from app.models.post import Post
from app.models.event import Event
from app.event_detection.keyword_spike import KeywordSpikeDetector
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def save_posts_to_db(posts, db: Session):
    """Save posts to database, avoiding duplicates."""
    saved_count = 0
    for post_data in posts:
        existing = db.query(Post).filter(
            Post.post_id == post_data['post_id']
        ).first()
        
        if not existing:
            post = Post(**post_data)
            db.add(post)
            saved_count += 1
    
    db.commit()
    logger.info(f"Saved {saved_count} new posts")
    return saved_count


def collect_reddit_data():
    """Scheduled task to collect Reddit data."""
    logger.info("Starting scheduled Reddit collection")
    db = SessionLocal()
    
    try:
        collector = RedditCollector()
        posts = collector.collect_from_all_subreddits()
        saved = save_posts_to_db(posts, db)
        logger.info(f"Reddit collection complete: {saved} new posts")
    except Exception as e:
        logger.error(f"Error in scheduled Reddit collection: {e}")
    finally:
        db.close()


def collect_twitter_data():
    """Scheduled task to collect Twitter data."""
    logger.info("Starting scheduled Twitter collection")
    db = SessionLocal()
    
    try:
        collector = TwitterCollector()
        tweets = collector.collect_by_keywords(
            hours_back=settings.COLLECTION_INTERVAL_HOURS + 1
        )
        saved = save_posts_to_db(tweets, db)
        logger.info(f"Twitter collection complete: {saved} new tweets")
    except Exception as e:
        logger.error(f"Error in scheduled Twitter collection: {e}")
    finally:
        db.close()


def detect_events():
    """Scheduled task to detect events using keyword spikes."""
    logger.info("Starting scheduled event detection")
    db = SessionLocal()
    
    try:
        # Detect events from last 24 hours
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=24)
        
        detector = KeywordSpikeDetector(db)
        events = detector.detect_events(start_time, end_time)
        
        # Save new events
        for event in events:
            # Check if similar event already exists
            existing = db.query(Event).filter(
                Event.event_name == event.event_name,
                Event.event_start == event.event_start
            ).first()
            
            if not existing:
                db.add(event)
        
        db.commit()
        logger.info(f"Event detection complete: {len(events)} events detected")
    except Exception as e:
        logger.error(f"Error in scheduled event detection: {e}")
    finally:
        db.close()


# Initialize scheduler
scheduler = BackgroundScheduler()


def start_scheduler():
    """Start the background scheduler for periodic tasks."""
    logger.info("Starting background scheduler")
    
    # Schedule Reddit collection
    scheduler.add_job(
        collect_reddit_data,
        trigger=IntervalTrigger(hours=settings.COLLECTION_INTERVAL_HOURS),
        id='collect_reddit',
        name='Collect Reddit posts',
        replace_existing=True
    )
    
    # Schedule Twitter collection
    scheduler.add_job(
        collect_twitter_data,
        trigger=IntervalTrigger(hours=settings.COLLECTION_INTERVAL_HOURS),
        id='collect_twitter',
        name='Collect Twitter posts',
        replace_existing=True
    )
    
    # Schedule event detection (every 6 hours)
    scheduler.add_job(
        detect_events,
        trigger=IntervalTrigger(hours=6),
        id='detect_events',
        name='Detect economic events',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    logger.info("Background scheduler stopped")
