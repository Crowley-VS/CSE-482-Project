"""BERTopic-based event detection using topic modeling."""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import numpy as np
from bertopic import BERTopic
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer

from app.models.post import Post
from app.models.event import Event, DetectionMethod
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BERTopicDetector:
    """Detect events using BERTopic topic modeling."""
    
    def __init__(self, db: Session):
        """
        Initialize BERTopic detector.
        
        Args:
            db: Database session
        """
        self.db = db
        self.model: Optional[BERTopic] = None
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
    def detect_events(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        min_topic_size: int = 10,
        n_gram_range: tuple = (1, 2)
    ) -> List[Event]:
        """
        Detect events using BERTopic clustering.
        
        Args:
            start_time: Start of analysis period (default: 7 days ago)
            end_time: End of analysis period (default: now)
            min_topic_size: Minimum posts per topic
            n_gram_range: N-gram range for topic words
            
        Returns:
            List of detected Event objects
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(days=7)
        
        logger.info(f"Detecting events with BERTopic from {start_time} to {end_time}")
        
        # Get posts in time range
        posts = self.db.query(Post).filter(
            Post.created_at >= start_time,
            Post.created_at <= end_time
        ).all()
        
        if len(posts) < min_topic_size:
            logger.warning(f"Insufficient posts for BERTopic: {len(posts)}")
            return []
        
        # Prepare documents
        documents = self._prepare_documents(posts)
        
        # Train BERTopic model
        self.model = self._train_bertopic(
            documents,
            min_topic_size=min_topic_size,
            n_gram_range=n_gram_range
        )
        
        # Extract topics and create events
        events = self._create_events_from_topics(posts, documents)
        
        logger.info(f"Detected {len(events)} events using BERTopic")
        return events
    
    def _prepare_documents(self, posts: List[Post]) -> List[str]:
        """
        Prepare text documents from posts.
        
        Args:
            posts: List of posts
            
        Returns:
            List of text documents
        """
        documents = []
        
        for post in posts:
            # Combine title and text for Reddit, just text for Twitter
            if post.source == 'reddit' and post.title:
                doc = f"{post.title}. {post.text}"
            else:
                doc = post.text
            
            # Clean and validate
            if doc and len(doc.strip()) > 10:
                documents.append(doc.strip())
            else:
                documents.append("")  # Empty placeholder to maintain index alignment
        
        return documents
    
    def _train_bertopic(
        self,
        documents: List[str],
        min_topic_size: int = 10,
        n_gram_range: tuple = (1, 2)
    ) -> BERTopic:
        """
        Train BERTopic model on documents.
        
        Args:
            documents: List of text documents
            min_topic_size: Minimum cluster size
            n_gram_range: N-gram range for vocabulary
            
        Returns:
            Trained BERTopic model
        """
        logger.info(f"Training BERTopic on {len(documents)} documents")
        
        # Custom vectorizer for better topic words
        vectorizer_model = CountVectorizer(
            ngram_range=n_gram_range,
            stop_words='english',
            min_df=2
        )
        
        # Initialize and train BERTopic
        topic_model = BERTopic(
            embedding_model=self.embedding_model,
            vectorizer_model=vectorizer_model,
            min_topic_size=min_topic_size,
            nr_topics="auto",
            calculate_probabilities=False,  # Faster
            verbose=False
        )
        
        topics, probabilities = topic_model.fit_transform(documents)
        
        logger.info(f"Found {len(set(topics)) - 1} topics (excluding outliers)")
        return topic_model
    
    def _create_events_from_topics(
        self,
        posts: List[Post],
        documents: List[str]
    ) -> List[Event]:
        """
        Create Event objects from discovered topics.
        
        Args:
            posts: Original posts
            documents: Processed documents
            
        Returns:
            List of Event objects
        """
        if self.model is None:
            return []
        
        # Get topic assignments
        topics = self.model.topics_
        topic_info = self.model.get_topic_info()
        
        events = []
        
        # Process each topic (skip -1 which is outliers)
        for _, row in topic_info.iterrows():
            topic_id = row['Topic']
            
            if topic_id == -1:  # Skip outlier topic
                continue
            
            # Get posts assigned to this topic
            topic_posts = [
                posts[i] for i, t in enumerate(topics)
                if t == topic_id and i < len(posts)
            ]
            
            if len(topic_posts) < settings.MIN_POSTS_FOR_EVENT:
                continue
            
            # Create event
            event = self._create_event_from_topic(
                topic_id,
                topic_posts,
                row
            )
            
            if event:
                events.append(event)
        
        return events
    
    def _create_event_from_topic(
        self,
        topic_id: int,
        posts: List[Post],
        topic_info: Any
    ) -> Optional[Event]:
        """
        Create an Event from a BERTopic topic.
        
        Args:
            topic_id: Topic ID
            posts: Posts in this topic
            topic_info: Topic information from BERTopic
            
        Returns:
            Event object or None
        """
        if not posts:
            return None
        
        # Get topic words
        topic_words = [word for word, _ in self.model.get_topic(topic_id)[:10]]
        
        # Generate event name from top words
        event_name = self._generate_event_name(topic_words)
        
        # Calculate temporal bounds
        post_times = [p.created_at for p in posts]
        event_start = min(post_times)
        event_end = max(post_times)
        
        # Calculate metrics
        post_ids = [p.post_id for p in posts]
        reddit_count = sum(1 for p in posts if p.source == 'reddit')
        twitter_count = sum(1 for p in posts if p.source == 'twitter')
        
        # Engagement
        total_engagement = 0
        for p in posts:
            if p.source == 'reddit':
                total_engagement += (p.score or 0) + (p.num_comments or 0)
            else:
                total_engagement += (p.like_count or 0) + (p.retweet_count or 0)
        
        # Confidence based on topic size and coherence
        confidence_score = min(len(posts) / 100.0, 1.0)
        
        event = Event(
            event_name=event_name,
            event_type="topic_cluster",
            detection_method=DetectionMethod.BERTOPIC,
            confidence_score=confidence_score,
            description=f"Topic cluster with {len(posts)} posts",
            keywords=topic_words[:5],
            post_ids=post_ids,
            num_posts=len(posts),
            reddit_count=reddit_count,
            twitter_count=twitter_count,
            event_start=event_start,
            event_end=event_end,
            peak_time=event_start,  # Could be refined
            total_engagement=total_engagement,
            topic_id=topic_id,
            topic_words=topic_words
        )
        
        logger.info(f"Created topic event: {event_name} ({len(posts)} posts)")
        return event
    
    def _generate_event_name(self, topic_words: List[str]) -> str:
        """
        Generate a readable event name from topic words.
        
        Args:
            topic_words: Top words for the topic
            
        Returns:
            Event name string
        """
        # Take top 3 words and capitalize
        if len(topic_words) >= 3:
            name = f"{topic_words[0].title()}, {topic_words[1].title()}, {topic_words[2].title()}"
        elif len(topic_words) >= 1:
            name = ", ".join(w.title() for w in topic_words[:2])
        else:
            name = "Unknown Topic"
        
        return f"Discussion: {name}"
    
    def get_topic_over_time(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """
        Get topic evolution over time.
        
        Args:
            start_time: Start time
            end_time: End time
            
        Returns:
            Dictionary with topic evolution data
        """
        if self.model is None:
            logger.warning("Model not trained yet")
            return {}
        
        posts = self.db.query(Post).filter(
            Post.created_at >= start_time,
            Post.created_at <= end_time
        ).all()
        
        documents = self._prepare_documents(posts)
        timestamps = [p.created_at for p in posts]
        
        # Get topics over time
        topics_over_time = self.model.topics_over_time(
            documents,
            timestamps,
            nr_bins=20
        )
        
        return topics_over_time.to_dict('records')
