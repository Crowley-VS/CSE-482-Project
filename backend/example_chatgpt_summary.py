"""
Example script demonstrating ChatGPT event summarization.

This script shows how to:
1. Generate a summary for a single event
2. Batch generate summaries for multiple events
3. Retrieve events with their summaries

Usage:
    python example_chatgpt_summary.py
"""

import requests
import json
from datetime import datetime

# API Configuration
BASE_URL = "http://localhost:8000/api"


def generate_single_summary(event_id: int, model: str = "gpt-3.5-turbo"):
    """Generate a ChatGPT summary for a single event."""
    print(f"\n{'='*60}")
    print(f"Generating summary for Event #{event_id} using {model}")
    print(f"{'='*60}")

    response = requests.post(
        f"{BASE_URL}/events/{event_id}/summary",
        params={"model": model, "regenerate": False}
    )

    if response.status_code == 200:
        data = response.json()
        summary = data["summary"]

        print(f"\n✓ Summary generated successfully!")
        print(f"Summary ID: {summary['id']}")
        print(f"Method: {summary['summary_method']}")
        print(f"Created: {summary['created_at']}")
        print(f"\n{'-'*60}")
        print("SUMMARY TEXT:")
        print(f"{'-'*60}")
        print(summary['summary_text'])
        print(f"{'-'*60}\n")

        return summary
    else:
        print(f"\n✗ Error: {response.status_code}")
        print(response.json())
        return None


def batch_generate_summaries(event_ids: list = None, model: str = "gpt-3.5-turbo"):
    """Generate summaries for multiple events."""
    print(f"\n{'='*60}")
    print(f"Batch generating summaries using {model}")
    if event_ids:
        print(f"Event IDs: {event_ids}")
    else:
        print("Processing ALL events")
    print(f"{'='*60}")

    payload = {}
    if event_ids:
        payload["event_ids"] = event_ids

    response = requests.post(
        f"{BASE_URL}/events/summaries/batch",
        params={"model": model, "regenerate": False},
        json=payload
    )

    if response.status_code == 200:
        data = response.json()
        print(f"\n✓ Batch processing completed!")
        print(f"Total events: {data['total_events']}")
        print(f"Summaries generated: {data['summaries_generated']}")
        print(f"Summaries skipped: {data['summaries_skipped']}")
        print(f"Errors: {data['errors']}")
        return data
    else:
        print(f"\n✗ Error: {response.status_code}")
        print(response.json())
        return None


def get_events_with_summaries(limit: int = 10):
    """Retrieve events with their summaries."""
    print(f"\n{'='*60}")
    print(f"Fetching {limit} events with summaries")
    print(f"{'='*60}")

    response = requests.get(
        f"{BASE_URL}/events/",
        params={"include_summary": True, "limit": limit}
    )

    if response.status_code == 200:
        data = response.json()
        events = data["events"]

        print(f"\n✓ Retrieved {data['count']} events")

        for event in events:
            print(f"\n{'-'*60}")
            print(f"Event #{event['id']}: {event['event_name']}")
            print(f"Type: {event['event_type']}")
            print(f"Posts: {event['num_posts']}")

            if "summary" in event and event["summary"]:
                summary = event["summary"]
                print(f"\n📝 SUMMARY ({summary['summary_method']}):")
                print(summary['summary_text'][:300] + "...")
            else:
                print("\n⚠ No summary available")

        return events
    else:
        print(f"\n✗ Error: {response.status_code}")
        print(response.json())
        return None


def get_event_summary(event_id: int):
    """Get the summary for a specific event."""
    print(f"\n{'='*60}")
    print(f"Retrieving summary for Event #{event_id}")
    print(f"{'='*60}")

    response = requests.get(f"{BASE_URL}/events/{event_id}/summary")

    if response.status_code == 200:
        data = response.json()

        if data.get("has_summary"):
            print(f"\n✓ Summary found!")
            print(f"\nEvent: {data['event']['event_name']}")
            print(f"\n{'-'*60}")
            print("SUMMARY:")
            print(f"{'-'*60}")
            print(data['summary']['summary_text'])
            print(f"{'-'*60}\n")
        else:
            print(f"\n⚠ {data['message']}")

        return data
    else:
        print(f"\n✗ Error: {response.status_code}")
        print(response.json())
        return None


def main():
    """Main demonstration function."""
    print("\n" + "="*60)
    print("ChatGPT Event Summarization Demo")
    print("="*60)

    # Example 1: Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"\n✓ Backend server is running at {BASE_URL}")
    except requests.exceptions.ConnectionError:
        print(f"\n✗ Cannot connect to backend at {BASE_URL}")
        print("Please start the backend server first:")
        print("  cd backend && python run.py")
        return

    # Example 2: Get events to see what's available
    print("\n" + "="*60)
    print("Step 1: Checking available events")
    print("="*60)

    response = requests.get(f"{BASE_URL}/events/", params={"limit": 5})
    if response.status_code == 200:
        events = response.json()["events"]
        if not events:
            print("\n⚠ No events found in database.")
            print("Please run event detection first:")
            print("  POST /api/events/detect/keyword-spike")
            return

        print(f"\n✓ Found {len(events)} events:")
        for event in events[:3]:
            print(
                f"  - Event #{event['id']}: {event['event_name']} ({event['num_posts']} posts)")

        # Use the first event for demonstration
        demo_event_id = events[0]['id']
    else:
        print("\n✗ Error retrieving events")
        return

    # Example 3: Generate summary for single event
    print("\n" + "="*60)
    print("Step 2: Generate summary for single event")
    print("="*60)

    summary = generate_single_summary(demo_event_id, model="gpt-3.5-turbo")

    if not summary:
        print("\n⚠ Skipping remaining examples due to error")
        print("Check that your OPENAI_API_KEY is configured in .env")
        return

    # Example 4: Retrieve event with summary
    print("\n" + "="*60)
    print("Step 3: Retrieve event with summary")
    print("="*60)

    get_event_summary(demo_event_id)

    # Example 5: Batch generate (if multiple events)
    if len(events) > 1:
        print("\n" + "="*60)
        print("Step 4: Batch generate summaries")
        print("="*60)

        event_ids = [e['id'] for e in events[:3]]  # First 3 events
        batch_generate_summaries(event_ids, model="gpt-3.5-turbo")

    # Example 6: Get all events with summaries
    print("\n" + "="*60)
    print("Step 5: Retrieve events with summaries")
    print("="*60)

    get_events_with_summaries(limit=5)

    print("\n" + "="*60)
    print("Demo completed!")
    print("="*60)
    print("\nFor more information, see: backend/CHATGPT_SUMMARIES.md\n")


if __name__ == "__main__":
    main()
