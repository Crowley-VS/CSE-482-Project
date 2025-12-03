"""ChatGPT-based event summarization using OpenAI API."""
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import openai

from app.models.event import Event, EventSummary
from app.models.post import Post
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ChatGPTSummarizer:
    """Generate event summaries using ChatGPT."""

    def __init__(self, db: Session):
        """
        Initialize ChatGPT summarizer.

        Args:
            db: Database session
        """
        self.db = db
        self.client = None

        # Initialize OpenAI client if API key is available
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_api_key_here":
            openai.api_key = settings.OPENAI_API_KEY
            self.client = openai
        else:
            logger.warning(
                "OpenAI API key not configured. ChatGPT summarization will not be available.")

    def generate_summary(
        self,
        event: Event,
        max_posts: int = 50,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7
    ) -> Optional[EventSummary]:
        """
        Generate a summary for an event using ChatGPT.

        Args:
            event: Event to summarize
            max_posts: Maximum number of posts to include in context
            model: OpenAI model to use (gpt-3.5-turbo, gpt-4, etc.)
            temperature: Creativity parameter (0.0-1.0)

        Returns:
            EventSummary object or None if generation fails
        """
        if not self.client:
            logger.error(
                "OpenAI client not initialized. Check API key configuration.")
            return None

        try:
            # Get posts associated with the event
            posts = self._get_event_posts(event, max_posts)

            if not posts:
                logger.warning(f"No posts found for event {event.id}")
                return None

            # Prepare prompt
            prompt = self._create_summary_prompt(event, posts)

            # Call ChatGPT API
            logger.info(
                f"Generating ChatGPT summary for event {event.id} using {model}")

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert financial analyst and journalist. Your task is to create concise, informative summaries of economic events based on social media discussions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=temperature,
                max_tokens=500
            )

            summary_text = response.choices[0].message.content.strip()

            # Create EventSummary object
            summary = EventSummary(
                event_id=event.id,
                summary_text=summary_text,
                summary_method=f"chatgpt_{model}",
                num_source_posts=len(posts)
            )

            # Save to database
            self.db.add(summary)
            self.db.commit()
            self.db.refresh(summary)

            logger.info(f"Successfully generated summary for event {event.id}")
            return summary

        except Exception as e:
            logger.error(
                f"Error generating ChatGPT summary for event {event.id}: {e}")
            self.db.rollback()
            return None

    def batch_generate_summaries(
        self,
        event_ids: Optional[List[int]] = None,
        regenerate: bool = False,
        **kwargs
    ) -> Dict[str, any]:
        """
        Generate summaries for multiple events.

        Args:
            event_ids: List of event IDs to summarize (None = all events)
            regenerate: Whether to regenerate summaries for events that already have them
            **kwargs: Additional arguments passed to generate_summary

        Returns:
            Dictionary with results
        """
        query = self.db.query(Event)

        if event_ids:
            query = query.filter(Event.id.in_(event_ids))

        events = query.all()

        results = {
            "total_events": len(events),
            "summaries_generated": 0,
            "summaries_skipped": 0,
            "errors": 0
        }

        for event in events:
            # Check if summary already exists
            existing_summary = self.db.query(EventSummary).filter(
                EventSummary.event_id == event.id
            ).filter(
                EventSummary.summary_method.like("chatgpt_%")
            ).first()

            if existing_summary and not regenerate:
                logger.info(
                    f"Skipping event {event.id} - summary already exists")
                results["summaries_skipped"] += 1
                continue

            # Generate summary
            summary = self.generate_summary(event, **kwargs)

            if summary:
                results["summaries_generated"] += 1
            else:
                results["errors"] += 1

        return results

    def _get_event_posts(self, event: Event, max_posts: int) -> List[Post]:
        """
        Get posts associated with an event.

        Args:
            event: Event object
            max_posts: Maximum posts to retrieve

        Returns:
            List of Post objects
        """
        if not event.post_ids:
            return []

        # Get posts by IDs, limited to max_posts
        post_ids_to_fetch = event.post_ids[:max_posts]

        posts = self.db.query(Post).filter(
            Post.post_id.in_(post_ids_to_fetch)
        ).all()

        return posts

    def _create_summary_prompt(self, event: Event, posts: List[Post]) -> str:
        """
        Create a prompt for ChatGPT summarization.

        Args:
            event: Event object
            posts: List of Post objects

        Returns:
            Formatted prompt string
        """
        # Start with event context
        prompt = f"""I need you to create a comprehensive summary of an economic event detected from social media.

Event Name: {event.event_name}
Event Type: {event.event_type or 'Not specified'}
Time Period: {event.event_start.strftime('%Y-%m-%d %H:%M')} to {event.event_end.strftime('%Y-%m-%d %H:%M')}
Number of Posts: {event.num_posts}
Keywords: {', '.join(event.keywords) if event.keywords else 'None'}

Below are sample posts discussing this event:

"""

        # Add post content
        # Limit to first 20 posts for context
        for i, post in enumerate(posts[:20], 1):
            source = post.source.upper()

            if post.source == 'reddit' and post.title:
                prompt += f"{i}. [{source}] Title: {post.title}\n   Content: {post.text[:300]}...\n\n"
            else:
                prompt += f"{i}. [{source}] {post.text[:300]}...\n\n"

        # Add instructions
        prompt += """
Please create a concise summary (3-5 paragraphs) that:
1. Explains what this economic event is about
2. Highlights the key concerns or points being discussed
3. Mentions any specific data, dates, or figures mentioned
4. Captures the overall sentiment and public reaction
5. Provides context about why this matters economically

Write in a professional, journalistic style suitable for a financial news brief."""

        return prompt


def generate_event_summary(
    db: Session,
    event_id: int,
    model: str = "gpt-3.5-turbo",
    regenerate: bool = False
) -> Optional[EventSummary]:
    """
    Convenience function to generate a summary for a single event.

    Args:
        db: Database session
        event_id: Event ID to summarize
        model: OpenAI model to use
        regenerate: Force regeneration even if summary exists

    Returns:
        EventSummary or None
    """
    event = db.query(Event).filter(Event.id == event_id).first()

    if not event:
        logger.error(f"Event {event_id} not found")
        return None

    # Check for existing summary
    if not regenerate:
        existing = db.query(EventSummary).filter(
            EventSummary.event_id == event_id,
            EventSummary.summary_method.like("chatgpt_%")
        ).first()

        if existing:
            logger.info(f"Summary already exists for event {event_id}")
            return existing

    summarizer = ChatGPTSummarizer(db)
    return summarizer.generate_summary(event, model=model)
