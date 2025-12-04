"""Run script to start the FastAPI server - Production."""
import uvicorn
from app.core.logging import setup_logging

if __name__ == "__main__":
    # Setup logging
    setup_logging()

    # Run the FastAPI application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Production mode - no reload
        log_level="info"
    )
