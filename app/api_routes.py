"""
API routes for the CP Coach application.
Defines endpoints for user management and problem recommendations.
"""

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, Problem
from .schemas import UserResponse, RecommendationResponse, ProblemResponse
from .recommender import recommend_problems, record_solve, sync_user_solved_history

# Create router instance
router = APIRouter()

# Codeforces API base URL
CODEFORCES_API_URL = "https://codeforces.com/api"


def fetch_codeforces_user(handle: str) -> dict:
    """
    Fetch user information from Codeforces API.
    
    Args:
        handle: Codeforces username
        
    Returns:
        User data dictionary from Codeforces
        
    Raises:
        HTTPException: If user not found or API error
    """
    try:
        response = requests.get(
            f"{CODEFORCES_API_URL}/user.info",
            params={"handles": handle},
            timeout=10
        )
        data = response.json()
        
        if data.get("status") != "OK":
            raise HTTPException(
                status_code=404,
                detail=f"User '{handle}' not found on Codeforces"
            )
        
        return data["result"][0]
    
    except requests.RequestException as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Codeforces API: {str(e)}"
        )


@router.get("/user/{handle}")
def get_user(handle: str, db: Session = Depends(get_db)):
    """
    Fetch user rating from Codeforces and store/update in database.
    
    Args:
        handle: Codeforces username
        db: Database session (injected)
        
    Returns:
        User profile with rating information
    """
    # Fetch from Codeforces API
    cf_user = fetch_codeforces_user(handle)
    
    # Extract rating (default to 0 for unrated users)
    rating = cf_user.get("rating", 0)
    
    # Check if user exists in database
    db_user = db.query(User).filter(User.handle == handle).first()
    
    if db_user:
        # Update existing user's rating
        db_user.rating = rating
        db.commit()
        db.refresh(db_user)
    else:
        # Create new user
        db_user = User(handle=handle, rating=rating)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    
    # Sync recent solves from Codeforces
    try:
        from .weakness_analysis import fetch_user_submissions
        from .recommender import sync_user_solved_history
        
        # Fetch significant history to ensure we exclude all solved problems
        # 1000 is a reasonable balance between speed and coverage for most active users
        recent_subs = fetch_user_submissions(handle, count=1000) 
        
        if recent_subs:
            # Full sync (SolvedProblem + UserSkill max rating)
            sync_user_solved_history(db, db_user.id, recent_subs)
            
            # We don't need the manual "check for solves today" block anymore 
            # because sync_user_solved_history handles all SolvedProblem entries with correct timestamps.
            # But we DO need to ensure daily count calculation is still correct below.
            
    except Exception as e:
        print(f"Sync error (non-fatal): {e}")

    # Calculate daily solved count
    from .models import SolvedProblem
    from datetime import datetime
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    daily_count = db.query(SolvedProblem).filter(
        SolvedProblem.user_id == db_user.id,
        SolvedProblem.solved_at >= today_start,
        SolvedProblem.verdict == "AC"
    ).count()
    
    # Return explicit dict to ensure daily_solved_count is included
    # (Bypasses potential Pydantic/ORM attribute patching issues)
    return {
        "id": db_user.id,
        "handle": db_user.handle,
        "rating": db_user.rating,
        "daily_solved_count": daily_count,
        "created_at": db_user.created_at,
        "last_problem_solved": db_user.last_problem_solved
    }


@router.get("/admin/refresh-problems")
def force_refresh_problems(db: Session = Depends(get_db)):
    """
    Admin: Force fetch problems from Codeforces.
    Useful if the specific problem set is missing or stale.
    """
    from .main import fetch_and_store_problems
    try:
        fetch_and_store_problems(db)
        return {"message": "Problem fetch triggered successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommend", response_model=RecommendationResponse)
def get_recommendations(
    handle: str = Query(..., description="Codeforces handle"),
    topic: str = Query(..., description="Topic/tag to filter problems"),
    db: Session = Depends(get_db)
):
    """
    Get problem recommendations for a user based on topic and rating.
    
    Args:
        handle: Codeforces username
        topic: Topic/tag to filter problems (e.g., 'dp', 'graphs')
        db: Database session (injected)
        
    Returns:
        List of recommended problems with target rating info
    """
    # Get user from database
    db_user = db.query(User).filter(User.handle == handle).first()
    
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail=f"User '{handle}' not found. Please fetch user profile first using GET /user/{handle}"
        )
    
    # Get recommendations (returns list of dicts with explanations)
    problems, target_rating, message = recommend_problems(db, db_user, topic)
    
    # Build response - problems already contain explanations
    return RecommendationResponse(
        target_rating=target_rating,
        message=message or (f"No problems found for topic '{topic}'" if not problems else None),
        problems=problems
    )


