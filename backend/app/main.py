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


def seed_problems(db):
    """
    Seed the database with sample competitive programming problems.
    Only seeds if the problems table is empty.
    """
    # Check if problems already exist
    if db.query(Problem).first():
        return
    
    # Sample problems covering various topics and ratings
    problems = [
        # Dynamic Programming problems
        {"name": "Frog 1", "rating": 800, "tags": "dp", "url": "https://atcoder.jp/contests/dp/tasks/dp_a", "contest_id": None, "problem_index": None},
        {"name": "Boredom", "rating": 1500, "tags": "dp", "url": "https://codeforces.com/problemset/problem/455/A", "contest_id": 455, "problem_index": "A"},
        {"name": "Vacations", "rating": 1100, "tags": "dp", "url": "https://codeforces.com/problemset/problem/698/A", "contest_id": 698, "problem_index": "A"},
        {"name": "Longest Increasing Subsequence", "rating": 1700, "tags": "dp,binary search", "url": "https://codeforces.com/problemset/problem/340/D", "contest_id": 340, "problem_index": "D"},
        {"name": "Knapsack 1", "rating": 1200, "tags": "dp", "url": "https://atcoder.jp/contests/dp/tasks/dp_d", "contest_id": None, "problem_index": None},
        {"name": "Cut Ribbon", "rating": 1300, "tags": "dp", "url": "https://codeforces.com/problemset/problem/189/A", "contest_id": 189, "problem_index": "A"},
        
        # Graph problems
        {"name": "Building Roads", "rating": 1000, "tags": "graphs,dfs", "url": "https://cses.fi/problemset/task/1666", "contest_id": None, "problem_index": None},
        {"name": "Message Route", "rating": 1200, "tags": "graphs,bfs", "url": "https://cses.fi/problemset/task/1667", "contest_id": None, "problem_index": None},
        {"name": "Graph Connectivity", "rating": 1100, "tags": "graphs,dsu", "url": "https://codeforces.com/problemset/problem/217/A", "contest_id": 217, "problem_index": "A"},
        {"name": "Shortest Routes I", "rating": 1500, "tags": "graphs,dijkstra", "url": "https://cses.fi/problemset/task/1671", "contest_id": None, "problem_index": None},
        {"name": "Bipartiteness Check", "rating": 1400, "tags": "graphs,bfs,dfs", "url": "https://codeforces.com/problemset/problem/862/B", "contest_id": 862, "problem_index": "B"},
        {"name": "Topological Sorting", "rating": 1300, "tags": "graphs,topological sort", "url": "https://cses.fi/problemset/task/1679", "contest_id": None, "problem_index": None},
        
        # Binary Search problems
        {"name": "Binary Search", "rating": 800, "tags": "binary search", "url": "https://codeforces.com/problemset/problem/1539/A", "contest_id": 1539, "problem_index": "A"},
        {"name": "Aggressive Cows", "rating": 1400, "tags": "binary search", "url": "https://www.spoj.com/problems/AGGRCOW/", "contest_id": None, "problem_index": None},
        {"name": "Ropes", "rating": 1200, "tags": "binary search", "url": "https://codeforces.com/problemset/problem/579/B", "contest_id": 579, "problem_index": "B"},
        {"name": "Factory Machines", "rating": 1500, "tags": "binary search", "url": "https://cses.fi/problemset/task/1620", "contest_id": None, "problem_index": None},
        {"name": "K-th Number", "rating": 1600, "tags": "binary search,sorting", "url": "https://codeforces.com/problemset/problem/76/A", "contest_id": 76, "problem_index": "A"},
        
        # Greedy problems
        {"name": "Tasks and Deadlines", "rating": 1100, "tags": "greedy,sorting", "url": "https://cses.fi/problemset/task/1630", "contest_id": None, "problem_index": None},
        {"name": "Minimum Moves", "rating": 900, "tags": "greedy,math", "url": "https://codeforces.com/problemset/problem/681/A", "contest_id": 681, "problem_index": "A"},
        {"name": "Stick Lengths", "rating": 1000, "tags": "greedy,sorting", "url": "https://cses.fi/problemset/task/1074", "contest_id": None, "problem_index": None},
        
        # Math problems
        {"name": "Counting Divisors", "rating": 1100, "tags": "math,number theory", "url": "https://cses.fi/problemset/task/1713", "contest_id": None, "problem_index": None},
        {"name": "Exponentiation", "rating": 1000, "tags": "math,modular arithmetic", "url": "https://cses.fi/problemset/task/1095", "contest_id": None, "problem_index": None},
        {"name": "GCD and LCM", "rating": 900, "tags": "math,number theory", "url": "https://codeforces.com/problemset/problem/858/A", "contest_id": 858, "problem_index": "A"},
        
        # String problems
        {"name": "Palindrome Check", "rating": 800, "tags": "strings", "url": "https://codeforces.com/problemset/problem/131/A", "contest_id": 131, "problem_index": "A"},
        {"name": "Substring Removal", "rating": 1200, "tags": "strings,two pointers", "url": "https://codeforces.com/problemset/problem/1496/A", "contest_id": 1496, "problem_index": "A"},
        {"name": "String Hashing", "rating": 1400, "tags": "strings,hashing", "url": "https://cses.fi/problemset/task/1753", "contest_id": None, "problem_index": None},
        
        # Implementation problems
        {"name": "Watermelon", "rating": 800, "tags": "implementation,math", "url": "https://codeforces.com/problemset/problem/4/A", "contest_id": 4, "problem_index": "A"},
        {"name": "Theatre Square", "rating": 900, "tags": "implementation,math", "url": "https://codeforces.com/problemset/problem/1/A", "contest_id": 1, "problem_index": "A"},
        {"name": "Way Too Long Words", "rating": 800, "tags": "implementation,strings", "url": "https://codeforces.com/problemset/problem/71/A", "contest_id": 71, "problem_index": "A"},
        {"name": "Team", "rating": 800, "tags": "implementation", "url": "https://codeforces.com/problemset/problem/231/A", "contest_id": 231, "problem_index": "A"},
    ]
    
    # Add problems to database
    for p in problems:
        problem = Problem(**p)
        db.add(problem)
    
    db.commit()
    print(f"Seeded {len(problems)} problems to database")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events.
    Creates database tables and seeds sample data on startup.
    """
    # Startup: Create tables and seed data
    Base.metadata.create_all(bind=engine)
    
    # Seed sample problems
    db = SessionLocal()
    try:
        seed_problems(db)
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

if os.getenv("RAILWAY_ENVIRONMENT"):
    logger.info("🚀 Railway Deployment Detected")
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
