"""
Recommendation Engine for Competitive Programming Problems.

This module implements a rating-aware, topic-sensitive problem recommendation
system using heuristic-based logic.

Design Principles:
- Deterministic: Same input always produces same output
- Rating-aware: Adjusts difficulty based on user performance
- Topic-sensitive: Filters problems by selected topic
- Extensible: Ready for skill graph and learning velocity integration
"""

from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from .models import User, Problem, SolvedProblem, UserSkill
from .config import (
    DIFFICULTY_WINDOW,
    RECOMMENDATION_LIMIT,
    RATING_INCREASE_ON_AC,
    RATING_DECREASE_ON_WA,
    SKIP_COOLDOWN_COUNT,
    MAX_RECOMMENDATIONS_PER_TOPIC,
    normalize_tags,
)


# =============================================================================
# CONSTANTS
# =============================================================================

# Rating bounds for target difficulty clamping
MIN_TARGET_RATING = 800
MAX_TARGET_RATING = 2400


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
        # PROGRESSIVE OVERLOAD: Base target on the problem rating you just solved, not your user rating
        base_rating = last_solve.problem.rating if last_solve and last_solve.problem else current_rating
        
        # Fallback: if problem rating is very low (e.g. 800) but user is 1500, use user rating max
        # Actually, if they chose to solve an 800, maybe they want to build up?
        # Let's take max(current_rating, base_rating) to avoid dropping too low?
        # No, if a 1500 user solves an 800 efficiently, they should probably get ~1000 next, not 1600 immediately.
        # But if they are 1500, giving them 900 is annoying.
        # Compromise: Base on current_rating mostly, but use problem_rating to prove competence.
        # Let's use max(current_rating, base_rating) as the "proven level".
        
        proven_level = max(current_rating, base_rating)

        if last_solve.verdict == "AC":
            # Check for slowness
            if last_solve.is_slow_solve:
                target = proven_level + 0  # Maintain level to practice
            else:
                target = proven_level + 100 # Standard progression
        else:
            target = proven_level - 50 # WA
            
    elif skip_time > solve_time:
        # Last action was a Skip
        # PROGRESSIVE SKIP: If it's too easy, base it on the PROBLEM'S rating, not the user's.
        skip_base_rating = last_skip.problem.rating if last_skip and last_skip.problem else current_rating
        
        if last_skip.feedback == "too_easy":
            # If they say a 1200 is too easy, give them 1300 -- even if they are rated 800.
            # Use max(current, problem) to ensure we go UP.
            proven_skip_level = max(current_rating, skip_base_rating)
            target = proven_skip_level + 100
            
        elif last_skip.feedback == "too_hard":
            # If they say 1200 is too hard, they likely want 1100.
            # Don't drop them to 800 (User rating) if they are trying 1200.
            # Gentle step down.
            
            # Use skip_base_rating - 100
            # But ensure we don't go below what might be reasonable?
            target = skip_base_rating - 100
            
        else:
             target = current_rating # Neutral skip
             
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


# Skip cooldown imported from config


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
    # Deterministic ranking: prioritize closeness to target difficulty
    # Use problem ID as secondary sort key for stable, reproducible ordering
    # This ensures same user gets same results within cache TTL
    
    sorted_problems = sorted(
        problems,
        key=lambda p: (abs(p.rating - target_rating), p.id)
    )
    
    return sorted_problems[:limit]


# =============================================================================
# MAIN RECOMMENDATION FUNCTION
# =============================================================================

