"""BERTopic-based event detection using topic modeling."""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import numpy as np
import scipy.sparse as sp
from bertopic import BERTopic
from bertopic.vectorizers import ClassTfidfTransformer
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.preprocessing import normalize

from app.models.post import Post
from app.models.event import Event, DetectionMethod
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class FixedClassTfidfTransformer(ClassTfidfTransformer):
    """
    Custom ClassTfidfTransformer that fixes scipy 1.13+ compatibility issue.

    This fixes the "object of type 'numpy.float64' has no len()" error
    by ensuring the diagonal values are always arrays, not scalars.
    """

    def fit(self, X, multiplier=None):
        """Fit the model with X."""
        # Count the number of documents per class
        self.doc_count = np.sum(X, axis=0)

        # Calculate the inverse document frequency
        # Add 1 to avoid division by zero
        idf = np.log((X.sum(axis=1).A1.sum() + 1) / (self.doc_count + 1))

        # Convert to array and ensure it's 1D
        if isinstance(idf, np.matrix):
            idf = np.asarray(idf).ravel()
        elif isinstance(idf, (int, float, np.number)):
            # If it's a scalar, convert to array
            idf = np.array([idf])
        else:
            idf = np.asarray(idf).ravel()

        print(
            f"[DEBUG] IDF shape: {idf.shape}, type: {type(idf)}, dtype: {idf.dtype}")

        # Ensure idf is a 1D array
        if idf.ndim == 0:
            idf = np.array([float(idf)])

        # Create diagonal matrix - ensure idf is an array
        self._idf_diag = sp.diags(idf.ravel(), offsets=0, shape=(
            len(idf), len(idf)), dtype=np.float64)

        return self


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

        logger.info(
            f"Detecting events with BERTopic from {start_time} to {end_time}")
        print(
            f"[DEBUG] Starting BERTopic detection: start={start_time}, end={end_time}, min_topic_size={min_topic_size}")

        # Get posts in time range
        posts = self.db.query(Post).filter(
            Post.created_at >= start_time,
            Post.created_at <= end_time
        ).all()

        print(f"[DEBUG] Found {len(posts)} posts in time range")

        if len(posts) < min_topic_size:
            logger.warning(f"Insufficient posts for BERTopic: {len(posts)}")
            return []

        # Prepare documents
        documents = self._prepare_documents(posts)
        print(f"[DEBUG] Prepared {len(documents)} documents")

        # Train BERTopic model
        try:
            self.model = self._train_bertopic(
                documents,
                min_topic_size=min_topic_size,
                n_gram_range=n_gram_range
            )
            print(f"[DEBUG] BERTopic model trained successfully")
        except Exception as e:
            print(f"[DEBUG] ERROR in _train_bertopic: {e}")
            import traceback
            traceback.print_exc()
            raise

        # Extract topics and create events
        events = self._create_events_from_topics(posts, documents)

        logger.info(f"Detected {len(events)} events using BERTopic")
        print(f"[DEBUG] Created {len(events)} events from topics")
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
                # Empty placeholder to maintain index alignment
                documents.append("")

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
        print(
            f"[DEBUG] _train_bertopic called with min_topic_size={min_topic_size}, n_gram_range={n_gram_range}")
        print(f"[DEBUG] n_gram_range type: {type(n_gram_range)}")
        print(
            f"[DEBUG] documents type: {type(documents)}, len: {len(documents)}")

        # Filter out empty documents
        non_empty_docs = [
            doc for doc in documents if doc and len(doc.strip()) > 0]
        print(
            f"[DEBUG] Non-empty documents: {len(non_empty_docs)} out of {len(documents)}")

        if len(non_empty_docs) < min_topic_size:
            logger.warning(
                f"Too few non-empty documents: {len(non_empty_docs)}")
            raise ValueError(
                f"Insufficient non-empty documents for clustering: {len(non_empty_docs)} < {min_topic_size}")

        # Custom vectorizer for better topic words
        print(
            f"[DEBUG] Creating CountVectorizer with ngram_range={n_gram_range}")
        vectorizer_model = CountVectorizer(
            ngram_range=n_gram_range,
            stop_words='english',
            min_df=2
        )
        print(f"[DEBUG] CountVectorizer created successfully")

        # Use our fixed ClassTfidfTransformer to avoid scipy.sparse.diags error
        print(f"[DEBUG] Creating FixedClassTfidfTransformer")
        ctfidf_model = FixedClassTfidfTransformer()
        print(f"[DEBUG] FixedClassTfidfTransformer created successfully")

        # Initialize and train BERTopic
        print(f"[DEBUG] Creating BERTopic model")
        topic_model = BERTopic(
            embedding_model=self.embedding_model,
            vectorizer_model=vectorizer_model,
            ctfidf_model=ctfidf_model,
            min_topic_size=min_topic_size,
            nr_topics="auto",
            calculate_probabilities=False,  # Faster
            verbose=False
        )
        print(f"[DEBUG] BERTopic model created, starting fit_transform")

        try:
            topics, probabilities = topic_model.fit_transform(documents)
            print(f"[DEBUG] fit_transform completed successfully")
            print(
                f"[DEBUG] topics type: {type(topics)}, shape: {getattr(topics, 'shape', 'N/A')}")
            print(f"[DEBUG] probabilities type: {type(probabilities)}")
        except Exception as e:
            print(f"[DEBUG] ERROR in fit_transform: {e}")
            import traceback
            print(f"[DEBUG] Full traceback:")
            traceback.print_exc()
            raise

        logger.info(
            f"Found {len(set(topics)) - 1} topics (excluding outliers)")
        print(f"[DEBUG] Unique topics: {set(topics)}")
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

        print(f"[DEBUG] Processing {len(topic_info)} topics")
        print(f"[DEBUG] Topic info columns: {topic_info.columns.tolist()}")
        print(f"[DEBUG] Topic info shape: {topic_info.shape}")

        events = []

        # Process each topic (skip -1 which is outliers)
        for idx, row in topic_info.iterrows():
            topic_id = row['Topic']
            print(f"[DEBUG] Processing topic {topic_id} (row {idx})")

            if topic_id == -1:  # Skip outlier topic
                print(f"[DEBUG] Skipping outlier topic -1")
                continue

            # Get posts assigned to this topic
            topic_posts = [
                posts[i] for i, t in enumerate(topics)
                if t == topic_id and i < len(posts)
            ]

            print(f"[DEBUG] Topic {topic_id}: {len(topic_posts)} posts")

            if len(topic_posts) < settings.MIN_POSTS_FOR_EVENT:
                print(
                    f"[DEBUG] Topic {topic_id}: Too few posts ({len(topic_posts)} < {settings.MIN_POSTS_FOR_EVENT}), skipping")
                continue

            # Create event
            print(f"[DEBUG] Creating event for topic {topic_id}")
            print(f"[DEBUG] Row type: {type(row)}, Row contents: {row}")
            event = self._create_event_from_topic(
                topic_id,
                topic_posts,
                row
            )

            if event:
                print(
                    f"[DEBUG] Successfully created event: {event.event_name}")
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
        print(f"[DEBUG] Getting topic words for topic {topic_id}")
        topic_representation = self.model.get_topic(topic_id)
        print(
            f"[DEBUG] Topic representation type: {type(topic_representation)}")
        print(f"[DEBUG] Topic representation: {topic_representation}")

        if isinstance(topic_representation, bool) and not topic_representation:
            print(f"[DEBUG] Invalid topic {topic_id}, skipping")
            return None

        topic_words = [word for word, _ in topic_representation[:10]]
        print(f"[DEBUG] Topic words extracted: {topic_words}")
        print(f"[DEBUG] Topic words type: {type(topic_words)}")

        # Generate event name from top words
        print(f"[DEBUG] Generating event name from {len(topic_words)} words")
        event_name = self._generate_event_name(topic_words)
        print(f"[DEBUG] Generated event name: {event_name}")

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
        print(f"[DEBUG] _generate_event_name called with: {topic_words}")
        print(f"[DEBUG] topic_words type: {type(topic_words)}")

        # Ensure topic_words is a list
        if not isinstance(topic_words, list):
            print(
                f"[DEBUG] Converting topic_words to list (was {type(topic_words)})")
            topic_words = list(topic_words) if hasattr(
                topic_words, '__iter__') else [str(topic_words)]

        print(f"[DEBUG] topic_words length: {len(topic_words)}")

        # Take top 3 words and capitalize
        if len(topic_words) >= 3:
            print(f"[DEBUG] Using top 3 words")
            name = f"{topic_words[0].title()}, {topic_words[1].title()}, {topic_words[2].title()}"
        elif len(topic_words) >= 1:
            print(f"[DEBUG] Using available words (less than 3)")
            name = ", ".join(w.title() for w in topic_words[:2])
        else:
            print(f"[DEBUG] No words available, using default")
            name = "Unknown Topic"

        print(f"[DEBUG] Generated name: {name}")
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
