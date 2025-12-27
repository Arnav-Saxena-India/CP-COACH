import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

CF_API_URL = "https://codeforces.com/api/problemset.problems"

def fetch_problems_from_cf() -> List[Dict]:
    """
    Fetch all problems from Codeforces API and filter suitable ones.
    
    Filters:
    - Must have a rating (exclude unrated)
    - Rating between 800 and 2400 (focus on standard progression)
    - Must have standard tags
    """
    try:
        logger.info("Fetching problems from Codeforces API...")
        response = requests.get(CF_API_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data["status"] != "OK":
            logger.error(f"CF API Error: {data.get('comment')}")
            return []
            
        problems_data = data["result"]["problems"]
        # problemStatistics = data["result"]["problemStatistics"] # Can be used for popularity later
        
        cleaned_problems = []
        
        for p in problems_data:
            # Basic validation
            if "rating" not in p or "tags" not in p:
                continue
                
            rating = p["rating"]
            
            # Filter range (keep dataset manageable and relevant)
            if not (800 <= rating <= 2400):
                continue
                
            # Exclude special contest types if needed (optional)
            
            # Construct URL
            # Contest Problems: https://codeforces.com/contest/{contestId}/problem/{index}
            # Gym Problems: https://codeforces.com/gym/{contestId}/problem/{index}
            
            contest_id = p.get("contestId")
            index = p.get("index")
            
            if not contest_id or not index:
                continue
                
            # Determine URL
            # Heuristic: If contestId < 100000, it's usually standard contest. Gyms are huge numbers.
            # But standard URL works for most.
            is_gym = contest_id >= 100000
            if is_gym:
                url = f"https://codeforces.com/gym/{contest_id}/problem/{index}"
            else:
                url = f"https://codeforces.com/contest/{contest_id}/problem/{index}"
                
            cleaned_problems.append({
                "name": p["name"],
                "rating": rating,
                "tags": ",".join(p["tags"]), # Flatten list to string
                "url": url,
                "contest_id": contest_id,
                "problem_index": index
            })
            
        logger.info(f"Fetched and processed {len(cleaned_problems)} problems from Codeforces.")
        return cleaned_problems
        
    except Exception as e:
        logger.error(f"Failed to fetch CF problems: {str(e)}")
        return []

if __name__ == "__main__":
    # Test run
    logging.basicConfig(level=logging.INFO)
    res = fetch_problems_from_cf()
    print(f"Sample: {res[0] if res else 'None'}")
