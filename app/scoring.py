"""
Scoring Module for CP Coach.

Provides weighted scoring logic for weakness analysis and recommendations.
All scoring functions are deterministic (same input → same output).
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict

from .config import (
    WRONG_SUBMISSION_BASE_WEIGHT,
    DIFFICULTY_MULTIPLIER,
    REPEATED_ATTEMPT_PENALTY,
    TIME_DECAY_FACTOR,
    TIME_DECAY_MAX_DAYS,
    get_rating_bucket,
    normalize_tag,
)


def calculate_weakness_score(
    attempts: int,
    successes: int,
    problem_rating: int,
    user_rating: int,
    days_ago: float = 0.0
) -> float:
    """
    Calculate weighted weakness score for a topic/problem.
    
    Scoring factors:
    1. Failure rate: More wrong attempts = higher weakness
    2. Difficulty weight: Failing harder problems = more weight
    3. Attempt penalty: Repeated failures = higher penalty
    4. Time decay: Recent failures are more relevant
    
    Args:
        attempts: Total number of attempts
        successes: Number of successful solves
        problem_rating: Rating of the problem
        user_rating: User's current rating
        days_ago: Days since last attempt
        
    Returns:
        Weighted weakness score (higher = weaker)
    """
    if attempts == 0:
        return 0.0
    
    # Base failure score
    failures = attempts - successes
    if failures <= 0:
        return 0.0  # No weakness if all attempts succeeded
    
    # 1. Failure rate component
    failure_rate = failures / attempts
    base_score = failure_rate * WRONG_SUBMISSION_BASE_WEIGHT
    
    # 2. Difficulty weight: failing harder problems is more concerning
    # If problem is harder than user rating, weight it more
    rating_ratio = problem_rating / max(user_rating, 800)
    difficulty_weight = min(rating_ratio * DIFFICULTY_MULTIPLIER, 2.0)
    
    # 3. Repeated attempt penalty
    attempt_penalty = 1.0 + (failures * REPEATED_ATTEMPT_PENALTY)
    
    # 4. Time decay: more recent = more relevant
    capped_days = min(days_ago, TIME_DECAY_MAX_DAYS)
    time_weight = TIME_DECAY_FACTOR ** capped_days
    
    # Combine all factors
    final_score = base_score * difficulty_weight * attempt_penalty * time_weight
    
    return round(final_score, 4)


def aggregate_topic_weakness(
    submissions: List[Dict],
    user_rating: int
) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate weakness scores by topic from submission history.
    
    Args:
        submissions: List of submission dicts with problem info
        user_rating: User's current rating
        
    Returns:
        Dict of topic -> {score, attempts, successes, avg_rating}
    """
    topic_stats = defaultdict(lambda: {
        "attempts": 0,
        "successes": 0,
        "total_rating": 0,
        "last_attempt_time": None,
        "rating_sum": 0,
    })
    
    now = datetime.utcnow()
    
    for sub in submissions:
        problem = sub.get("problem", {})
        tags_str = problem.get("tags", "")
        rating = problem.get("rating", 0) or 0
        verdict = sub.get("verdict", "")
        timestamp = sub.get("creationTimeSeconds", 0)
        
        if not tags_str or not rating:
            continue
        
        # Parse tags
        if isinstance(tags_str, str):
            tags = [normalize_tag(t.strip()) for t in tags_str.split(",") if t.strip()]
        else:
            tags = [normalize_tag(t) for t in tags_str]
        
        # Update stats for each tag
        for tag in tags:
            stats = topic_stats[tag]
            stats["attempts"] += 1
            stats["rating_sum"] += rating
            
            if verdict == "OK":
                stats["successes"] += 1
            
            # Track most recent attempt
            if timestamp:
                attempt_time = datetime.fromtimestamp(timestamp)
                if not stats["last_attempt_time"] or attempt_time > stats["last_attempt_time"]:
                    stats["last_attempt_time"] = attempt_time
    
    # Calculate final scores
    result = {}
    for topic, stats in topic_stats.items():
        attempts = stats["attempts"]
        if attempts == 0:
            continue
        
        avg_rating = stats["rating_sum"] / attempts
        days_ago = 0.0
        if stats["last_attempt_time"]:
            days_ago = (now - stats["last_attempt_time"]).total_seconds() / 86400
        
        score = calculate_weakness_score(
            attempts=attempts,
            successes=stats["successes"],
            problem_rating=int(avg_rating),
            user_rating=user_rating,
            days_ago=days_ago
        )
        
        result[topic] = {
            "score": score,
            "attempts": attempts,
            "successes": stats["successes"],
            "failure_rate": round((attempts - stats["successes"]) / attempts, 2),
            "avg_rating": int(avg_rating),
            "days_since_last": round(days_ago, 1),
        }
    
    return result


