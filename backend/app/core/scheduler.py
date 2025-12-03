"""Scheduled tasks for data collection and event detection."""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.collectors.reddit_selenium_collector import RedditSeleniumCollector
from app.collectors.twitter_selenium_collector import TwitterSeleniumCollector
from app.models.post import Post
from app.models.event import Event
from app.event_detection.lda_detector import LDADetector
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
    logger.info("="*60)
    logger.info("Starting scheduled Reddit collection")
    logger.info(f"Target subreddits: {settings.SUBREDDITS}")
    logger.info(f"Posts per subreddit: {settings.MAX_POSTS_PER_SUBREDDIT}")
    db = SessionLocal()

    try:
        with RedditSeleniumCollector(headless=settings.SELENIUM_HEADLESS) as collector:
            logger.info("Reddit collector initialized, beginning scraping...")
            posts = collector.collect_from_multiple_subreddits(
                subreddit_names=settings.SUBREDDITS,
                limit_per_subreddit=settings.MAX_POSTS_PER_SUBREDDIT
            )
            logger.info(f"Collected {len(posts)} total posts from Reddit")
            saved = save_posts_to_db(posts, db)
            logger.info(
                f"Reddit collection complete: {saved} new posts saved ({len(posts) - saved} duplicates skipped)")
    except Exception as e:
        logger.error(
            f"Error in scheduled Reddit collection: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("="*60)


def collect_twitter_data():
    """Scheduled task to collect Twitter data."""
    logger.info("="*60)
    logger.info("Starting scheduled Twitter collection")
    logger.info(f"Search keywords: {settings.ECONOMIC_KEYWORDS}")
    logger.info(f"Max tweets per query: {settings.MAX_TWEETS_PER_QUERY}")
    db = SessionLocal()

    try:
        with TwitterSeleniumCollector(headless=settings.SELENIUM_HEADLESS) as collector:
            logger.info("Twitter collector initialized, beginning scraping...")
            tweets = collector.collect_by_keywords(
                keywords=settings.ECONOMIC_KEYWORDS,
                max_results=settings.MAX_TWEETS_PER_QUERY
            )
            logger.info(f"Collected {len(tweets)} total tweets from Twitter")
            saved = save_posts_to_db(tweets, db)
            logger.info(
                f"Twitter collection complete: {saved} new tweets saved ({len(tweets) - saved} duplicates skipped)")
    except Exception as e:
        logger.error(
            f"Error in scheduled Twitter collection: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("="*60)


def detect_events():
    """Scheduled task to detect events using LDA topic modeling."""
    logger.info("="*60)
    logger.info("Starting scheduled event detection")
    db = SessionLocal()

    try:
        # Detect events from last 7 days (LDA needs more data)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=7)

        logger.info(
            f"Analyzing posts from {start_time.strftime('%Y-%m-%d %H:%M UTC')} to {end_time.strftime('%Y-%m-%d %H:%M UTC')}")

        detector = LDADetector(db)
        events = detector.detect_events(start_time, end_time)

        logger.info(
            f"LDA detector found {len(events)} potential events")

        # Save new events
        new_events = 0
        for event in events:
            # Check if similar event already exists
            existing = db.query(Event).filter(
                Event.event_name == event.event_name,
                Event.event_start == event.event_start
            ).first()

            if not existing:
                db.add(event)
                new_events += 1
                logger.info(
                    f"New event detected: {event.event_name} (confidence: {event.confidence:.2f})")
            else:
                logger.debug(f"Event already exists: {event.event_name}")

        db.commit()
        logger.info(
            f"Event detection complete: {new_events} new events saved ({len(events) - new_events} duplicates skipped)")
    except Exception as e:
        logger.error(f"Error in scheduled event detection: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("="*60)


# Initialize scheduler
scheduler = BackgroundScheduler()


def run_initial_collection():
    """Run initial data collection on application startup."""
    logger.info("#"*60)
    logger.info("# INITIAL DATA COLLECTION ON STARTUP")
    logger.info("#"*60)

    try:
        # Collect Reddit data
        logger.info("Step 1/2: Collecting Reddit data...")
        collect_reddit_data()

        # Collect Twitter data
        # logger.info("Step 2/2: Collecting Twitter data...")
        # collect_twitter_data()

        logger.info("#"*60)
        logger.info("# Initial data collection complete")
        logger.info("#"*60)
    except Exception as e:
        logger.error(f"Error in initial data collection: {e}", exc_info=True)


def start_scheduler():
    """Start the background scheduler for periodic tasks."""
    logger.info("="*60)
    logger.info("Starting background scheduler")
    logger.info("="*60)

    # Schedule Reddit collection
    scheduler.add_job(
        collect_reddit_data,
        trigger=IntervalTrigger(hours=settings.COLLECTION_INTERVAL_HOURS),
        id='collect_reddit',
        name='Collect Reddit posts',
        replace_existing=True
    )
    logger.info(
        f"✓ Scheduled Reddit collection (every {settings.COLLECTION_INTERVAL_HOURS} hours)")

    # Schedule Twitter collection
    # scheduler.add_job(
    #    collect_twitter_data,
    #    trigger=IntervalTrigger(hours=settings.COLLECTION_INTERVAL_HOURS),
    #    id='collect_twitter',
    #    name='Collect Twitter posts',
    #    replace_existing=True
    # )
    # logger.info(
    #    f"✓ Scheduled Twitter collection (every {settings.COLLECTION_INTERVAL_HOURS} hours)")

    # Schedule event detection (every 6 hours)
    scheduler.add_job(
        detect_events,
        trigger=IntervalTrigger(hours=6),
        id='detect_events',
        name='Detect economic events',
        replace_existing=True
    )
    logger.info("✓ Scheduled event detection (every 6 hours)")

    scheduler.start()
    logger.info("="*60)
    logger.info("✓ Background scheduler started successfully")
    logger.info("="*60)


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    logger.info("Background scheduler stopped")