@router.post("/solve/{problem_id}")
def submit_solve(
    problem_id: int,
    handle: str = Query(..., description="Codeforces handle"),
    verdict: str = Query("AC", description="Verdict: 'AC' (Accepted) or 'WA' (Wrong Answer)"),
    time_taken: int = Query(None, description="Time taken in seconds to solve"),
    db: Session = Depends(get_db)
):
    """
    Record a problem solve attempt with verdict.
    Analyzes performance if time_taken is provided.
    """
    # Validate verdict
    if verdict not in ["AC", "WA"]:
        raise HTTPException(status_code=400, detail="Verdict must be 'AC' or 'WA'")
    
    # Get user
    db_user = db.query(User).filter(User.handle == handle).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get problem
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
        
    # AI Performance Analysis
    is_slow = False
    ai_advice = None
    
    if verdict == "AC" and time_taken:
        from .ai_coach import analyze_performance
        analysis = analyze_performance({
            "rating": problem.rating,
            "tags": problem.tags
        }, time_taken)
        is_slow = analysis.get("is_slow", False)
        ai_advice = analysis.get("advice")
    
    # Record solve
    record_solve(db, db_user.id, problem_id, verdict, time_taken, is_slow)
    
    return {
        "message": f"Recorded {verdict}", 
        "ai_analysis": {
            "is_slow": is_slow,
            "advice": ai_advice
        }
    }


@router.post("/skip/{problem_id}")
def skip_problem(
    problem_id: int,
    handle: str = Query(..., description="Codeforces handle"),
    feedback: str = Query(None, regex="^(too_easy|too_hard)$"),
    db: Session = Depends(get_db)
):
    """
    Skip a problem (too easy). Tracks skip count per problem.
    
    Behavior:
    - First skip: Save to skipped_problems, recommend again after 10 other problems
    - Second skip (same problem): Auto-mark as solved (user considers it too easy)
    
    Args:
        problem_id: ID of the problem to skip
        handle: Codeforces username
        db: Database session (injected)
        
    Returns:
        Message indicating skip recorded or auto-marked as solved
    """
    from .models import SkippedProblem
    from datetime import datetime
    
    # Get user
    db_user = db.query(User).filter(User.handle == handle).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get problem
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    
    # Check for existing skip record
    existing_skip = db.query(SkippedProblem).filter(
        SkippedProblem.user_id == db_user.id,
        SkippedProblem.problem_id == problem_id
    ).first()
    
    if existing_skip:
        # Already skipped once - confirm done
        existing_skip.skip_count += 1
        existing_skip.skipped_at = datetime.utcnow()
        
        # Immediate auto-solve on any repeat
        record_solve(db, db_user.id, problem_id, "AC")
        db.commit()
        return {"message": f"Skipped - marked '{problem.name}' as done", "auto_solved": True}
    else:
        # First skip - mark as done immediately per user request (User Experience decision)
        # We record it as solved to remove from pool permanently
        
        # 1. Record fake solve first (so it happens "before" the skip)
        record_solve(db, db_user.id, problem_id, "AC")
        
        # 2. Record skip with refined timestamp to ensure it's treated as the LATEST action
        from datetime import timedelta
        # Ensure skip is strictly "later" than the solve we just recorded
        # This guarantees calculate_target_rating sees the Skip (and its feedback) as the last interaction
        skip_record = SkippedProblem(
            user_id=db_user.id,
            problem_id=problem_id,
            skip_count=1,
            feedback=feedback,
            skipped_at=datetime.utcnow() + timedelta(seconds=1) 
        )
        db.add(skip_record)
        
        db.commit()
        return {"message": f"Skipped & marked '{problem.name}' as done", "auto_solved": True}


