"""
Recommendation Engine for Competitive Programming Problems.

This module implements a rating-aware, topic-sensitive problem recommendation
system using heuristic-based logic.

Design Principles:
- Rating-aware: Adjusts difficulty based on user performance
- Topic-sensitive: Filters problems by selected topic
- Extensible: Ready for skill graph and learning velocity integration
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from .models import User, Problem, SolvedProblem, UserSkill


# =============================================================================
# CONSTANTS
# =============================================================================

# Rating bounds for target difficulty clamping
MIN_TARGET_RATING = 800
MAX_TARGET_RATING = 2400

# Difficulty window: how far from target rating to search
DIFFICULTY_WINDOW = 150

# Number of problems to recommend
RECOMMENDATION_LIMIT = 3

# Rating adjustments based on last verdict
RATING_INCREASE_ON_AC = 100
RATING_DECREASE_ON_WA = 50


# =============================================================================
# STEP 1: DETERMINE TARGET DIFFICULTY
# =============================================================================

def get_last_solve_verdict(db: Session, user_id: int) -> Optional[str]:
    """
    Get the verdict of the user's most recent problem attempt.
    
    Args:
        db: Database session
        user_id: User's database ID
        
    Returns:
        "AC" if last solve was accepted, "WA" if wrong answer, None if no history
    """
    last_solve = db.query(SolvedProblem).filter(
        SolvedProblem.user_id == user_id
    ).order_by(desc(SolvedProblem.solved_at)).first()
    
    if last_solve is None:
        return None
    
    return last_solve.verdict


def calculate_target_rating(db: Session, user_id: int, current_rating: int) -> int:
    """
    Calculate target rating based on LAST interaction (Solve OR Skip).
    
    Logic:
    - Solve (AC) + Fast -> +100
    - Solve (AC) + Slow -> +0 (Maintain)
    - Skip (Too Easy) -> +100
    - Skip (Too Hard) -> -100
    - Default/Start -> current_rating
    """
    from .models import SolvedProblem, SkippedProblem
    
    # Get last solve
    last_solve = db.query(SolvedProblem).filter(SolvedProblem.user_id == user_id).order_by(desc(SolvedProblem.solved_at)).first()
    
    # Get last skip
    last_skip = db.query(SkippedProblem).filter(SkippedProblem.user_id == user_id).order_by(desc(SkippedProblem.skipped_at)).first()
    
    # Determine which was more recent
    solve_time = last_solve.solved_at if last_solve else datetime.min
    skip_time = last_skip.skipped_at if last_skip else datetime.min
    
    target = current_rating
    
    if solve_time > skip_time:
        # Last action was a Solve
        if last_solve.verdict == "AC":
            # Check for slowness
            if last_solve.is_slow_solve:
                target += 0  # Maintain level to practice
            else:
                target += 100 # Standard progression
        else:
            target -= 50 # WA
            
    elif skip_time > solve_time:
        # Last action was a Skip
        if last_skip.feedback == "too_easy":
            target += 100
        elif last_skip.feedback == "too_hard":
            target -= 100
        else:
             target += 0 # Neutral skip
             
    else:
        # No history
        target = current_rating
        
    return max(MIN_TARGET_RATING, min(MAX_TARGET_RATING, target))


# =============================================================================
# STEP 2 & 3: TOPIC AND DIFFICULTY FILTERING
# =============================================================================

def filter_problems_by_topic_and_difficulty(
    db: Session,
    topic: str,
    target_rating: int,
    window: int = DIFFICULTY_WINDOW
) -> List[Problem]:
    """
    Get problems matching topic within difficulty window.
    
    Filters:
    - Problem.tags contains selected_topic
    - abs(problem.rating - target_rating) <= window
    
    Args:
        db: Database session
        topic: Selected topic/tag to filter by
        target_rating: Center of difficulty window
        window: How far from target to search (default: 150)
        
    Returns:
        List of matching problems (unordered)
        
    # TODO: Integrate skill graph here
    # - Consider prerequisite topics
    # - Boost problems that strengthen weak areas
    """
    min_rating = target_rating - window
    max_rating = target_rating + window
    
    return db.query(Problem).filter(
        Problem.tags.ilike(f"%{topic.lower()}%"),
        Problem.rating >= min_rating,
        Problem.rating <= max_rating
    ).all()


# =============================================================================
# STEP 4: SOLVE HISTORY FILTER
# =============================================================================

def get_solved_problem_ids(db: Session, user_id: int) -> List[int]:
    """
    Get list of problem IDs already solved by the user.
    
    Args:
        db: Database session
        user_id: User's database ID
        
    Returns:
        List of solved problem IDs
    """
    solved = db.query(SolvedProblem.problem_id).filter(
        SolvedProblem.user_id == user_id
    ).all()
    
    return [s[0] for s in solved]


def exclude_solved_problems(
    problems: List[Problem],
    solved_ids: List[int]
) -> List[Problem]:
    """
    Remove already-solved problems from the candidate list.
    
    Args:
        problems: List of candidate problems
        solved_ids: List of problem IDs to exclude
        
    Returns:
        Filtered list with solved problems removed
    """
    if not solved_ids:
        return problems
    
    return [p for p in problems if p.id not in solved_ids]


# Number of problems to solve before re-showing a skipped problem
SKIP_COOLDOWN_COUNT = 10


def get_recently_skipped_ids(db: Session, user_id: int) -> List[int]:
    """
    Get problem IDs that were skipped and haven't had enough solves since.
    
    A skipped problem becomes eligible for re-recommendation after the user
    has solved at least SKIP_COOLDOWN_COUNT problems since the skip.
    
    Args:
        db: Database session
        user_id: User's database ID
        
    Returns:
        List of problem IDs to exclude (recently skipped)
    """
    from .models import SkippedProblem
    
    # Get the timestamp of the Nth most recent solve
    recent_solves = db.query(SolvedProblem.solved_at).filter(
        SolvedProblem.user_id == user_id
    ).order_by(desc(SolvedProblem.solved_at)).limit(SKIP_COOLDOWN_COUNT).all()
    
    if len(recent_solves) < SKIP_COOLDOWN_COUNT:
        # Not enough solves yet, exclude ALL skipped problems
        skipped = db.query(SkippedProblem.problem_id).filter(
            SkippedProblem.user_id == user_id
        ).all()
        return [s[0] for s in skipped]
    
    # Get the cutoff time (10th most recent solve)
    cutoff_time = recent_solves[-1][0]
    
    # Exclude problems skipped AFTER the cutoff time
    skipped = db.query(SkippedProblem.problem_id).filter(
        SkippedProblem.user_id == user_id,
        SkippedProblem.skipped_at > cutoff_time
    ).all()
    
    return [s[0] for s in skipped]


# =============================================================================
# STEP 5: RANKING LOGIC
# =============================================================================

def rank_problems_by_distance(
    problems: List[Problem],
    target_rating: int,
    limit: int = RECOMMENDATION_LIMIT
) -> List[Problem]:
    """
    Sort problems by distance from target rating (closest first).
    
    Args:
        problems: List of candidate problems
        target_rating: Target rating for distance calculation
        limit: Maximum number of problems to return
        
    Returns:
        Top N problems sorted by rating distance
        
    # TODO: Integrate additional ranking factors
    # - Problem popularity/quality score
    # - Time since last attempt on similar problems
    """
    # MVP ranking: prioritize closeness to target difficulty
    # Future: add problem quality, recency, pattern similarity
    sorted_problems = sorted(
        problems,
        key=lambda p: abs(p.rating - target_rating)
    )
    
    return sorted_problems[:limit]


# =============================================================================
# MAIN RECOMMENDATION FUNCTION
# =============================================================================

def recommend_problems(
    db: Session,
    user: User,
    topic: str
) -> Tuple[List[Problem], int, Optional[str]]:
    """
    Generate problem recommendations for a user.
    
    Pipeline:
    1. Determine target difficulty from last solve verdict
    2. Filter problems by topic
    3. Filter problems by difficulty window (±150)
    4. Exclude already-solved problems
    5. Rank by distance from target rating
    6. Return top 3 problems
    
    Args:
        db: Database session
        user: User requesting recommendations
        topic: Selected topic/tag to filter by
        
    Returns:
        Tuple of (problems, target_rating, message)
        - problems: List of up to 3 recommended problems
        - target_rating: The calculated target rating
        - message: Optional info message (e.g., fallback notification)
    """
    # Step 1: Determine target difficulty (Adaptive)
    from datetime import datetime # Import needed for func
    target_rating = calculate_target_rating(db, user.id, user.rating)
    
    # Step 2 & 3: Filter by topic and difficulty
    candidates = filter_problems_by_topic_and_difficulty(db, topic, target_rating)
    
    # Step 4: Exclude solved problems
    solved_ids = get_solved_problem_ids(db, user.id)
    candidates = exclude_solved_problems(candidates, solved_ids)
    
    # Step 4b: Exclude recently skipped problems
    skipped_ids = get_recently_skipped_ids(db, user.id)
    candidates = [p for p in candidates if p.id not in skipped_ids]
    
    # Step 5: Rank and limit
    # Get Top 5 candidates for AI selection
    ranked_candidates = rank_problems_by_distance(candidates, target_rating, limit=5)
    
    # Step 6: AI Selection
    # Convert to dicts first
    candidate_dicts = problems_to_dicts_with_explanations(ranked_candidates, target_rating)
    
    from .ai_coach import select_best_problem
    best_problem = select_best_problem(candidate_dicts, {
        "rating": user.rating,
        "weak_topics": [] # TODO: Pass real weak topics if available
    })
    
    # Return as list (ensure at least 1)
    final_recs = [best_problem] if best_problem else []
    
    # If no problems found, try fallback
    message = None
    if not final_recs:
        recs, message = _fallback_to_easiest(db, topic, solved_ids, target_rating)
        final_recs = problems_to_dicts_with_explanations(recs, target_rating)
    
    return final_recs, target_rating, message


def problems_to_dicts_with_explanations(
    problems: List[Problem],
    target_rating: int
) -> List[dict]:
    """
    Convert ORM Problem objects to API-friendly dicts with explanations.
    
    Args:
        problems: List of Problem ORM objects
        target_rating: Target rating for explanation generation
        
    Returns:
        List of dicts with id, name, rating, tags, url, and explanation
    """
    return [
        {
            "id": p.id,
            "name": p.name,
            "rating": p.rating,
            "tags": p.tags,
            "url": p.url,
            "explanation": explain_recommendation(p, target_rating)
        }
        for p in problems
    ]


def _fallback_to_easiest(
    db: Session,
    topic: str,
    solved_ids: List[int],
    target_rating: int
) -> Tuple[List[Problem], str]:
    """
    Fallback: Return easiest unsolved problems when no matches in range.
    
    Args:
        db: Database session
        topic: Selected topic/tag
        solved_ids: Problem IDs to exclude
        target_rating: Original target rating (for message)
        
    Returns:
        Tuple of (problems, message)
    """
    query = db.query(Problem).filter(
        Problem.tags.ilike(f"%{topic.lower()}%")
    )
    
    if solved_ids:
        query = query.filter(Problem.id.notin_(solved_ids))
    
    problems = query.order_by(Problem.rating.asc()).limit(RECOMMENDATION_LIMIT).all()
    
    min_range = max(MIN_TARGET_RATING, target_rating - DIFFICULTY_WINDOW)
    max_range = min(MAX_TARGET_RATING, target_rating + DIFFICULTY_WINDOW)
    message = f"No problems in target range ({min_range}-{max_range}). Showing easiest available."
    
    return problems, message


# =============================================================================
# SOLVE TRACKING
# =============================================================================

def record_solve(
    db: Session,
    user_id: int,
    problem_id: int,
    verdict: str = "AC",
    time_taken: Optional[int] = None,
    is_slow: bool = False
) -> Optional[SolvedProblem]:
    """
    Record a problem solve attempt.
    """
    # Check if already recorded
    existing = db.query(SolvedProblem).filter(
        SolvedProblem.user_id == user_id,
        SolvedProblem.problem_id == problem_id
    ).first()
    
    if existing:
        existing.verdict = verdict
        if time_taken:
            existing.time_taken_seconds = time_taken
            existing.is_slow_solve = is_slow
        db.commit()
        return existing
    
    solve_record = SolvedProblem(
        user_id=user_id,
        problem_id=problem_id,
        verdict=verdict,
        time_taken_seconds=time_taken,
        is_slow_solve=is_slow
    )
    db.add(solve_record)
    
    if verdict == "AC":
        problem = db.query(Problem).filter(Problem.id == problem_id).first()
        if problem:
            _update_user_skills(db, user_id, problem.tags)
    
    db.commit()
    db.refresh(solve_record)
    return solve_record


def _update_user_skills(db: Session, user_id: int, tags: str) -> None:
    """
    Update skill counters for each topic in the problem's tags.
    Called only for AC verdicts.
    
    Args:
        db: Database session
        user_id: User's database ID
        tags: Comma-separated problem tags
    """
    from datetime import datetime
    
    # Parse tags (comma-separated)
    topics = [t.strip().lower() for t in tags.split(",") if t.strip()]
    
    for topic in topics:
        # Find or create skill record for this topic
        skill = db.query(UserSkill).filter(
            UserSkill.user_id == user_id,
            UserSkill.topic == topic
        ).first()
        
        if skill:
            # Increment existing skill counter
            skill.solve_count += 1
            skill.last_practiced_at = datetime.utcnow()
        else:
            # Create new skill record
            skill = UserSkill(
                user_id=user_id,
                topic=topic,
                solve_count=1
            )
            db.add(skill)


# =============================================================================
# EXPLANATION HELPER
# =============================================================================

def explain_recommendation(problem: Problem, target_rating: int) -> str:
    """
    Generate a human-readable explanation for why a problem was recommended.
    
    Args:
        problem: The recommended problem
        target_rating: The user's target rating
        
    Returns:
        Explanation string for inclusion in API response
        
    # TODO: Enhance with more context
    # - Topic match strength
    # - Skill gap analysis
    # - Learning path position
    """
    distance = abs(problem.rating - target_rating)
    
    if distance == 0:
        match_desc = "exactly matches"
    elif distance <= 50:
        match_desc = "closely matches"
    elif distance <= 100:
        match_desc = "is near"
    else:
        match_desc = "is within range of"
    
    return (
        f"Recommended because its rating ({problem.rating}) "
        f"{match_desc} your target difficulty ({target_rating})."
    )

