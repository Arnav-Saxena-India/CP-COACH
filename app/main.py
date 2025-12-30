"""
FastAPI application entry point.
Initializes the application, database, with rate limiting and structured logging.
"""

import os
import time
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from .database import engine, Base, SessionLocal
from .models import Problem
from .api_routes import router
from .cf_client import fetch_problems_from_cf
from .config import API_VERSION, LOG_FORMAT, LOG_DATE_FORMAT, RATE_LIMIT_PER_MINUTE
from .errors import APIError, RateLimitError
from .cache import user_data_cache

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT
)
logger = logging.getLogger(__name__)


# =============================================================================
# RATE LIMITING (Simple in-memory implementation)
# =============================================================================

class RateLimiter:
    """Simple in-memory rate limiter per IP."""
    
    def __init__(self, requests_per_minute: int = RATE_LIMIT_PER_MINUTE):
        self.requests_per_minute = requests_per_minute
        self.requests = {}  # IP -> list of timestamps
    
    def is_allowed(self, ip: str) -> tuple[bool, int]:
        """
        Check if request is allowed.
        
        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        now = time.time()
        minute_ago = now - 60
        
        # Clean old entries
        if ip in self.requests:
            self.requests[ip] = [t for t in self.requests[ip] if t > minute_ago]
        else:
            self.requests[ip] = []
        
        # Check limit
        if len(self.requests[ip]) >= self.requests_per_minute:
            oldest = min(self.requests[ip])
            retry_after = int(oldest + 60 - now) + 1
            return False, retry_after
        
        # Record request
        self.requests[ip].append(now)
        return True, 0

rate_limiter = RateLimiter()


# =============================================================================
# STARTUP/SHUTDOWN
# =============================================================================

def fetch_and_store_problems(db):
    """Fetch problems from Codeforces API and store them in the database."""
    try:
        problems = fetch_problems_from_cf()
    except Exception as e:
        logger.error(f"Failed to fetch problems: {e}")
        return
    
    if not problems:
        logger.warning("No problems fetched from Codeforces.")
        return

    count = 0
    for p_data in problems:
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
        logger.info(f"Successfully added {count} new problems to the database.")
    except Exception as e:
        logger.error(f"Database error during seeding: {e}")
        db.rollback()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: Create tables
    Base.metadata.create_all(bind=engine)
    
    # Run Schema Migrations
    from .database import run_migrations
    run_migrations(engine)
    
    # Seed problems if database is empty
    db = SessionLocal()
    try:
        problem_count = db.query(Problem).count()
        if problem_count < 100:
            logger.info(f"Database has only {problem_count} problems. Fetching from Codeforces...")
            fetch_and_store_problems(db)
        else:
            logger.info(f"Database already has {problem_count} problems. Skipping initial fetch.")
    except Exception as e:
        logger.error(f"Error during startup seeding: {e}")
    finally:
        db.close()
    
    yield
    
    # Shutdown: Cleanup cache
    user_data_cache.clear()
    logger.info("Application shutdown complete.")


# =============================================================================
# APPLICATION SETUP
# =============================================================================

app = FastAPI(
    title="Adaptive Competitive Programming Coach",
    description="API for recommending competitive programming problems based on user rating and topic preferences",
    version="2.0.0",
    lifespan=lifespan
)

# Deployment logging
if os.getenv("RENDER") or os.getenv("RAILWAY_ENVIRONMENT"):
    logger.info("🚀 Production Environment Detected (Render/Railway)")
    logger.info("Database URL Configured: " + ("YES" if os.getenv("DATABASE_URL") else "NO"))
else:
    logger.info("🔧 Running in Local/Development Mode")


# =============================================================================
# MIDDLEWARE
# =============================================================================

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next: Callable) -> Response:
    """Log request timing and cache status."""
    start_time = time.time()
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Rate limiting (skip for health checks)
    if not request.url.path.startswith("/health"):
        allowed, retry_after = rate_limiter.is_allowed(client_ip)
        if not allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": True,
                    "code": "RATE_LIMITED",
                    "message": "Too many requests",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration_ms = (time.time() - start_time) * 1000
    
    # Log request
    logger.info(
        f"{request.method} {request.url.path} "
        f"status={response.status_code} "
        f"duration={duration_ms:.1f}ms "
        f"ip={client_ip}"
    )
    
    # Add timing header
    response.headers["X-Response-Time"] = f"{duration_ms:.1f}ms"
    
    return response


# Global exception handler for APIError
@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handle structured API errors."""
    logger.error(f"API Error: {exc.code} - {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response().to_dict()
    )


# Global exception handler for unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with structured response."""
    import traceback
    
    error_msg = str(exc)
    logger.error(f"Unhandled exception: {error_msg}\n{traceback.format_exc()}")
    
    # Don't expose full traceback in production
    is_production = os.getenv("RENDER") or os.getenv("RAILWAY_ENVIRONMENT")
    detail = "An internal error occurred" if is_production else traceback.format_exc()
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "code": "INTERNAL_ERROR",
            "message": error_msg if not is_production else "Internal server error",
            "detail": detail,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Include API routes with versioning prefix
app.include_router(router, prefix=f"/api/{API_VERSION}")

# Also include without prefix for backward compatibility
app.include_router(router)


# =============================================================================
# ROOT ENDPOINTS
# =============================================================================

@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "message": "Adaptive Competitive Programming Coach API",
        "version": "2.0.0",
        "api_version": API_VERSION,
        "docs": "/docs",
        "endpoints": {
            "health": "GET /health",
            "get_user": f"GET /api/{API_VERSION}/user/{{handle}}",
            "get_recommendations": f"GET /api/{API_VERSION}/recommend?handle={{handle}}&topic={{topic}}",
            "extension_recommend": f"GET /api/{API_VERSION}/extension/recommend?handle={{handle}}&topic={{topic}}",
            "mark_solved": f"POST /api/{API_VERSION}/solve/{{problem_id}}?handle={{handle}}",
            "list_problems": f"GET /api/{API_VERSION}/problems"
        },
        "note": "Legacy endpoints without /api/v1 prefix are still supported for backward compatibility."
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    cache_stats = user_data_cache.stats()
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "cache": cache_stats
    }


@app.get(f"/api/{API_VERSION}/health")
def health_check_versioned():
    """Versioned health check endpoint."""
    return health_check()