@router.get("/problems", response_model=list[ProblemResponse])
def list_problems(
    topic: str = Query(None, description="Filter by topic/tag"),
    db: Session = Depends(get_db)
):
    """
    List all available problems, optionally filtered by topic.
    
    Args:
        topic: Optional topic/tag to filter problems
        db: Database session (injected)
        
    Returns:
        List of problems
    """
    query = db.query(Problem)
    
    if topic:
        query = query.filter(Problem.tags.contains(topic.lower()))
    
    return query.all()


# =============================================================================
# EXTENSION ENDPOINTS
# =============================================================================

@router.get("/extension/recommend", response_model=RecommendationResponse)
def extension_recommend(
    handle: str = Query(..., description="Codeforces handle"),
    topic: str = Query(..., description="Topic/tag to filter problems"),
    rating_offset: int = Query(0, description="Manual rating adjustment (-100 for easier, +100 for harder)"),
    db: Session = Depends(get_db)
):
    """
    Extension-friendly recommendation endpoint.
    
    Designed for browser extensions to fetch recommendations.
    Stateless and reuses the same logic as /recommend.
    
    TODO: Add rate limiting per extension/user
    TODO: Restrict to verified extension origin in production
    TODO: Consider caching for performance
    
    Args:
        handle: Codeforces username
        topic: Topic/tag to filter problems
        rating_offset: Manual adjustment to target rating (default 0)
        db: Database session (injected)
        
    Returns:
        RecommendationResponse with problems and explanations
    """
    # Get user from database
    db_user = db.query(User).filter(User.handle == handle).first()
    
    if not db_user:
        raise HTTPException(
            status_code=404,
            detail=f"User '{handle}' not found. Please register first using GET /user/{handle}"
        )
    
    # Reuse existing recommendation logic - with rating offset applied
    problems, target_rating, message = recommend_problems(db, db_user, topic, rating_offset=rating_offset)
    
    # Calculate daily solved count
    from datetime import datetime
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    from .models import SolvedProblem
    daily_count = db.query(SolvedProblem).filter(
        SolvedProblem.user_id == db_user.id,
        SolvedProblem.solved_at >= today_start,
        SolvedProblem.verdict == "AC"
    ).count()
    
    # Add badge to message (temporary UI hack until schema updated)
    # Frontend can parse this or display as is
    final_message = message or ""
    if not final_message:
         final_message = f"Top picks for {topic}"
         
    return RecommendationResponse(
        target_rating=target_rating,
        message=final_message,
        problems=problems,
        # TODO: Add explicit daily_count field to schema
        daily_count=daily_count 
    )


# =============================================================================
# WEAKNESS ANALYSIS ENDPOINTS
# =============================================================================

