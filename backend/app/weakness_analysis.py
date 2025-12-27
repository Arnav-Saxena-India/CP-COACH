"""
Weakness Analysis Module.

Deterministic analysis of user contest performance to detect weak areas.
NO AI/LLM logic here - pure data analysis only.
"""

from typing import List, Dict, Tuple, Optional
from datetime import datetime
from collections import defaultdict

import requests
from sqlalchemy.orm import Session

from .models import User, UserContestProblemStat


# =============================================================================
# CONSTANTS
# =============================================================================

CODEFORCES_API_URL = "https://codeforces.com/api"

# Weakness detection thresholds
MIN_ATTEMPTS_FOR_WEAK_BAND = 8  # REQUIREMENT: attempted_count >= 8
WEAK_UNSOLVED_RATE = 0.60  # REQUIREMENT: unsolved_rate >= 0.60

MIN_ATTEMPTS_FOR_WEAK_TOPIC = 6  # REQUIREMENT: attempted_count >= 6
WEAK_TOPIC_SOLVED_RATE = 0.40  # REQUIREMENT: solved_rate <= 0.40

# Rating bucket width
RATING_BUCKET_WIDTH = 100

# Upsolving
MAX_UPSOLVE_CANDIDATES = 5
UPSOLVE_RATING_BUFFER = 100  # REQUIREMENT: rating <= user_rating + 100


# =============================================================================
# STEP 1: FETCH AND STORE CONTEST SUBMISSIONS
# =============================================================================

def fetch_user_submissions(handle: str, count: int = 100) -> List[dict]:
    """
    Fetch user's recent submissions from Codeforces API.
    
    Args:
        handle: Codeforces username
        count: Number of submissions to fetch
        
    Returns:
        List of submission dictionaries
    """
    try:
        response = requests.get(
            f"{CODEFORCES_API_URL}/user.status",
            params={"handle": handle, "count": count},
            timeout=15
        )
        data = response.json()
        
        if data.get("status") != "OK":
            return []
        
        return data.get("result", [])
    except Exception:
        return []


def sync_contest_stats(db: Session, user: User, submissions: List[dict]) -> int:
    """
    Process submissions and update UserContestProblemStat table.
    
    Only processes contest submissions (has contestId).
    
    Args:
        db: Database session
        user: User object
        submissions: List of CF submission objects
        
    Returns:
        Number of stats updated
    """
    stats_updated = 0
    
    # Group submissions by contest+problem
    problem_submissions = defaultdict(list)
    for sub in submissions:
        if "contestId" not in sub:
            continue
        
        contest_id = sub["contestId"]
        problem = sub.get("problem", {})
        problem_index = problem.get("index", "")
        problem_id = f"{contest_id}{problem_index}"
        
        problem_submissions[(contest_id, problem_id)].append(sub)
    
    # Process each contest problem
    for (contest_id, problem_id), subs in problem_submissions.items():
        # Get or create stat record
        stat = db.query(UserContestProblemStat).filter(
            UserContestProblemStat.user_id == user.id,
            UserContestProblemStat.contest_id == contest_id,
            UserContestProblemStat.problem_id == problem_id
        ).first()
        
        if not stat:
            # Get problem info from first submission
            first_sub = subs[0]
            problem_info = first_sub.get("problem", {})
            
            stat = UserContestProblemStat(
                user_id=user.id,
                contest_id=contest_id,
                problem_id=problem_id,
                problem_name=problem_info.get("name"),
                problem_rating=problem_info.get("rating"),
                tags=",".join(problem_info.get("tags", []))
            )
            db.add(stat)
        
        # Update stats based on submissions
        stat.attempted = True
        stat.attempt_count = len(subs)
        
        # Check for AC verdict
        for sub in subs:
            if sub.get("verdict") == "OK":
                stat.solved = True
                stat.solved_at = datetime.fromtimestamp(sub.get("creationTimeSeconds", 0))
                
                # Calculate time to AC (from contest start)
                relative_time = sub.get("relativeTimeSeconds")
                if relative_time and relative_time < 7200:  # During 2-hour contest
                    stat.time_to_ac = relative_time
                else:
                    stat.solved_after_contest = True
                break
        
        # Track first attempt time
        if subs:
            earliest = min(subs, key=lambda s: s.get("creationTimeSeconds", float("inf")))
            stat.first_attempt_at = datetime.fromtimestamp(earliest.get("creationTimeSeconds", 0))
        
        stats_updated += 1
    
    db.commit()
    return stats_updated


# =============================================================================
# STEP 2: WEAK RATING BAND DETECTION
# =============================================================================

