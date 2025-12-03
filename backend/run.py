"""Run script to start the FastAPI server."""
import uvicorn
from app.core.logging import setup_logging

if __name__ == "__main__":
    # Setup logging
    setup_logging()

    # Run the FastAPI application
    # Scheduler and initial collection are started via app lifespan
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
