# ChatGPT Event Summarization

This feature adds AI-powered event summarization using OpenAI's ChatGPT API.

## Overview

The ChatGPT summarizer analyzes detected economic events and generates comprehensive, human-readable summaries that explain:
- What the event is about
- Key concerns and discussion points
- Specific data, dates, or figures mentioned
- Overall sentiment and public reaction
- Economic context and significance

## Setup

### 1. Install Dependencies

```bash
cd backend
pip install openai==1.3.0
# Or if using poetry:
poetry add openai
```

### 2. Configure OpenAI API Key

Add your OpenAI API key to `.env`:

```bash
OPENAI_API_KEY=sk-your-actual-api-key-here
```

Get your API key from: https://platform.openai.com/api-keys

## API Endpoints

### Generate Summary for Single Event

**POST** `/api/events/{event_id}/summary`

Generate a ChatGPT summary for a specific event.

**Query Parameters:**
- `model` (optional): OpenAI model to use (default: `gpt-3.5-turbo`)
  - Options: `gpt-3.5-turbo`, `gpt-4`, `gpt-4-turbo-preview`
- `regenerate` (optional): Force regeneration even if summary exists (default: `false`)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/events/1/summary?model=gpt-3.5-turbo"
```

**Response:**
```json
{
  "status": "success",
  "event_id": 1,
  "summary": {
    "id": 1,
    "event_id": 1,
    "summary_text": "This event centers around...",
    "summary_method": "chatgpt_gpt-3.5-turbo",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Batch Generate Summaries

**POST** `/api/events/summaries/batch`

Generate summaries for multiple events at once.

**Query Parameters:**
- `event_ids` (optional): List of event IDs to summarize (omit to process all events)
- `model` (optional): OpenAI model to use (default: `gpt-3.5-turbo`)
- `regenerate` (optional): Force regeneration for existing summaries (default: `false`)

**Example:**
```bash
curl -X POST "http://localhost:8000/api/events/summaries/batch" \
  -H "Content-Type: application/json" \
  -d '{"event_ids": [1, 2, 3]}'
```

**Response:**
```json
{
  "status": "success",
  "total_events": 3,
  "summaries_generated": 3,
  "summaries_skipped": 0,
  "errors": 0
}
```

### Get Event Summary

**GET** `/api/events/{event_id}/summary`

Retrieve the latest summary for an event.

**Example:**
```bash
curl "http://localhost:8000/api/events/1/summary"
```

### Get Events with Summaries

**GET** `/api/events/?include_summary=true`

Retrieve events with their summaries included.

**Query Parameters:**
- `include_summary` (optional): Include summaries in response (default: `false`)
- `method` (optional): Filter by detection method
- `limit` (optional): Max events to return (default: 50, max: 200)
- `offset` (optional): Pagination offset (default: 0)

**Example:**
```bash
curl "http://localhost:8000/api/events/?include_summary=true&limit=10"
```

## Usage Examples

### Python

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Generate summary for event #1
response = requests.post(
    f"{BASE_URL}/events/1/summary",
    params={"model": "gpt-3.5-turbo"}
)
summary = response.json()
print(summary["summary"]["summary_text"])

# Batch generate for all events
response = requests.post(
    f"{BASE_URL}/events/summaries/batch",
    params={"regenerate": False}
)
results = response.json()
print(f"Generated {results['summaries_generated']} summaries")

# Get event with summary
response = requests.get(
    f"{BASE_URL}/events/1",
    params={"include_summary": True}
)
event = response.json()
if "summary" in event:
    print(event["summary"]["summary_text"])
```

### JavaScript/Frontend

```javascript
// Generate summary
async function generateSummary(eventId) {
  const response = await fetch(
    `/api/events/${eventId}/summary?model=gpt-3.5-turbo`,
    { method: 'POST' }
  );
  const data = await response.json();
  return data.summary;
}

// Get events with summaries
async function getEventsWithSummaries() {
  const response = await fetch('/api/events/?include_summary=true&limit=20');
  const data = await response.json();
  return data.events;
}

// Batch generate
async function batchGenerate(eventIds) {
  const response = await fetch('/api/events/summaries/batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ event_ids: eventIds })
  });
  return await response.json();
}
```

## Model Selection

### GPT-3.5-turbo (Recommended)
- **Cost**: ~$0.001 per summary
- **Speed**: Fast (~2-5 seconds)
- **Quality**: Good for most use cases
- **Best for**: Production, batch processing

### GPT-4
- **Cost**: ~$0.03 per summary
- **Speed**: Slower (~10-20 seconds)
- **Quality**: Excellent, more nuanced
- **Best for**: Critical events, detailed analysis

### GPT-4-turbo
- **Cost**: ~$0.01 per summary
- **Speed**: Medium (~5-10 seconds)
- **Quality**: Excellent
- **Best for**: Balance of quality and cost

## Cost Estimation

Based on average usage:
- **GPT-3.5-turbo**: ~1,000 summaries = $1.00
- **GPT-4**: ~1,000 summaries = $30.00
- **GPT-4-turbo**: ~1,000 summaries = $10.00

*Costs are approximate and depend on summary length and prompt complexity*

## Workflow Integration

### Automatic Summary Generation

To automatically generate summaries when events are detected:

1. **Option 1: Post-detection hook**
   ```python
   # In event detection code
   from app.event_detection.chatgpt_summarizer import generate_event_summary
   
   # After saving event
   summary = generate_event_summary(db, event.id)
   ```

2. **Option 2: Scheduled task**
   ```python
   # Add to scheduler
   from app.event_detection.chatgpt_summarizer import ChatGPTSummarizer
   
   def summarize_new_events():
       db = next(get_db())
       summarizer = ChatGPTSummarizer(db)
       summarizer.batch_generate_summaries(regenerate=False)
   
   # Run daily
   scheduler.add_job(summarize_new_events, 'cron', hour=2)
   ```

## Database Schema

Summaries are stored in the `event_summaries` table:

```sql
CREATE TABLE event_summaries (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    summary_text TEXT NOT NULL,
    summary_method VARCHAR(50) NOT NULL,  -- e.g., 'chatgpt_gpt-3.5-turbo'
    num_source_posts INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Error Handling

The API handles common errors gracefully:

- **No API key configured**: Returns 500 with message about configuration
- **Event not found**: Returns 404
- **OpenAI API error**: Returns 500 with error details
- **Rate limiting**: Automatically retries with exponential backoff

## Best Practices

1. **Use GPT-3.5-turbo for most cases** - It's fast and cost-effective
2. **Enable `regenerate=false`** - Avoid duplicate summaries
3. **Batch process** - Use `/summaries/batch` for multiple events
4. **Monitor costs** - Track OpenAI usage in their dashboard
5. **Cache summaries** - Summaries are stored in DB, no need to regenerate
6. **Handle errors** - Check API responses and log failures

## Troubleshooting

### "OpenAI client not initialized"
- Check that `OPENAI_API_KEY` is set in `.env`
- Verify the key is not the placeholder value
- Restart the backend server after updating `.env`

### "Failed to generate summary"
- Check OpenAI API key is valid
- Verify you have API credits
- Check OpenAI service status
- Review backend logs for detailed errors

### Summaries are generic/low quality
- Try using GPT-4 for better quality
- Ensure events have enough posts (5+ recommended)
- Check that post content is meaningful

## Integration with Frontend

Example React component:

```jsx
function EventSummary({ eventId }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);

  const generateSummary = async () => {
    setLoading(true);
    try {
      const response = await fetch(
        `/api/events/${eventId}/summary?model=gpt-3.5-turbo`,
        { method: 'POST' }
      );
      const data = await response.json();
      setSummary(data.summary.summary_text);
    } catch (error) {
      console.error('Failed to generate summary:', error);
    }
    setLoading(false);
  };

  return (
    <div>
      {summary ? (
        <p>{summary}</p>
      ) : (
        <button onClick={generateSummary} disabled={loading}>
          {loading ? 'Generating...' : 'Generate Summary'}
        </button>
      )}
    </div>
  );
}
```

## Security Notes

- **Never commit** your OpenAI API key to version control
- Use environment variables for API keys
- Consider rate limiting summary generation endpoints
- Monitor API usage to prevent abuse
- Implement user authentication for production use