def detect_weak_rating_bands(db: Session, user_id: int) -> List[Dict]:
    """
    Detect weak rating bands based on unsolved rate.
    
    A rating band is weak if:
    - attempted_count >= threshold
    - unsolved_rate >= 60%
    
    Args:
        db: Database session
        user_id: User's database ID
        
    Returns:
        List of weak band dicts with stats
    """
    # Get all stats with ratings
    stats = db.query(UserContestProblemStat).filter(
        UserContestProblemStat.user_id == user_id,
        UserContestProblemStat.problem_rating.isnot(None),
        UserContestProblemStat.attempted == True
    ).all()
    
    # Group by rating bucket
    buckets = defaultdict(lambda: {"attempted": 0, "solved": 0, "unsolved": 0})
    
    for stat in stats:
        bucket = (stat.problem_rating // RATING_BUCKET_WIDTH) * RATING_BUCKET_WIDTH
        bucket_key = f"{bucket}-{bucket + RATING_BUCKET_WIDTH}"
        
        buckets[bucket_key]["attempted"] += 1
        if stat.solved:
            buckets[bucket_key]["solved"] += 1
        else:
            buckets[bucket_key]["unsolved"] += 1
    
    # Find weak bands
    weak_bands = []
    for band, counts in buckets.items():
        if counts["attempted"] >= MIN_ATTEMPTS_FOR_WEAK_BAND:
            unsolved_rate = counts["unsolved"] / counts["attempted"]
            if unsolved_rate >= WEAK_UNSOLVED_RATE:
                weak_bands.append({
                    "band": band,
                    "attempted": counts["attempted"],
                    "solved": counts["solved"],
                    "unsolved": counts["unsolved"],
                    "unsolved_rate": round(unsolved_rate, 2)
                })
    
    # Sort by unsolved rate (worst first)
    weak_bands.sort(key=lambda x: x["unsolved_rate"], reverse=True)
    
    return weak_bands


# =============================================================================
# STEP 3: WEAK TOPIC DETECTION
# =============================================================================

def detect_weak_topics(db: Session, user_id: int) -> List[Dict]:
    """
    Detect weak topics/tags based on solve rate.
    
    A topic is weak if:
    - attempted_count >= threshold
    - solved_rate < 40%
    
    Args:
        db: Database session
        user_id: User's database ID
        
    Returns:
        List of weak topic dicts with stats
    """
    # Get all attempted stats with tags
    stats = db.query(UserContestProblemStat).filter(
        UserContestProblemStat.user_id == user_id,
        UserContestProblemStat.tags.isnot(None),
        UserContestProblemStat.attempted == True
    ).all()
    
    # Group by topic
    topics = defaultdict(lambda: {"attempted": 0, "solved": 0, "failed": 0})
    
    for stat in stats:
        if not stat.tags:
            continue
        
        for tag in stat.tags.split(","):
            tag = tag.strip().lower()
            if not tag:
                continue
            
            topics[tag]["attempted"] += 1
            if stat.solved:
                topics[tag]["solved"] += 1
            else:
                topics[tag]["failed"] += 1
    
    # Find weak topics
    weak_topics = []
    for topic, counts in topics.items():
        if counts["attempted"] >= MIN_ATTEMPTS_FOR_WEAK_TOPIC:
            solved_rate = counts["solved"] / counts["attempted"]
            if solved_rate < WEAK_TOPIC_SOLVED_RATE:
                weak_topics.append({
                    "topic": topic,
                    "attempted": counts["attempted"],
                    "solved": counts["solved"],
                    "failed": counts["failed"],
                    "solved_rate": round(solved_rate, 2)
                })
    
    # Sort by solved rate (worst first)
    weak_topics.sort(key=lambda x: x["solved_rate"])
    
    return weak_topics


# =============================================================================
# STEP 4: UPSOLVING CANDIDATE SELECTION
# =============================================================================

def get_upsolve_candidates(
    db: Session,
    user_id: int,
    user_rating: int,
    weak_bands: List[Dict],
    weak_topics: List[Dict]
) -> List[Dict]:
    """
    Get upsolving candidates ranked by weakness match.
    
    Candidates are problems that:
    - Were attempted but NOT solved
    - Rating <= user_rating + 100
    
    Scoring Rule:
    +3 if problem.tag in weak_topics
    +2 if problem.rating_band in weak_rating_bands
    +1 if solved_after_contest == false (redundant since we select unsolved)
    -1 if problem_rating > user_rating
    
    Args:
        db: Database session
        user_id: User's database ID
        user_rating: User's current rating
        weak_bands: List of weak rating band dicts
        weak_topics: List of weak topic dicts
        
    Returns:
        List of upsolve candidate dicts
    """
    # Get unsolved attempted problems
    unsolved = db.query(UserContestProblemStat).filter(
        UserContestProblemStat.user_id == user_id,
        UserContestProblemStat.attempted == True,
        UserContestProblemStat.solved == False,
        UserContestProblemStat.problem_rating.isnot(None)
    ).all()
    
    # Filter by rating cap
    max_rating = user_rating + UPSOLVE_RATING_BUFFER
    candidates = [s for s in unsolved if s.problem_rating <= max_rating]
    
    # Extract weak band ranges and topics
    weak_band_set = set(b["band"] for b in weak_bands)
    weak_topic_set = set(t["topic"] for t in weak_topics)
    
    # Score and rank candidates
    scored_candidates = []
    for stat in candidates:
        score = 0
        reasons = []
        
        # +3 if problem.tag in weak_topics
        if stat.tags:
            problem_tags = set(t.strip().lower() for t in stat.tags.split(","))
            matching_weak_topics = problem_tags & weak_topic_set
            if matching_weak_topics:
                score += 3
                reasons.append(f"Weak topic: {', '.join(matching_weak_topics)}")
        
        # +2 if problem.rating_band in weak_rating_bands
        if stat.problem_rating:
            bucket = (stat.problem_rating // RATING_BUCKET_WIDTH) * RATING_BUCKET_WIDTH
            band_key = f"{bucket}-{bucket + RATING_BUCKET_WIDTH}"
            if band_key in weak_band_set:
                score += 2
                reasons.append(f"Weak rating band: {band_key}")
        
        # +1 if solved_after_contest == false (always true here since we filter by solved=False)
        # However, to match spec:
        if not stat.solved_after_contest:
            score += 1
            
        # -1 if problem_rating > user_rating
        if stat.problem_rating > user_rating:
            score -= 1
        
        # Add to list
        # Try to find local DB ID for "Mark as Solved" functionality
        # problem_id suffix is the index (e.g. 123A -> contest 123, index A)
        problem_index = stat.problem_id.replace(str(stat.contest_id), "")
        
        # Simple lookup - optimization: could bulk fetch but list is short
        from .models import Problem
        local_prob = db.query(Problem).filter(
            Problem.contest_id == stat.contest_id,
            Problem.problem_index == problem_index
        ).first()
        
        db_id = local_prob.id if local_prob else None

        scored_candidates.append({
            "problem_id": stat.problem_id,
            "contest_id": stat.contest_id,
            "db_id": db_id,  # Local database ID if available
            "name": stat.problem_name,
            "rating": stat.problem_rating,
            "tags": stat.tags,
            "url": f"https://codeforces.com/contest/{stat.contest_id}/problem/{stat.problem_id[-1]}",
            "score": score,
            "reasons": reasons,
            "attempt_count": stat.attempt_count
        })
    
    # Sort by: score desc, then rating asc
    scored_candidates.sort(key=lambda x: (-x["score"], x["rating"]))
    
    return scored_candidates[:MAX_UPSOLVE_CANDIDATES]

# =============================================================================
# STEP 5: PREPARE SUMMARY FOR AI
# =============================================================================

def prepare_weakness_summary(
    user_rating: int,
    weak_bands: List[Dict],
    weak_topics: List[Dict],
    upsolve_candidates: List[Dict],
    total_attempted: int,
    total_solved: int
) -> Dict:
    """
    Prepare a compact summary for AI interpretation.
    
    The AI receives ONLY this summarized data, never raw submissions.
    
    Args:
        user_rating: User's current rating
        weak_bands: List of weak rating band dicts
        weak_topics: List of weak topic dicts
        upsolve_candidates: List of upsolve candidate dicts
        total_attempted: Total problems attempted
        total_solved: Total problems solved
        
    Returns:
        Compact summary dict for AI prompt
    """
    overall_solved_rate = total_solved / total_attempted if total_attempted > 0 else 0
    
    return {
        "user_rating": user_rating,
        "total_attempted": total_attempted,
        "total_solved": total_solved,
        "overall_solved_rate": round(overall_solved_rate, 2),
        "weak_rating_bands": [b["band"] for b in weak_bands[:3]],
        "weak_topics": [t["topic"] for t in weak_topics[:5]],
        "upsolve_count": len(upsolve_candidates),
        "upsolve_preview": [
            {"rating": c["rating"], "tags": c["tags"]}
            for c in upsolve_candidates[:3]
        ]
    }
