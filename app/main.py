"""
FastAPI application entry point.
Initializes the application, database, and seeds sample problems.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .database import engine, Base, SessionLocal
from .models import Problem
from .database import engine, Base, SessionLocal
from .models import Problem
from .api_routes import router


from .cf_client import fetch_problems_from_cf
from sqlalchemy.exc import IntegrityError

def fetch_and_store_problems(db):
    """
    Fetch problems from Codeforces API and store them in the database.
    """
    problems = fetch_problems_from_cf()
    if not problems:
        print("No problems fetched from Codeforces.")
        return

    count = 0
    for p_data in problems:
        # Check if exists
        exists = db.query(Problem).filter(
            Problem.contest_id == p_data["contest_id"],
            Problem.problem_index == p_data["problem_index"]
        ).first()
        
        if not exists:
            problem = Problem(**p_data)
            db.add(problem)
            count += 1
    
    try:
        db.commit()
        print(f"Successfully added {count} new problems to the database.")
    except Exception as e:
        print(f"Database error during seeded: {e}")
        db.rollback()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Creates database tables and seeds sample data on startup.
    """
    # Startup: Create tables
    Base.metadata.create_all(bind=engine)
    
    # Seed problems if database is empty or explicitly requested
    db = SessionLocal()
    try:
        # Check if we have enough problems (heuristic check)
        problem_count = db.query(Problem).count()
        if problem_count < 100:
            print(f"Database has only {problem_count} problems. Fetching from Codeforces...")
            fetch_and_store_problems(db)
        else:
            print(f"Database already has {problem_count} problems. Skipping initial fetch.")
    except Exception as e:
        print(f"Error during startup seeding: {e}")
    finally:
        db.close()
    
    yield
    
    # Shutdown: Cleanup if needed
    pass


# Create FastAPI application
app = FastAPI(
    title="Adaptive Competitive Programming Coach",
    description="API for recommending competitive programming problems based on user rating and topic preferences",
    version="1.0.0",
    lifespan=lifespan
)

# Deployment Check
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if os.getenv("RENDER") or os.getenv("RAILWAY_ENVIRONMENT"):
    logger.info("🚀 Production Environment Detected (Render/Railway)")
    logger.info("Database URL Configured: " + ("YES" if os.getenv("DATABASE_URL") else "NO"))
else:
    logger.info("🔧 Running in Local/Development Mode")

# Debug: Global Exception Handler
@app.exception_handler(Exception)
async def debug_exception_handler(request, exc):
    import traceback
    error_msg = f"{str(exc)}\n\n{traceback.format_exc()}"
    print(f"CRITICAL ERROR: {error_msg}")
    return JSONResponse(
        status_code=500,
        content={"detail": error_msg}
    )

# Configure CORS for frontend and browser extension access
# TODO: Restrict origins in production to specific extension IDs
# TODO: Add rate limiting for extension endpoints
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for extension support
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "message": "Adaptive Competitive Programming Coach API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "get_user": "GET /user/{handle}",
            "get_recommendations": "GET /recommend?handle={handle}&topic={topic}",
            "extension_recommend": "GET /extension/recommend?handle={handle}&topic={topic}",
            "mark_solved": "POST /solve/{problem_id}?handle={handle}",
            "list_problems": "GET /problems"
        }
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
