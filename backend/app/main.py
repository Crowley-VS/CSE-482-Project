"""Main FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import threading

from app.api.routes import router
from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler, run_initial_collection
from app.core.logging import setup_logging, get_logger

# Setup logging at module level so it's initialized when the app starts
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown events."""
    # Startup
    logger.info("Starting application...")

    # Start background scheduler
    start_scheduler()

    # Run initial data collection in a separate thread to not block startup
    collection_thread = threading.Thread(
        target=run_initial_collection, daemon=True)
    collection_thread.start()

    yield

    # Shutdown
    logger.info("Shutting down application...")
    stop_scheduler()


app = FastAPI(
    title="Economic Event Detection API",
    description="Detect and summarize economic events from Reddit and Twitter",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "service": "Economic Event Detection API",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",  # TODO: Add actual DB check
        "collectors": "ready"
    }
