"""LDA-based event detection using topic modeling."""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
import numpy as np
from gensim import corpora, models
from gensim.parsing.preprocessing import STOPWORDS
from gensim.utils import simple_preprocess

from app.models.post import Post
from app.models.event import Event, DetectionMethod
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class LDADetector:
    """Detect events using Latent Dirichlet Allocation (LDA) topic modeling."""

    def __init__(self, db: Session):
        """
        Initialize LDA detector.

        Args:
            db: Database session
        """
        self.db = db
        self.lda_model: Optional[models.LdaMulticore] = None
        self.dictionary: Optional[corpora.Dictionary] = None
        self.corpus = None

    def detect_events(
        self,
        start_time: datetime = None,
        end_time: datetime = None,
        num_topics: int = 10,
        passes: int = 10,
        min_posts_per_topic: int = 5
    ) -> List[Event]:
        """
        Detect events using LDA topic modeling.

        Args:
            start_time: Start of analysis period (default: 7 days ago)
            end_time: End of analysis period (default: now)
            num_topics: Number of topics to discover
            passes: Number of training passes
            min_posts_per_topic: Minimum posts to create an event

        Returns:
            List of detected Event objects
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        logger.info(
            f"Detecting events with LDA from {start_time} to {end_time}")

        # Get posts in time range
        posts = self.db.query(Post).filter(
            Post.created_at >= start_time,
            Post.created_at <= end_time
        ).all()

        if len(posts) < num_topics:
            logger.warning(f"Insufficient posts for LDA: {len(posts)}")
            return []

        # Prepare documents
        processed_docs = self._preprocess_documents(posts)

        # Train LDA model
        self._train_lda(processed_docs, num_topics=num_topics, passes=passes)

        # Assign posts to topics
        topic_assignments = self._assign_posts_to_topics(processed_docs)

        # Create events from topics
        events = self._create_events_from_topics(
            posts,
            topic_assignments,
            min_posts_per_topic
        )

        logger.info(f"Detected {len(events)} events using LDA")
        return events

    def _preprocess_documents(self, posts: List[Post]) -> List[List[str]]:
        """
        Preprocess posts into tokenized documents.

        Args:
            posts: List of posts

        Returns:
            List of tokenized documents
        """
        processed = []

        for post in posts:
            # Get text
            if post.source == 'reddit' and post.title:
                text = f"{post.title} {post.text}"
            else:
                text = post.text

            if not text:
                processed.append([])
                continue

            # Tokenize and clean
            tokens = simple_preprocess(text, deacc=True)

            # Remove stopwords and short tokens
            tokens = [
                token for token in tokens
                if token not in STOPWORDS and len(token) > 3
            ]

            processed.append(tokens)

        return processed

    def _train_lda(
        self,
        processed_docs: List[List[str]],
        num_topics: int = 10,
        passes: int = 10
    ):
        """
        Train LDA model.

        Args:
            processed_docs: Preprocessed tokenized documents
            num_topics: Number of topics
            passes: Training passes
        """
        logger.info(f"Training LDA with {num_topics} topics")

        # Create dictionary
        self.dictionary = corpora.Dictionary(processed_docs)

        # Filter extremes
        self.dictionary.filter_extremes(
            no_below=2,  # Minimum document frequency
            no_above=0.5,  # Maximum document frequency
            keep_n=1000  # Keep top N most frequent
        )

        # Create corpus (bag of words)
        self.corpus = [
            self.dictionary.doc2bow(doc)
            for doc in processed_docs
        ]

        # Train LDA
        self.lda_model = models.LdaMulticore(
            corpus=self.corpus,
            id2word=self.dictionary,
            num_topics=num_topics,
            passes=passes,
            workers=2,
            random_state=42,
            per_word_topics=True
        )

        logger.info("LDA training complete")

    def _assign_posts_to_topics(
        self,
        processed_docs: List[List[str]]
    ) -> List[int]:
        """
        Assign each document to its dominant topic.

        Args:
            processed_docs: Preprocessed documents

        Returns:
            List of topic IDs (one per document)
        """
        if self.lda_model is None or self.dictionary is None:
            return []

        topic_assignments = []

        for doc in processed_docs:
            if not doc:
                topic_assignments.append(-1)  # No topic for empty docs
                continue

            # Get topic distribution for this document
            bow = self.dictionary.doc2bow(doc)
            topic_dist = self.lda_model.get_document_topics(bow)

            if topic_dist:
                # Get dominant topic (highest probability)
                dominant_topic = max(topic_dist, key=lambda x: x[1])[0]
                topic_assignments.append(dominant_topic)
            else:
                topic_assignments.append(-1)

        return topic_assignments

    def _create_events_from_topics(
        self,
        posts: List[Post],
        topic_assignments: List[int],
        min_posts: int
    ) -> List[Event]:
        """
        Create Event objects from LDA topics.

        Args:
            posts: Original posts
            topic_assignments: Topic ID for each post
            min_posts: Minimum posts to create an event

        Returns:
            List of Event objects
        """
        if self.lda_model is None:
            return []

        # Group posts by topic
        topic_posts: Dict[int, List[Post]] = {}
        for post, topic_id in zip(posts, topic_assignments):
            if topic_id >= 0:  # Skip unassigned
                if topic_id not in topic_posts:
                    topic_posts[topic_id] = []
                topic_posts[topic_id].append(post)

        events = []

        # Create event for each topic
        for topic_id, topic_post_list in topic_posts.items():
            if len(topic_post_list) < min_posts:
                continue

            event = self._create_event_from_topic(topic_id, topic_post_list)
            if event:
                events.append(event)

        return events

    def _create_event_from_topic(
        self,
        topic_id: int,
        posts: List[Post]
    ) -> Optional[Event]:
        """
        Create an Event from an LDA topic.

        Args:
            topic_id: LDA topic ID
            posts: Posts assigned to this topic

        Returns:
            Event object or None
        """
        if not posts or self.lda_model is None:
            return None

        # Get top words for this topic
        topic_words = self._get_topic_words(topic_id, top_n=10)

        # Generate event name
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
                total_engagement += (p.like_count or 0) + \
                    (p.retweet_count or 0)

        # Confidence based on coherence and size
        coherence = self._calculate_topic_coherence(topic_id)
        confidence_score = min((coherence + len(posts) / 100.0) / 2, 1.0)

        event = Event(
            event_name=event_name,
            event_type="lda_topic",
            detection_method=DetectionMethod.LDA,
            confidence_score=confidence_score,
            description=f"LDA topic cluster with {len(posts)} posts",
            keywords=[w for w, _ in topic_words[:5]],
            post_ids=post_ids,
            num_posts=len(posts),
            reddit_count=reddit_count,
            twitter_count=twitter_count,
            event_start=event_start,
            event_end=event_end,
            peak_time=event_start,
            total_engagement=total_engagement,
            topic_id=topic_id,
            topic_words=[w for w, _ in topic_words]
        )

        logger.info(f"Created LDA event: {event_name} ({len(posts)} posts)")
        return event

    def _get_topic_words(
        self,
        topic_id: int,
        top_n: int = 10
    ) -> List[Tuple[str, float]]:
        """
        Get top words for a topic.

        Args:
            topic_id: Topic ID
            top_n: Number of top words

        Returns:
            List of (word, probability) tuples
        """
        if self.lda_model is None:
            return []

        return self.lda_model.show_topic(topic_id, topn=top_n)

    def _calculate_topic_coherence(self, topic_id: int) -> float:
        """
        Calculate simple coherence score for a topic.

        Args:
            topic_id: Topic ID

        Returns:
            Coherence score (0-1)
        """
        # Simplified coherence: average of top word probabilities
        topic_words = self._get_topic_words(topic_id, top_n=5)
        if not topic_words:
            return 0.0

        avg_prob = np.mean([prob for _, prob in topic_words])
        return float(avg_prob)

    def _generate_event_name(
        self,
        topic_words: List[Tuple[str, float]]
    ) -> str:
        """
        Generate readable event name from topic words.

        Args:
            topic_words: List of (word, probability) tuples

        Returns:
            Event name string
        """
        if len(topic_words) >= 3:
            words = [w.title() for w, _ in topic_words[:3]]
            name = ", ".join(words)
        elif len(topic_words) >= 1:
            words = [w.title() for w, _ in topic_words[:2]]
            name = ", ".join(words)
        else:
            name = "Unknown Topic"

        return f"Topic: {name}"

    def get_topic_distribution(self, text: str) -> List[Tuple[int, float]]:
        """
        Get topic distribution for a new text.

        Args:
            text: Input text

        Returns:
            List of (topic_id, probability) tuples
        """
        if self.lda_model is None or self.dictionary is None:
            return []

        # Preprocess
        tokens = simple_preprocess(text, deacc=True)
        tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 3]

        # Get distribution
        bow = self.dictionary.doc2bow(tokens)
        return self.lda_model.get_document_topics(bow)

    def print_topics(self, num_words: int = 10):
        """
        Print all discovered topics.

        Args:
            num_words: Number of words per topic
        """
        if self.lda_model is None:
            logger.warning("LDA model not trained")
            return

        logger.info("Discovered LDA Topics:")
        for idx in range(self.lda_model.num_topics):
            words = self._get_topic_words(idx, top_n=num_words)
            word_str = ", ".join([f"{w}({p:.3f})" for w, p in words])
            logger.info(f"Topic {idx}: {word_str}")
