"""Run script to start the FastAPI server."""
import uvicorn
from app.core.logging import setup_logging
from app.core.scheduler import start_scheduler

if __name__ == "__main__":
    # Setup logging
    setup_logging()
    
    # Start background scheduler
    #start_scheduler()
    
    # Run the FastAPI application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
