"""Keyword-based spike detection for economic events."""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
from collections import defaultdict, Counter
import numpy as np
from sqlalchemy.orm import Session
from app.models.post import Post
from app.models.event import Event, DetectionMethod
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class KeywordSpikeDetector:
    """Detect events using temporal spike analysis of keyword frequencies."""
    
    def __init__(self, db: Session):
        """
        Initialize spike detector.
        
        Args:
            db: Database session
        """
        self.db = db
        self.time_window_hours = settings.TIME_WINDOW_HOURS
        self.spike_threshold = settings.SPIKE_THRESHOLD  # Standard deviations
        self.min_posts = settings.MIN_POSTS_FOR_EVENT
    
    def detect_events(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        keywords: List[str] = None
    ) -> List[Event]:
        """
        Detect events based on keyword frequency spikes.
        
        Args:
            start_time: Start of analysis period (default: 7 days ago)
            end_time: End of analysis period (default: now)
            keywords: Keywords to analyze (default: from config)
            
        Returns:
            List of detected Event objects
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(days=7)
        if keywords is None:
            keywords = settings.ECONOMIC_KEYWORDS
        
        logger.info(f"Detecting keyword spikes from {start_time} to {end_time}")
        
        detected_events = []
        
        for keyword in keywords:
            events = self._detect_keyword_spikes(
                keyword,
                start_time,
                end_time
            )
            detected_events.extend(events)
        
        logger.info(f"Detected {len(detected_events)} events from keyword spikes")
        return detected_events
    
    def _detect_keyword_spikes(
        self,
        keyword: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Event]:
        """
        Detect spikes for a specific keyword.
        
        Args:
            keyword: Keyword to analyze
            start_time: Start time
            end_time: End time
            
        Returns:
            List of detected events
        """
        # Get posts matching this keyword
        posts = self.db.query(Post).filter(
            Post.matched_keyword.ilike(f"%{keyword}%"),
            Post.created_at >= start_time,
            Post.created_at <= end_time
        ).order_by(Post.created_at).all()
        
        if len(posts) < self.min_posts:
            logger.debug(f"Insufficient posts for keyword '{keyword}': {len(posts)}")
            return []
        
        # Create time series of post counts
        time_series = self._create_time_series(posts, start_time, end_time)
        
        # Detect spikes in the time series
        spike_windows = self._find_spikes(time_series)
        
        # Create events from spike windows
        events = []
        for window_start, window_end, spike_score in spike_windows:
            event = self._create_event_from_spike(
                keyword,
                posts,
                window_start,
                window_end,
                spike_score
            )
            if event:
                events.append(event)
        
        return events
    
    def _create_time_series(
        self,
        posts: List[Post],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[datetime, int]:
        """
        Create hourly time series of post counts.
        
        Args:
            posts: List of posts
            start_time: Start time
            end_time: End time
            
        Returns:
            Dictionary mapping hour timestamps to post counts
        """
        # Initialize time series with zeros
        current = start_time.replace(minute=0, second=0, microsecond=0)
        time_series = {}
        
        while current <= end_time:
            time_series[current] = 0
            current += timedelta(hours=1)
        
        # Count posts per hour
        for post in posts:
            hour = post.created_at.replace(minute=0, second=0, microsecond=0)
            if hour in time_series:
                time_series[hour] += 1
        
        return time_series
    
    def _find_spikes(
        self,
        time_series: Dict[datetime, int]
    ) -> List[Tuple[datetime, datetime, float]]:
        """
        Find spike windows in time series using z-score.
        
        Args:
            time_series: Time series data
            
        Returns:
            List of (window_start, window_end, spike_score) tuples
        """
        if not time_series:
            return []
        
        # Convert to sorted lists
        times = sorted(time_series.keys())
        counts = [time_series[t] for t in times]
        
        # Calculate rolling statistics
        window_size = self.time_window_hours
        spikes = []
        
        for i in range(len(counts) - window_size + 1):
            window_counts = counts[i:i + window_size]
            window_sum = sum(window_counts)
            
            # Calculate z-score for this window
            mean = np.mean(counts)
            std = np.std(counts)
            
            if std > 0:
                z_score = (window_sum / window_size - mean) / std
                
                # Check if this is a spike
                if z_score >= self.spike_threshold and window_sum >= self.min_posts:
                    window_start = times[i]
                    window_end = times[i + window_size - 1]
                    spikes.append((window_start, window_end, z_score))
        
        # Merge overlapping spikes
        merged_spikes = self._merge_overlapping_spikes(spikes)
        
        return merged_spikes
    
    def _merge_overlapping_spikes(
        self,
        spikes: List[Tuple[datetime, datetime, float]]
    ) -> List[Tuple[datetime, datetime, float]]:
        """
        Merge overlapping spike windows.
        
        Args:
            spikes: List of (start, end, score) tuples
            
        Returns:
            Merged list of spikes
        """
        if not spikes:
            return []
        
        # Sort by start time
        sorted_spikes = sorted(spikes, key=lambda x: x[0])
        merged = [sorted_spikes[0]]
        
        for current in sorted_spikes[1:]:
            previous = merged[-1]
            
            # Check if overlapping
            if current[0] <= previous[1]:
                # Merge: extend end time, take max score
                merged[-1] = (
                    previous[0],
                    max(previous[1], current[1]),
                    max(previous[2], current[2])
                )
            else:
                merged.append(current)
        
        return merged
    
    def _create_event_from_spike(
        self,
        keyword: str,
        all_posts: List[Post],
        window_start: datetime,
        window_end: datetime,
        spike_score: float
    ) -> Event:
        """
        Create an Event object from a detected spike.
        
        Args:
            keyword: The keyword that spiked
            all_posts: All posts for this keyword
            window_start: Spike window start
            window_end: Spike window end
            spike_score: Z-score of the spike
            
        Returns:
            Event object (not yet added to database)
        """
        # Get posts in this window
        window_posts = [
            p for p in all_posts
            if window_start <= p.created_at <= window_end
        ]
        
        if len(window_posts) < self.min_posts:
            return None
        
        # Calculate metrics
        post_ids = [p.post_id for p in window_posts]
        reddit_count = sum(1 for p in window_posts if p.source == 'reddit')
        twitter_count = sum(1 for p in window_posts if p.source == 'twitter')
        
        # Calculate total engagement
        total_engagement = 0
        for p in window_posts:
            if p.source == 'reddit':
                total_engagement += (p.score or 0) + (p.num_comments or 0)
            else:  # twitter
                total_engagement += (p.like_count or 0) + (p.retweet_count or 0)
        
        # Find peak time (hour with most posts)
        hour_counts = Counter(
            p.created_at.replace(minute=0, second=0, microsecond=0)
            for p in window_posts
        )
        peak_time = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else window_start
        
        # Create event
        event = Event(
            event_name=f"{keyword.upper()} Activity Spike",
            event_type=keyword.lower().replace(" ", "_"),
            detection_method=DetectionMethod.KEYWORD_SPIKE,
            confidence_score=min(spike_score / 10.0, 1.0),  # Normalize to 0-1
            description=f"Detected {len(window_posts)} posts about '{keyword}' (z-score: {spike_score:.2f})",
            keywords=[keyword],
            post_ids=post_ids,
            num_posts=len(window_posts),
            reddit_count=reddit_count,
            twitter_count=twitter_count,
            event_start=window_start,
            event_end=window_end,
            peak_time=peak_time,
            total_engagement=total_engagement
        )
        
        logger.info(f"Created event: {event.event_name} ({len(window_posts)} posts)")
        return event
    
    def get_keyword_trends(
        self,
        hours_back: int = 168  # 7 days
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get trend data for all economic keywords.
        
        Args:
            hours_back: How many hours of history to analyze
            
        Returns:
            Dictionary mapping keywords to their trend data
        """
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours_back)
        
        trends = {}
        
        for keyword in settings.ECONOMIC_KEYWORDS:
            posts = self.db.query(Post).filter(
                Post.matched_keyword.ilike(f"%{keyword}%"),
                Post.created_at >= start_time,
                Post.created_at <= end_time
            ).all()
            
            time_series = self._create_time_series(posts, start_time, end_time)
            
            # Convert to list format
            trend_data = [
                {'timestamp': ts.isoformat(), 'count': count}
                for ts, count in sorted(time_series.items())
            ]
            
            trends[keyword] = trend_data
        
        return trends