@router.get("/analysis/weaknesses")
def get_weakness_analysis(
    handle: str = Query(..., description="Codeforces handle"),
    sync: bool = Query(True, description="Sync latest submissions first"),
    refresh: bool = Query(False, description="Refresh/shuffle upsolve suggestions"),
    db: Session = Depends(get_db)
):
    """
    Analyze user's weak areas and suggest upsolving candidates.
    
    This endpoint:
    1. Fetches recent contest submissions (if sync=True)
    2. Detects weak rating bands (deterministic)
    3. Detects weak topics (deterministic)
    4. Identifies upsolving candidates
    5. Generates AI explanation (Gemini)
    
    Args:
        handle: Codeforces username
        sync: Whether to sync latest submissions first
        db: Database session
        
    Returns:
        Weakness analysis with AI explanation and upsolve suggestions
    """
    from .models import UserContestProblemStat
    from .weakness_analysis import (
        fetch_user_submissions,
        sync_contest_stats,
        detect_weak_rating_bands,
        detect_weak_topics,
        get_upsolve_candidates,
        prepare_weakness_summary
    )
    from .ai_coach import generate_weakness_explanation, generate_upsolve_reason
    
    # Get or create user
    db_user = db.query(User).filter(User.handle == handle).first()
    if not db_user:
        # Fetch from Codeforces
        cf_user = fetch_codeforces_user(handle)
        rating = cf_user.get("rating", 0)
        db_user = User(handle=handle, rating=rating)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
    
    # Sync contest submissions if requested
    if sync:
        submissions = fetch_user_submissions(handle, count=500) # Increased count for better sync
        if submissions:
             # Sync contest stats (for weakness analysis)
            sync_contest_stats(db, db_user, submissions)
            
            # Sync solved history (for recommender and exclusion)
            from .recommender import sync_user_solved_history
            sync_user_solved_history(db, db_user.id, submissions)
            
    # Get total stats for summary
    total_stats = db.query(UserContestProblemStat).filter(
        UserContestProblemStat.user_id == db_user.id,
        UserContestProblemStat.attempted == True
    ).all()
    
    total_attempted = len(total_stats)
    total_solved = sum(1 for s in total_stats if s.solved)
    
    # Run deterministic analysis
    weak_bands = detect_weak_rating_bands(db, db_user.id)
    weak_topics = detect_weak_topics(db, db_user.id)
    upsolve_candidates = get_upsolve_candidates(
        db, db_user.id, db_user.rating, weak_bands, weak_topics
    )
    
    # Shuffle for refresh if requested (randomize top candidates)
    import random
    if refresh:
        # Keep top 15 candidates relevant but shuffle them
        top_candidates = upsolve_candidates[:15]
        random.shuffle(top_candidates)
        # Re-sort slightly by score to ensure quality isn't totally lost?
        # No, pure shuffle of good candidates is better for variety.
        upsolve_candidates = top_candidates + upsolve_candidates[15:]
    
    # Prepare summary for AI (using UN-shuffled data for stable cache hash usually? 
    # Actually upsolve_candidates list in summary affects hash. 
    # But we implemented stable hash in previous step! So we are safe.)
    summary = prepare_weakness_summary(
        user_rating=db_user.rating,
        weak_bands=weak_bands,
        weak_topics=weak_topics,
        upsolve_candidates=upsolve_candidates,
        total_attempted=total_attempted,
        total_solved=total_solved
    )
    
    # AI Explanation with Caching (Stable Hash Logic from previous step is here)
    from .models import UserAnalysisCache
    import hashlib
    import json
    from datetime import datetime, timedelta

    ai_explanation = ""
    
    # Calculate hash on STABLE data (exclude specific upsolve candidates)
    stable_summary_data = {
        "user_rating": summary["user_rating"],
        "overall_solved_rate": summary["overall_solved_rate"],
        "weak_rating_bands": summary["weak_rating_bands"],
        "weak_topics": summary["weak_topics"]
    }
    summary_hash = hashlib.md5(json.dumps(stable_summary_data, sort_keys=True).encode()).hexdigest()
    
    # Check cache
    cache = db.query(UserAnalysisCache).filter(UserAnalysisCache.user_id == db_user.id).first()
    use_cache = False
    
    if cache:
        if cache.summary_hash == summary_hash:
            use_cache = True
        elif cache.created_at > datetime.utcnow() - timedelta(hours=24):
             use_cache = True
             
    if use_cache and cache.explanation and "Error" not in cache.explanation:
        ai_explanation = cache.explanation
    elif total_attempted > 0:
        # Try to fetch fresh explanation
        explanation = generate_weakness_explanation(summary)
        
        if "API error" in explanation or "unavailable" in explanation:
             if cache and cache.explanation:
                 ai_explanation = f"{cache.explanation}\n\n(Note: Cached insight shown due to high traffic)"
             else:
                 ai_explanation = explanation
        else:
            ai_explanation = explanation
            if not cache:
                cache = UserAnalysisCache(user_id=db_user.id)
                db.add(cache)
            
            cache.summary_hash = summary_hash
            cache.explanation = explanation
            cache.created_at = datetime.utcnow()
            db.commit()
    else:
        ai_explanation = "No contest data available yet. Participate in rated contests to get personalized weakness analysis."

    # Build response
    return {
        "handle": handle,
        "rating": db_user.rating,
        "contests_analyzed": len(set(s.contest_id for s in total_stats)),
        "problems_attempted": total_attempted,
        "problems_solved": total_solved,
        "weak_rating_bands": [b["band"] for b in weak_bands],
        "weak_topics": [t["topic"] for t in weak_topics],
        "weak_band_details": weak_bands[:3],
        "weak_topic_details": weak_topics[:5],
        "summary_explanation": ai_explanation,
        "upsolve_suggestions": [
            {
                "problem_id": c["problem_id"],
                "contest_id": c["contest_id"],
                "db_id": c.get("db_id"),  # Pass DB ID for actions
                "name": c["name"],
                "rating": c["rating"],
                "tags": c["tags"],
                "url": c["url"],
                "reason": generate_upsolve_reason(c)
            }
            for c in upsolve_candidates[:5] # Limit to 5
        ]
    }
