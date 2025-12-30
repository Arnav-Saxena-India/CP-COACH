"""
Centralized Configuration Module for CP Coach.

All configurable constants, timeouts, TTLs, and limits are defined here.
Import from this module instead of hardcoding values.
"""

# =============================================================================
# CODEFORCES API CONFIGURATION
# =============================================================================

CF_API_BASE_URL = "https://codeforces.com/api"
CF_API_TIMEOUT = 30  # seconds
CF_API_MAX_RETRIES = 3
CF_API_RETRY_DELAY = 1.0  # seconds (exponential backoff base)

# CF Handle validation pattern
CF_HANDLE_PATTERN = r"^[a-zA-Z0-9_-]{3,24}$"

# =============================================================================
# CACHE CONFIGURATION
# =============================================================================

CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours
CACHE_MAX_ENTRIES = 1000  # Maximum cached handles

# =============================================================================
# RATE LIMITING
# =============================================================================

RATE_LIMIT_PER_MINUTE = 60
RATE_LIMIT_BURST = 10

# =============================================================================
# RATING BUCKETS
# =============================================================================

RATING_BUCKET_LOW = 1200      # Beginner: < 1200
RATING_BUCKET_MID = 1600      # Intermediate: 1200-1600
# Advanced: > 1600

def get_rating_bucket(rating: int) -> str:
    """Get rating bucket label for a given rating."""
    if rating < RATING_BUCKET_LOW:
        return "beginner"
    elif rating < RATING_BUCKET_MID:
        return "intermediate"
    else:
        return "advanced"

# =============================================================================
# SCORING WEIGHTS
# =============================================================================

# Wrong submission weighting
WRONG_SUBMISSION_BASE_WEIGHT = 0.5
DIFFICULTY_MULTIPLIER = 1.2  # Extra weight for harder problems

# Penalty for repeated attempts
REPEATED_ATTEMPT_PENALTY = 0.2  # Additive per attempt

# Time decay for recency weighting
TIME_DECAY_FACTOR = 0.95  # Per day decay
TIME_DECAY_MAX_DAYS = 30  # Cap decay calculation

# =============================================================================
# RECOMMENDATION SETTINGS
# =============================================================================

RECOMMENDATION_LIMIT = 5
MAX_RECOMMENDATIONS_PER_TOPIC = 5
DIFFICULTY_WINDOW = 150  # ± from target rating

# Rating adjustments based on performance
RATING_INCREASE_ON_AC = 100
RATING_DECREASE_ON_WA = 50

# Skip cooldown (problems between re-showing skipped problem)
SKIP_COOLDOWN_COUNT = 10

# =============================================================================
# API SETTINGS
# =============================================================================

API_VERSION = "v1"
MAX_PAYLOAD_SIZE_BYTES = 1024 * 1024  # 1MB

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# TAG NORMALIZATION MAP
# =============================================================================

# Maps various CF tag names to consistent internal names
TAG_NORMALIZATION_MAP = {
    # Common aliases
    "dp": "dp",
    "dynamic programming": "dp",
    "greedy": "greedy",
    "implementation": "implementation",
    "math": "math",
    "number theory": "number theory",
    "graphs": "graphs",
    "graph": "graphs",
    "trees": "trees",
    "tree": "trees",
    "binary search": "binary search",
    "binarysearch": "binary search",
    "data structures": "data structures",
    "ds": "data structures",
    "strings": "strings",
    "string": "strings",
    "geometry": "geometry",
    "sorting": "sortings",
    "sortings": "sortings",
    "brute force": "brute force",
    "bruteforce": "brute force",
    "constructive algorithms": "constructive algorithms",
    "constructive": "constructive algorithms",
    "two pointers": "two pointers",
    "twopointers": "two pointers",
    "dfs and similar": "dfs and similar",
    "dfs": "dfs and similar",
    "bfs": "dfs and similar",
    "bitmasks": "bitmasks",
    "bitmask": "bitmasks",
    "combinatorics": "combinatorics",
    "divide and conquer": "divide and conquer",
    "games": "games",
    "game theory": "games",
    "interactive": "interactive",
    "probabilities": "probabilities",
    "probability": "probabilities",
    "shortest paths": "shortest paths",
    "flows": "flows",
    "dsu": "dsu",
    "disjoint set union": "dsu",
    "union find": "dsu",
    "hashing": "hashing",
    "fft": "fft",
    "matrices": "matrices",
    "matrix": "matrices",
    "ternary search": "ternary search",
    "meet-in-the-middle": "meet-in-the-middle",
    "expression parsing": "expression parsing",
    "2-sat": "2-sat",
    "chinese remainder theorem": "chinese remainder theorem",
    "schedules": "schedules",
}

def normalize_tag(tag: str) -> str:
    """Normalize a CF tag to consistent internal format."""
    tag_lower = tag.lower().strip()
    return TAG_NORMALIZATION_MAP.get(tag_lower, tag_lower)

def normalize_tags(tags_str: str) -> str:
    """Normalize comma-separated tags string."""
    if not tags_str:
        return ""
    tags = [normalize_tag(t.strip()) for t in tags_str.split(",")]
    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique_tags.append(t)
    return ",".join(unique_tags)
