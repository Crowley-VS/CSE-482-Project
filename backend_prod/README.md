# Production Backend - Read-Only API

This is a lightweight production backend that provides read-only access to posts and events, plus data import/export functionality.

## Features

- **Read-Only Event API**: Retrieve detected events and their summaries
- **Read-Only Post API**: Query posts with various filters
- **Data Transfer**: Import and export posts and events

## API Endpoints

### Health
- `GET /` - Root health check
- `GET /health` - Detailed health status
- `GET /api/v1/health/` - API health check

### Events (Read-Only)
- `GET /api/v1/events/` - List all events with optional filters
- `GET /api/v1/events/{event_id}` - Get specific event details
- `GET /api/v1/events/{event_id}/posts` - Get posts for an event

### Posts (Read-Only)
- `GET /api/v1/posts/` - List posts with filters (source, subreddit, keyword, time range)
- `GET /api/v1/posts/{post_id}` - Get specific post details

### Data Transfer
- `GET /api/v1/data/export` - Export all posts and events as JSON
- `POST /api/v1/data/import` - Import posts and events from JSON

## Installation

### Using pip
```bash
pip install -r requirements.txt
```

### Using Poetry
```bash
poetry install
```

## Configuration

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/economic_events_db

# Application
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

## Running the Application

### With Python
```bash
python run.py
```

### With Uvicorn
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### With Docker
```bash
docker build -t backend-prod .
docker run -p 8000:8000 --env-file .env backend-prod
```

## Architecture

This backend is designed to be minimal and focused:
- No data collection (no Reddit/Twitter API dependencies)
- No event detection (no NLP/ML dependencies)
- No background schedulers
- Only database reads and writes for data transfer
- Optimized for serving data to frontends

## Docker Deployment

See `Dockerfile` for containerized deployment instructions.