def recommend_problems(
    db: Session,
    user: User,
    topic: str,
    rating_offset: int = 0
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
        rating_offset: Manual adjustment to target rating (default 0)
        
    Returns:
        Tuple of (problems, target_rating, message)
        - problems: List of up to 3 recommended problems
        - target_rating: The calculated target rating
        - message: Optional info message (e.g., fallback notification)
    """
    # Step 1: Determine target difficulty (Adaptive)
    from datetime import datetime # Import needed for func
    from .models import UserSkill
    
    base_target = calculate_target_rating(db, user.id, user.rating)
    
    # Step 1b: Progressive Overload per Topic
    # Ensure target is at least the max rating solved for this topic
    skill_record = db.query(UserSkill).filter(
        UserSkill.user_id == user.id,
        UserSkill.topic == topic.lower()
    ).first()
    
    topic_max = skill_record.max_solved_rating if skill_record else 0
    
    # Principle: "Same or higher level"
    # Logic: Target should be at least (topic_max). 
    # But if they just solved topic_max, maybe +100?
    # User said: "next time the user gets same or higher level problem"
    # So if they solved 1200, recommender should NOT show 1000. It should show >= 1200.
    
    target_rating = max(base_target, topic_max)
    
    # Step 1c: Apply manual rating offset (for user-controlled adjustment)
    target_rating = target_rating + rating_offset
    target_rating = max(MIN_TARGET_RATING, min(MAX_TARGET_RATING, target_rating))
    
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
            _update_user_skills_with_rating(db, user_id, problem.tags, problem.rating)
    
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
    
    for topic in topics:
        # Find or create skill record for this topic
        skill = db.query(UserSkill).filter(
            UserSkill.user_id == user_id,
            UserSkill.topic == topic
        ).first()
        
        problem_rating = 0
        problem = db.query(Problem).filter(Problem.tags.ilike(f"%{topic}%"), Problem.tags == tags).first() # Approximation
        # Better: get rating from caller or re-query problem. 
        # Actually, caller record_solve has access to problem. Let's rely on that if we change signature, 
        # but here we only have tags. 
        # Let's fix record_solve to pass rating or problem object? 
        # Easier: In this function we don't have problem object easily.
        # But wait, record_solve passed 'tags' from problem object.
        # Let's use a simpler heuristic: we need the problem rating to update max_solved_rating.
        # Check if we can get it.
        pass 

def _update_user_skills_with_rating(db: Session, user_id: int, tags: str, rating: int) -> None:
    """
    Update skill counters and max rating for each topic.
    """
    # Parse tags (comma-separated)
    topics = [t.strip().lower() for t in tags.split(",") if t.strip()]
    
    for topic in topics:
        # Find or create skill record for this topic
        skill = db.query(UserSkill).filter(
            UserSkill.user_id == user_id,
            UserSkill.topic == topic
        ).first()
        
        if skill:
            skill.solve_count += 1
            skill.last_practiced_at = datetime.utcnow()
            if rating > skill.max_solved_rating:
                skill.max_solved_rating = rating
        else:
            skill = UserSkill(
                user_id=user_id,
                topic=topic,
                solve_count=1,
                max_solved_rating=rating
            )
            db.add(skill)


def sync_user_solved_history(db: Session, user_id: int, submissions: List[dict]) -> int:
    """
    Sync full solve history from Codeforces submissions.
    Updates SolvedProblem and UserSkill (max_solved_rating).
    """
    from .models import Problem, UserSkill, SolvedProblem
    
    # 1. Filter for AC submissions
    ac_subs = [s for s in submissions if s.get("verdict") == "OK"]
    if not ac_subs:
        return 0
        
    # 2. Get all local problems (for fast lookup)
    # Optimization: If too many problems, query by contest_id set?
    # For now, fetching all IDs is okay if < 10k. 
    # Better: Query matching contest IDs.
    contest_ids = set(s.get("contestId") for s in ac_subs if s.get("contestId"))
    local_problems = db.query(Problem).filter(Problem.contest_id.in_(contest_ids)).all()
    
    # Map (contest_id, index) -> Problem
    prob_map = {(p.contest_id, p.problem_index): p for p in local_problems}
    
    # 3. Get existing solved IDs to avoid duplicates
    existing_solved = set(
        id_tupl[0] 
        for id_tupl in db.query(SolvedProblem.problem_id).filter(SolvedProblem.user_id == user_id).all()
    )
    
    # 4. Prepare updates
    new_solves = []
    skills_update = {} # topic -> max_rating
    
    count = 0
    for sub in ac_subs:
        cid = sub.get("contestId")
        idx = sub.get("problem", {}).get("index")
        
        if (cid, idx) in prob_map:
            prob = prob_map[(cid, idx)]
            
            # Update Skill Max Rating (even if already solved, check if we missed max rating update?)
            # No, if we solved it, we likely recorded it. But for sync, let's just track max rating from all ACs.
            if prob.tags:
                rating = prob.rating
                tags = [t.strip().lower() for t in prob.tags.split(",") if t.strip()]
                for t in tags:
                    skills_update[t] = max(skills_update.get(t, 0), rating)
            
            if prob.id not in existing_solved:
                # Add to SolvedProblem
                new_solves.append(SolvedProblem(
                    user_id=user_id,
                    problem_id=prob.id,
                    verdict="AC",
                    solved_at=datetime.fromtimestamp(sub.get("creationTimeSeconds", 0))
                ))
                existing_solved.add(prob.id)
                count += 1
                
    # 5. Commit SolvedProblems
    if new_solves:
        db.bulk_save_objects(new_solves)
        
    # 6. Commit Skill Updates
    for topic, max_rating in skills_update.items():
        skill = db.query(UserSkill).filter(UserSkill.user_id == user_id, UserSkill.topic == topic).first()
        if skill:
            skill.solve_count += 0 # Don't recount blindly, this is tricky. 
            # Actually, we don't know if we counted it before. 
            # Safe bet: Just update max_solved_rating if higher.
            if max_rating > skill.max_solved_rating:
                skill.max_solved_rating = max_rating
        else:
            # New skill entry
            skill = UserSkill(
                user_id=user_id,
                topic=topic,
                solve_count=0, # Unknown count if we don't scan all, but fine.
                max_solved_rating=max_rating
            )
            db.add(skill)
            
    db.commit()
    return count


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

