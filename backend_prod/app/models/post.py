"""Database models for posts from Reddit and Twitter."""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Boolean, Index
from sqlalchemy.sql import func
from app.db.session import Base


class Post(Base):
    """Model for storing social media posts (Reddit & Twitter)."""

    __tablename__ = "posts"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Source identification
    source = Column(String(20), nullable=False,
                    index=True)  # 'reddit' or 'twitter'
    post_id = Column(String(100), unique=True, nullable=False, index=True)

    # Content
    title = Column(String(1000), nullable=True)  # Reddit posts have titles
    text = Column(Text, nullable=False)

    # Author information
    author = Column(String(100), nullable=True)
    author_id = Column(String(100), nullable=True)  # Twitter author ID

    # Reddit-specific fields
    subreddit = Column(String(50), nullable=True, index=True)
    score = Column(Integer, nullable=True)
    upvote_ratio = Column(Float, nullable=True)
    num_comments = Column(Integer, nullable=True)
    is_self = Column(Boolean, nullable=True)
    link_flair_text = Column(String(100), nullable=True)

    # Twitter-specific fields
    retweet_count = Column(Integer, nullable=True)
    reply_count = Column(Integer, nullable=True)
    like_count = Column(Integer, nullable=True)
    quote_count = Column(Integer, nullable=True)

    # Common fields
    matched_keyword = Column(String(100), nullable=True, index=True)
    url = Column(String(2000), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, index=True)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())

    # Indexes for common queries
    __table_args__ = (
        Index('idx_source_created', 'source', 'created_at'),
        Index('idx_keyword_created', 'matched_keyword', 'created_at'),
    )

    def __repr__(self):
        return f"<Post {self.source}:{self.post_id}>"

    def to_dict(self):
        """Convert model to dictionary."""
        return {
            'id': self.id,
            'source': self.source,
            'post_id': self.post_id,
            'title': self.title,
            'text': self.text,
            'author': self.author,
            'subreddit': self.subreddit,
            'matched_keyword': self.matched_keyword,
            'url': self.url,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'collected_at': self.collected_at.isoformat() if self.collected_at else None,
            # Include all fields for data export
            'author_id': self.author_id,
            'score': self.score,
            'upvote_ratio': self.upvote_ratio,
            'num_comments': self.num_comments,
            'is_self': self.is_self,
            'link_flair_text': self.link_flair_text,
            'retweet_count': self.retweet_count,
            'reply_count': self.reply_count,
            'like_count': self.like_count,
            'quote_count': self.quote_count,
        }
