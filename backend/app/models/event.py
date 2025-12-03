"""Database models for detected economic events."""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, JSON, Enum
from sqlalchemy.sql import func
import enum
from app.db.session import Base


class DetectionMethod(str, enum.Enum):
    """Event detection method types."""
    KEYWORD_SPIKE = "keyword_spike"
    BERTOPIC = "bertopic"
    LDA = "lda"
    MANUAL = "manual"


class Event(Base):
    """Model for storing detected economic events."""

    __tablename__ = "events"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Event identification
    event_name = Column(String(200), nullable=False)
    # e.g., 'inflation', 'fed_announcement'
    event_type = Column(String(100), nullable=True, index=True)

    # Detection metadata
    detection_method = Column(
        Enum(DetectionMethod),
        nullable=False,
        index=True
    )
    confidence_score = Column(Float, nullable=True)  # 0-1 confidence

    # Event description
    description = Column(Text, nullable=True)
    keywords = Column(JSON, nullable=True)  # List of associated keywords

    # Associated posts
    post_ids = Column(JSON, nullable=False)  # List of post IDs in this event
    num_posts = Column(Integer, nullable=False)

    # Sources
    reddit_count = Column(Integer, default=0)
    twitter_count = Column(Integer, default=0)

    # Temporal information
    event_start = Column(DateTime(timezone=True), nullable=False, index=True)
    event_end = Column(DateTime(timezone=True), nullable=False)
    peak_time = Column(DateTime(timezone=True), nullable=True)

    # Engagement metrics
    total_engagement = Column(Integer, default=0)  # Sum of scores/likes
    avg_sentiment = Column(Float, nullable=True)  # -1 to 1

    # Clustering metadata (for BERTopic/LDA)
    topic_id = Column(Integer, nullable=True)
    topic_words = Column(JSON, nullable=True)  # Top words for this topic

    # Timestamps
    detected_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Event {self.id}: {self.event_name} ({self.detection_method})>"

    def to_dict(self, include_summary: bool = False, db_session=None):
        """Convert model to dictionary.

        Args:
            include_summary: Whether to include the latest summary if available
            db_session: Database session for fetching summary (required if include_summary=True)
        """
        result = {
            'id': self.id,
            'event_name': self.event_name,
            'event_type': self.event_type,
            'detection_method': self.detection_method.value if self.detection_method else None,
            'confidence_score': self.confidence_score,
            'description': self.description,
            'keywords': self.keywords,
            'num_posts': self.num_posts,
            'reddit_count': self.reddit_count,
            'twitter_count': self.twitter_count,
            'event_start': self.event_start.isoformat() if self.event_start else None,
            'event_end': self.event_end.isoformat() if self.event_end else None,
            'total_engagement': self.total_engagement,
            'avg_sentiment': self.avg_sentiment,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
        }

        # Optionally include the latest summary
        if include_summary and db_session:
            summary = db_session.query(EventSummary).filter(
                EventSummary.event_id == self.id
            ).order_by(EventSummary.created_at.desc()).first()

            if summary:
                result['summary'] = summary.to_dict()

        return result


class EventSummary(Base):
    """Model for storing event summaries."""

    __tablename__ = "event_summaries"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, nullable=False, index=True)

    # Summary content
    summary_text = Column(Text, nullable=False)
    # 'extractive', 'bart', 't5', etc.
    summary_method = Column(String(50), nullable=False)

    # Evaluation metrics
    rouge_1 = Column(Float, nullable=True)
    rouge_2 = Column(Float, nullable=True)
    rouge_l = Column(Float, nullable=True)
    bleu_score = Column(Float, nullable=True)

    # Metadata
    num_source_posts = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<EventSummary {self.id} for Event {self.event_id}>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'summary_text': self.summary_text,
            'summary_method': self.summary_method,
            'rouge_1': self.rouge_1,
            'rouge_2': self.rouge_2,
            'rouge_l': self.rouge_l,
            'bleu_score': self.bleu_score,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
