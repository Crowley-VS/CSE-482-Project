# ChatGPT Event Summary - Quick Reference

## Quick Start

### 1. Setup
```bash
# Add to .env
OPENAI_API_KEY=sk-your-api-key-here

# Install OpenAI package
pip install openai==1.3.0
```

### 2. Generate Summary
```bash
# Single event
curl -X POST "http://localhost:8000/api/events/1/summary?model=gpt-3.5-turbo"

# Batch (all events without summaries)
curl -X POST "http://localhost:8000/api/events/summaries/batch"
```

### 3. Retrieve Summary
```bash
# Get specific event summary
curl "http://localhost:8000/api/events/1/summary"

# Get events with summaries included
curl "http://localhost:8000/api/events/?include_summary=true"
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/events/{id}/summary` | POST | Generate summary for event |
| `/events/{id}/summary` | GET | Get event summary |
| `/events/summaries/batch` | POST | Batch generate summaries |
| `/events/?include_summary=true` | GET | Get events with summaries |

## Query Parameters

### POST `/events/{id}/summary`
- `model`: Model to use (`gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo`)
- `regenerate`: Force regeneration (default: `false`)

### POST `/events/summaries/batch`
- `event_ids`: List of event IDs (omit for all)
- `model`: Model to use
- `regenerate`: Force regeneration

### GET `/events/`
- `include_summary`: Include summaries (default: `false`)
- `limit`: Max events (default: 50)
- `offset`: Pagination offset

## Python Usage

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Generate summary
response = requests.post(
    f"{BASE_URL}/events/1/summary",
    params={"model": "gpt-3.5-turbo"}
)
summary = response.json()["summary"]["summary_text"]

# Batch generate
requests.post(
    f"{BASE_URL}/events/summaries/batch",
    params={"regenerate": False}
)

# Get with summary
response = requests.get(
    f"{BASE_URL}/events/1",
    params={"include_summary": True}
)
event = response.json()
```

## Model Comparison

| Model | Cost/Summary | Speed | Quality | Use Case |
|-------|-------------|-------|---------|----------|
| gpt-3.5-turbo | ~$0.001 | Fast (2-5s) | Good | Production |
| gpt-4 | ~$0.03 | Slow (10-20s) | Excellent | Critical events |
| gpt-4-turbo | ~$0.01 | Medium (5-10s) | Excellent | Balanced |

## Example Response

```json
{
  "status": "success",
  "event_id": 1,
  "summary": {
    "id": 1,
    "event_id": 1,
    "summary_text": "This event centers around the Federal Reserve's announcement of a 0.25% interest rate hike...",
    "summary_method": "chatgpt_gpt-3.5-turbo",
    "num_source_posts": 50,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

## Common Issues

**"OpenAI client not initialized"**
- Check `OPENAI_API_KEY` in `.env`
- Restart backend after updating `.env`

**"Failed to generate summary"**
- Verify API key is valid
- Check OpenAI credits/billing
- Review backend logs

**Low quality summaries**
- Use GPT-4 for better quality
- Ensure events have 5+ posts
- Check post content quality

## Cost Monitoring

- 1,000 summaries with GPT-3.5-turbo ≈ $1.00
- 1,000 summaries with GPT-4 ≈ $30.00
- Monitor usage: https://platform.openai.com/usage

## Integration Example

```python
# In event detection workflow
from app.event_detection.chatgpt_summarizer import generate_event_summary

# After detecting event
event = detect_event()
db.add(event)
db.commit()

# Generate summary
summary = generate_event_summary(db, event.id)
```

## Full Documentation

See [CHATGPT_SUMMARIES.md](CHATGPT_SUMMARIES.md) for complete documentation.