def rank_weak_topics(
    topic_scores: Dict[str, Dict[str, Any]],
    min_attempts: int = 3,
    limit: int = 5
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Rank topics by weakness score, filtering by minimum attempts.
    
    Args:
        topic_scores: Output from aggregate_topic_weakness
        min_attempts: Minimum attempts required to consider topic
        limit: Maximum topics to return
        
    Returns:
        List of (topic, stats) tuples sorted by weakness score descending
    """
    # Filter by minimum attempts
    qualified = [
        (topic, stats) for topic, stats in topic_scores.items()
        if stats["attempts"] >= min_attempts
    ]
    
    # Sort by score descending, then topic name for stability
    sorted_topics = sorted(
        qualified,
        key=lambda x: (-x[1]["score"], x[0])
    )
    
    return sorted_topics[:limit]


def calculate_problem_impact_score(
    problem: Dict,
    weak_topics: List[str],
    weak_rating_bands: List[Tuple[int, int]],
    user_rating: int
) -> float:
    """
    Calculate impact score for a problem recommendation.
    
    Higher score = addressing more weaknesses = better recommendation.
    
    Args:
        problem: Problem dict with tags and rating
        weak_topics: List of user's weak topic names
        weak_rating_bands: List of (min, max) rating bands where user is weak
        user_rating: User's current rating
        
    Returns:
        Impact score (higher = better match for addressing weaknesses)
    """
    score = 0.0
    
    # 1. Topic match bonus
    tags_str = problem.get("tags", "")
    if isinstance(tags_str, str):
        tags = [normalize_tag(t.strip()) for t in tags_str.split(",") if t.strip()]
    else:
        tags = [normalize_tag(t) for t in tags_str]
    
    for tag in tags:
        if tag in weak_topics:
            score += 3.0  # Significant bonus for matching weak topic
    
    # 2. Rating band match bonus
    rating = problem.get("rating", 0)
    for min_r, max_r in weak_rating_bands:
        if min_r <= rating <= max_r:
            score += 2.0  # Bonus for matching weak rating band
            break
    
    # 3. Appropriate difficulty bonus (within reach but challenging)
    rating_diff = rating - user_rating
    if 0 <= rating_diff <= 200:
        score += 1.0  # Slightly harder = good for growth
    elif -100 <= rating_diff < 0:
        score += 0.5  # Slightly easier = confidence building
    
    return round(score, 2)


def sort_recommendations_by_impact(
    problems: List[Dict],
    weak_topics: List[str],
    weak_rating_bands: List[Tuple[int, int]],
    user_rating: int,
    limit: int = 5
) -> List[Dict]:
    """
    Sort problem recommendations by impact score.
    
    Args:
        problems: List of problem dicts
        weak_topics: User's weak topics
        weak_rating_bands: User's weak rating bands
        user_rating: User's current rating
        limit: Max problems to return
        
    Returns:
        Problems sorted by impact score descending
    """
    # Calculate impact for each problem
    scored = []
    for p in problems:
        impact = calculate_problem_impact_score(
            p, weak_topics, weak_rating_bands, user_rating
        )
        scored.append((impact, p))
    
    # Sort by impact descending, then by problem ID for stability
    sorted_problems = sorted(
        scored,
        key=lambda x: (-x[0], x[1].get("id", 0))
    )
    
    return [p for _, p in sorted_problems[:limit]]
