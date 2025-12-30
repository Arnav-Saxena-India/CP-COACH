"""
Codeforces API Client Module.

Handles all communication with Codeforces API including:
- Timeout and retry handling with exponential backoff
- Caching to prevent duplicate API calls
- Structured error responses
- Tag normalization during fetch
"""

import requests
import logging
import time
from typing import List, Dict, Optional, Tuple, Any

from .config import (
    CF_API_BASE_URL,
    CF_API_TIMEOUT,
    CF_API_MAX_RETRIES,
    CF_API_RETRY_DELAY,
    normalize_tags,
)
from .cache import user_data_cache
from .errors import CFAPIError, CFAPITimeoutError

logger = logging.getLogger(__name__)

CF_PROBLEMS_URL = f"{CF_API_BASE_URL}/problemset.problems"
CF_USER_INFO_URL = f"{CF_API_BASE_URL}/user.info"
CF_USER_STATUS_URL = f"{CF_API_BASE_URL}/user.status"


def _make_cf_request(url: str, params: Dict = None) -> Tuple[bool, Any]:
    """
    Make a request to CF API with timeout and retry logic.
    
    Args:
        url: API endpoint URL
        params: Optional query parameters
        
    Returns:
        Tuple of (success, data_or_error)
    """
    last_error = None
    
    for attempt in range(CF_API_MAX_RETRIES):
        try:
            delay = CF_API_RETRY_DELAY * (2 ** attempt) if attempt > 0 else 0
            if delay > 0:
                logger.info(f"Retry {attempt + 1}/{CF_API_MAX_RETRIES} after {delay}s")
                time.sleep(delay)
            
            response = requests.get(
                url, 
                params=params, 
                timeout=CF_API_TIMEOUT
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "OK":
                error_msg = data.get("comment", "Unknown CF API error")
                logger.warning(f"CF API returned error: {error_msg}")
                last_error = error_msg
                continue
            
            return True, data.get("result")
            
        except requests.exceptions.Timeout:
            logger.warning(f"CF API timeout (attempt {attempt + 1})")
            last_error = "timeout"
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"CF API request failed: {e}")
            last_error = str(e)
    
    # All retries exhausted
    if last_error == "timeout":
        raise CFAPITimeoutError()
    raise CFAPIError(f"CF API failed after {CF_API_MAX_RETRIES} attempts", last_error)


def fetch_cf_user_info(handle: str, use_cache: bool = True) -> Dict:
    """
    Fetch user info from Codeforces API.
    
    Args:
        handle: Codeforces username
        use_cache: Whether to check cache first
        
    Returns:
        User info dictionary with rating, rank, etc.
    """
    cache_key = f"user_info:{handle.lower()}"
    
    if use_cache:
        cached, hit = user_data_cache.get(cache_key)
        if hit:
            logger.info(f"Cache hit for user info: {handle}")
            return cached
    
    logger.info(f"Fetching user info from CF API: {handle}")
    success, result = _make_cf_request(CF_USER_INFO_URL, {"handles": handle})
    
    if success and result:
        user_info = result[0] if isinstance(result, list) else result
        user_data_cache.set(cache_key, user_info)
        return user_info
    
    raise CFAPIError(f"Failed to fetch user info for {handle}")


def fetch_cf_user_submissions(
    handle: str, 
    count: int = 100, 
    use_cache: bool = True
) -> List[Dict]:
    """
    Fetch user's recent submissions from Codeforces API.
    
    Args:
        handle: Codeforces username
        count: Number of submissions to fetch
        use_cache: Whether to check cache first
        
    Returns:
        List of submission dictionaries
    """
    cache_key = f"submissions:{handle.lower()}:{count}"
    
    if use_cache:
        cached, hit = user_data_cache.get(cache_key)
        if hit:
            logger.info(f"Cache hit for submissions: {handle}")
            return cached
    
    logger.info(f"Fetching submissions from CF API: {handle}")
    success, result = _make_cf_request(
        CF_USER_STATUS_URL, 
        {"handle": handle, "count": count}
    )
    
    if success and result:
        user_data_cache.set(cache_key, result)
        return result
    
    return []


def fetch_problems_from_cf(use_cache: bool = True) -> List[Dict]:
    """
    Fetch all problems from Codeforces API and filter suitable ones.
    
    Features:
    - Timeout and retry handling
    - Tag normalization
    - Caching to prevent duplicate calls
    
    Filters:
    - Must have a rating (exclude unrated)
    - Rating between 800 and 2400
    - Must have contest ID and index
    
    Returns:
        List of problem dictionaries with normalized tags
    """
    cache_key = "all_problems"
    
    if use_cache:
        cached, hit = user_data_cache.get(cache_key)
        if hit:
            logger.info("Cache hit for problems list")
            return cached
    
    logger.info("Fetching problems from Codeforces API...")
    
    try:
        success, result = _make_cf_request(CF_PROBLEMS_URL)
        
        if not success or not result:
            logger.error("Failed to fetch problems from CF API")
            return []
        
        problems_data = result.get("problems", [])
        cleaned_problems = []
        
        for p in problems_data:
            # Basic validation
            if "rating" not in p or "tags" not in p:
                continue
            
            rating = p["rating"]
            
            # Filter range (keep dataset manageable and relevant)
            if not (800 <= rating <= 2400):
                continue
            
            contest_id = p.get("contestId")
            index = p.get("index")
            
            if not contest_id or not index:
                continue
            
            # Determine URL
            is_gym = contest_id >= 100000
            if is_gym:
                url = f"https://codeforces.com/gym/{contest_id}/problem/{index}"
            else:
                url = f"https://codeforces.com/contest/{contest_id}/problem/{index}"
            
            # Normalize tags during fetch
            raw_tags = ",".join(p["tags"])
            normalized_tags = normalize_tags(raw_tags)
            
            cleaned_problems.append({
                "name": p["name"],
                "rating": rating,
                "tags": normalized_tags,
                "url": url,
                "contest_id": contest_id,
                "problem_index": index
            })
        
        logger.info(f"Fetched {len(cleaned_problems)} problems from Codeforces")
        
        # Cache for longer (problems don't change often)
        user_data_cache.set(cache_key, cleaned_problems, ttl=12 * 60 * 60)
        return cleaned_problems
        
    except (CFAPIError, CFAPITimeoutError) as e:
        logger.error(f"CF API error fetching problems: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching problems: {e}")
        return []


def normalize_cf_submissions(submissions: List[Dict]) -> List[Dict]:
    """
    Normalize CF submissions data with consistent tag names.
    
    Args:
        submissions: Raw submission list from CF API
        
    Returns:
        Normalized submission list
    """
    normalized = []
    
    for sub in submissions:
        problem = sub.get("problem", {})
        
        # Normalize tags
        raw_tags = problem.get("tags", [])
        if isinstance(raw_tags, list):
            raw_tags = ",".join(raw_tags)
        
        normalized_sub = {
            "id": sub.get("id"),
            "contestId": sub.get("contestId"),
            "problem": {
                "contestId": problem.get("contestId"),
                "index": problem.get("index"),
                "name": problem.get("name"),
                "rating": problem.get("rating"),
                "tags": normalize_tags(raw_tags),
            },
            "verdict": sub.get("verdict"),
            "creationTimeSeconds": sub.get("creationTimeSeconds"),
        }
        normalized.append(normalized_sub)
    
    return normalized


if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    
    print("Testing problem fetch...")
    problems = fetch_problems_from_cf()
    print(f"Fetched {len(problems)} problems")
    if problems:
        print(f"Sample: {problems[0]}")
