"""
Lead Engine — FastAPI Application
Entry point for the backend server.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routes import router
from backend.scheduler import stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("═══ Lead Engine Starting ═══")
    await init_db()
    logger.info("Database initialized")
    from backend.scheduler import start_scheduler_service
    start_scheduler_service()
    yield
    # Shutdown
    stop_scheduler()
    logger.info("═══ Lead Engine Stopped ═══")


app = FastAPI(
    title="Lead Engine",
    description="Automated executive lead-generation agent for business development",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for production flexibility
# Since we use JWT in headers (not cookies), allow_credentials=False is safer with "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False, 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routes
app.include_router(router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "Lead Engine API", "version": "1.0.0"}
