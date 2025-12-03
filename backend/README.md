# Economic Event Detection Backend

Backend API for detecting and summarizing economic events from Reddit and Twitter.

## Features

- **Data Collection**: Automated collection from Reddit (r/Economics, r/WallStreetBets, r/Finance) and Twitter
- **Event Detection**: Three different approaches
  - Keyword-based spike detection (temporal analysis)
  - BERTopic clustering
  - LDA topic modeling
- **AI Summarization**: ChatGPT-powered event summaries with GPT-3.5 and GPT-4 support
- **REST API**: FastAPI endpoints for data collection and event retrieval
- **Scheduled Tasks**: Automatic periodic data collection and event detection
- **PostgreSQL Storage**: Persistent storage of posts and detected events

## Setup

### Prerequisites

- Python 3.9+
- PostgreSQL database
- Reddit API credentials
- Twitter API credentials

### Installation

1. Install Poetry (if not already installed):
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

2. Install dependencies:
```bash
poetry install
```

3. Download spaCy model:
```bash
poetry run python -m spacy download en_core_web_sm
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

5. Initialize database:
```bash
poetry run python -c "from app.db.session import init_db; init_db()"
```

### Running the Server

```bash
poetry run python run.py
```

Or use Poetry's shell:
```bash
poetry shell
python run.py
```

Server will start at `http://localhost:8000`

API documentation available at `http://localhost:8000/docs`

## API Endpoints

### Health
- `GET /health` - Health check
- `GET /api/v1/health/db` - Database health

### Data Collection
- `POST /api/v1/collection/reddit/collect` - Collect from Reddit
- `POST /api/v1/collection/twitter/collect` - Collect from Twitter
- `POST /api/v1/collection/collect-all` - Collect from all sources
- `GET /api/v1/collection/stats` - Collection statistics

### Event Detection
- `POST /api/v1/events/detect/keyword-spike` - Detect using keyword spikes
- `POST /api/v1/events/detect/bertopic` - Detect using BERTopic
- `POST /api/v1/events/detect/lda` - Detect using LDA
- `GET /api/v1/events/` - List detected events
- `GET /api/v1/events/{event_id}` - Get event details
- `GET /api/v1/events/{event_id}/posts` - Get posts for an event
- `GET /api/v1/events/trends/keywords` - Get keyword trends

### Event Summarization (NEW)
- `POST /api/v1/events/{event_id}/summary` - Generate ChatGPT summary for event
- `POST /api/v1/events/summaries/batch` - Batch generate summaries
- `GET /api/v1/events/{event_id}/summary` - Get event summary

See [CHATGPT_SUMMARIES.md](CHATGPT_SUMMARIES.md) for detailed documentation.

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── endpoints/      # API route handlers
│   │   └── routes.py       # Route configuration
│   ├── collectors/         # Data collection modules
│   │   ├── reddit_collector.py
│   │   └── twitter_collector.py
│   ├── core/               # Core utilities
│   │   ├── config.py       # Configuration
│   │   ├── logging.py      # Logging setup
│   │   └── scheduler.py    # Background tasks
│   ├── db/                 # Database
│   │   └── session.py      # DB connection
│   ├── event_detection/    # Event detection algorithms
│   │   ├── keyword_spike.py
│   │   ├── bertopic_detector.py
│   │   ├── lda_detector.py
│   │   └── chatgpt_summarizer.py  # NEW: ChatGPT summarization
│   ├── models/             # Database models
│   │   ├── post.py
│   │   └── event.py
│   └── main.py             # FastAPI app
├── requirements.txt
├── .env.example
└── run.py
```

## Configuration

Edit `.env` file to configure:
- Database connection
- API credentials (Reddit, Twitter)
- **OpenAI API key** (for ChatGPT summaries)
- Collection intervals
- Economic keywords to track
- Subreddits to monitor
- Event detection thresholds

### Setting up ChatGPT Summaries

1. Get an OpenAI API key from https://platform.openai.com/api-keys
2. Add to `.env`: `OPENAI_API_KEY=sk-your-api-key-here`
3. Install OpenAI package: `poetry add openai`
4. See [CHATGPT_SUMMARIES.md](CHATGPT_SUMMARIES.md) for usage

## Development

Run tests:
```bash
poetry run pytest
```

Format code:
```bash
poetry run black app/
```

Lint:
```bash
poetry run flake8 app/
```

Add new dependencies:
```bash
poetry add <package-name>
```

Add dev dependencies:
```bash
poetry add --group dev <package-name>
```
