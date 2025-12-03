# Docker Deployment Guide

This guide explains how to deploy the Economic Event Detection backend using Docker.

## Quick Start

### 1. Build the Docker Image

```bash
cd backend
docker build -t economic-events-backend .
```

### 2. Run with Docker Compose (Recommended)

```bash
# Copy the example environment file and configure it
cp .env.example .env
# Edit .env with your API keys and configuration

# Start the services
docker compose -f docker-compose.production.yml up -d

# View logs
docker compose -f docker-compose.production.yml logs -f backend

# Stop the services
docker compose -f docker-compose.production.yml down
```

### 3. Run with Docker Run (Manual)

```bash
# Run PostgreSQL
docker run -d \
  --name economic_events_db \
  -e POSTGRES_DB=economic_events_db \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  postgres:15-alpine

# Run the backend
docker run -d \
  --name economic_events_backend \
  -p 8000:8000 \
  --env-file .env \
  -e DATABASE_URL=postgresql://user:password@host.docker.internal:5432/economic_events_db \
  economic-events-backend
```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Required variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDDIT_CLIENT_ID`: Reddit API client ID
- `REDDIT_CLIENT_SECRET`: Reddit API client secret

Optional variables:
- `TWITTER_BEARER_TOKEN`: Twitter API bearer token
- `REDDIT_USERNAME`: For Selenium-based Reddit scraping
- `REDDIT_PASSWORD`: For Selenium-based Reddit scraping
- `SELENIUM_HEADLESS`: Set to "true" for production (default)
- `SCHEDULER_ACTIVE`: Enable/disable scheduled data collection

## Features

The Docker image includes:

✅ Python 3.11
✅ Google Chrome (stable)
✅ ChromeDriver (latest compatible version)
✅ All Python dependencies from requirements.txt
✅ spaCy English language model
✅ NLTK data packages
✅ PostgreSQL client libraries
✅ Health check endpoint
✅ Non-root user for security

## Chrome/Selenium Support

The image includes full Chrome and Selenium support for web scraping:

- **Headless mode**: Chrome runs without GUI (production default)
- **ChromeDriver**: Automatically matched to Chrome version
- **Session persistence**: Chrome data stored in `/app/chrome_data` volume

## Database Initialization

The database schema will be created automatically on first run. To manually run migrations:

```bash
docker compose exec backend alembic upgrade head
```

## Health Check

The API includes a health check endpoint:

```bash
curl http://localhost:8000/api/health
```

Docker's built-in health check will automatically monitor this endpoint.

## Production Deployment

### Resource Limits

Uncomment the resource limits in `docker-compose.production.yml` to set memory and CPU limits:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
```

### Scaling

To run multiple backend instances:

```bash
docker compose -f docker-compose.production.yml up -d --scale backend=3
```

Note: You'll need a load balancer (nginx, traefik) in front of multiple instances.

### Monitoring

View real-time logs:

```bash
# All services
docker compose -f docker-compose.production.yml logs -f

# Just backend
docker compose -f docker-compose.production.yml logs -f backend

# Just database
docker compose -f docker-compose.production.yml logs -f db
```

### Backup Database

```bash
docker compose exec db pg_dump -U user economic_events_db > backup.sql
```

### Restore Database

```bash
cat backup.sql | docker compose exec -T db psql -U user economic_events_db
```

## Troubleshooting

### Chrome/ChromeDriver Issues

If you encounter Chrome-related errors:

```bash
# Check Chrome version
docker compose exec backend google-chrome --version

# Check ChromeDriver version
docker compose exec backend chromedriver --version
```

### Permission Issues

If you encounter permission errors with Chrome:

```bash
# Check chrome_data volume permissions
docker compose exec backend ls -la /app/chrome_data
```

### Database Connection Issues

```bash
# Test database connectivity
docker compose exec backend python -c "from app.db.session import engine; engine.connect()"
```

### View Application Logs

```bash
docker compose exec backend cat /app/logs/app.log
```

## Updating

To update the application:

```bash
# Pull latest code
git pull

# Rebuild the image
docker compose -f docker-compose.production.yml build

# Restart services
docker compose -f docker-compose.production.yml up -d
```

## Cleanup

```bash
# Stop and remove containers
docker compose -f docker-compose.production.yml down

# Remove volumes (WARNING: This deletes all data!)
docker compose -f docker-compose.production.yml down -v

# Remove images
docker rmi economic-events-backend
```

## API Documentation

Once running, access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Security Considerations

1. **Change default database credentials** in production
2. **Use secrets management** for API keys (Docker secrets, K8s secrets, etc.)
3. **Enable HTTPS** with a reverse proxy (nginx, traefik)
4. **Keep dependencies updated** regularly
5. **Monitor resource usage** and set appropriate limits
6. **Regular backups** of the database
7. **Use .env file** for sensitive data (never commit to Git)

## Cloud Deployment

### AWS ECS/Fargate

```bash
# Build for AMD64 (if on Apple Silicon)
docker buildx build --platform linux/amd64 -t economic-events-backend .

# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker tag economic-events-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/economic-events-backend:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/economic-events-backend:latest
```

### Google Cloud Run

```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/<project-id>/economic-events-backend

# Deploy
gcloud run deploy economic-events-backend \
  --image gcr.io/<project-id>/economic-events-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Digital Ocean App Platform

Use the `docker-compose.production.yml` or create an app spec:

```yaml
name: economic-events-backend
services:
- name: backend
  dockerfile_path: backend/Dockerfile
  github:
    repo: your-repo
    branch: main
  envs:
  - key: DATABASE_URL
    value: ${db.DATABASE_URL}
databases:
- name: db
  engine: PG
  version: "15"
```
