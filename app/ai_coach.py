import os
import logging
import json
from groq import Groq

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Groq client
# ensure GROQ_API_KEY is set in environment variables
client = Groq(
    api_key=os.getenv("GROQ_API_KEY"),
)

# Model configuration
# Using Llama 3.3 70B (Latest stable flagship)
MODEL_NAME = "llama-3.3-70b-versatile"

def generate_weakness_explanation(summary_data: dict) -> str:
    """
    Generate a personalized explanation of weaknesses using Groq (Llama3).
    
    Args:
        summary_data: Dict containing:
            - user_rating
            - weak_rating_bands (list)
            - weak_topics (list)
            - upsolve_preview (list of problems)
            - overall_solved_rate
            
    Returns:
        String explanation from AI
        
    Raises:
        Exception: If API call fails (handled by caller)
    """
    if not os.getenv("GROQ_API_KEY"):
        return "AI explanation unavailable - GROQ_API_KEY not configured."

    try:
        # Construct prompt
        prompt = f"""
        You are an elite Competitive Programming Coach. 
        Analyze this student's performance and give brief, high-impact advice.
        
        Student Profile:
        - Rating: {summary_data.get('user_rating')}
        - Weak Rating Ranges: {', '.join(map(str, summary_data.get('weak_rating_bands', [])))} (High failure rate here)
        - Weak Topics: {', '.join(summary_data.get('weak_topics', []))}
        - Overall Solved Rate: {int(summary_data.get('overall_solved_rate', 0) * 100)}%
        
        Upsolving Recommendation:
        I have selected {summary_data.get('upsolve_count')} problems for them, focusing on {', '.join([p['tags'] for p in summary_data.get('upsolve_preview', [])][:3])}.
        
        Task:
        1. Explain WHY they are stuck (connection between rating/topics).
        2. Give 1 concrete tip to improve in their weak topics.
        3. Motivate them to solve the recommended problems.
        
        Keep it short (max 3 sentences). Be encouraging but direct.
        """

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful, expert competitive programming coach."
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model=MODEL_NAME,
            temperature=0.6,
            max_tokens=250,
        )

        return chat_completion.choices[0].message.content

    except Exception as e:
        logger.error(f"Groq API Error: {str(e)}")
        # Return a friendly error message to the UI
        if "401" in str(e):
             return "AI unavailable: Invalid API Key."
        elif "429" in str(e):
             return "AI busy: Rate limit exceeded. Try again in a minute."
        return "AI insight temporarily unavailable (Backend connection issue)."


def analyze_performance(problem_data: dict, time_taken: int) -> dict:
    """
    Analyze if the solve time was too slow compared to problem rating.
    
    Args:
        problem_data: Dict with 'rating', 'tags'
        time_taken: Time in seconds
        
    Returns:
        Dict: {"is_slow": bool, "advice": str|None}
    """
    if not os.getenv("GROQ_API_KEY"):
        return {"is_slow": False, "advice": None}
        
    rating = problem_data.get("rating", 1000)
    minutes = time_taken // 60
    
    # Heuristic check first to save API calls
    # Heuristic: < 5 mins for <1000, < 15 mins for <1500, etc.
    expected_minutes = (rating / 100) * 1.5  # e.g. 1000->15m, 1500->22m
    
    if minutes <= expected_minutes:
        return {"is_slow": False, "advice": None}
        
    # If slow, ask AI for specific advice
    try:
        prompt = f"""
        Student took {minutes} minutes to solve a {rating}-rated Codeforces problem.
        Problem tags: {problem_data.get('tags')}.
        Typically this should take {int(expected_minutes)} minutes.
        
        Give 1 concise tip on how to recognize/solve this type of problem faster next time.
        Maximum 2 sentences.
        """
        
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_NAME,
            max_tokens=100
        )
        return {
            "is_slow": True, 
            "advice": completion.choices[0].message.content
        }
    except Exception as e:
        logger.error(f"AI Analysis Error: {e}")
        return {"is_slow": True, "advice": "Try to identify the pattern faster next time."}


def select_best_problem(candidates: list, user_profile: dict) -> dict:
    """
    Select the single best problem from candidates to ensure variety and engagement.
    
    Args:
        candidates: List of problem dicts
        user_profile: Dict with rating, weak topics
        
    Returns:
        The selected problem dict (or the first one if AI fails)
    """
    if not candidates:
        return None
    
    if not os.getenv("GROQ_API_KEY"):
        return candidates[0]
        
    try:
        # Simplified representation for AI
        options = []
        for i, p in enumerate(candidates):
            options.append(f"Option {i}: {p['rating']} rating, Tags: {p['tags']}")
            
        prompt = f"""
        Select the best next problem for a User (Rating: {user_profile.get('rating')}).
        Weaknesses: {', '.join(user_profile.get('weak_topics', []))}.
        
        Candidates:
        {chr(10).join(options)}
        
        Goal: Maximize learning and variety. Don't pick the same tag twice in a row if possible.
        Return ONLY the Option Index (e.g. "0" or "2").
        """
        
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=MODEL_NAME,
            max_tokens=10
        )
        
        choice_text = completion.choices[0].message.content.strip()
        import re
        match = re.search(r'\d+', choice_text)
        if match:
            idx = int(match.group())
            if 0 <= idx < len(candidates):
                return candidates[idx]
                
        return candidates[0]
        
    except Exception as e:
        logger.error(f"AI Selection Error: {e}")
        return candidates[0]


def generate_upsolve_reason(problem_data: dict) -> str:
    """
    Generate a very short reason for recommending a specific problem.
    (Optional: Can use AI, but for speed logic we use template or mini-AI call)
    For Groq speed, we CAN actually use AI, but purely rule-based is faster 
    and saves rate limits. Sticking to deterministic for list items.
    """
    reasons = problem_data.get("reasons", [])
    if reasons:
        return f"Focus: {reasons[0]}"
    return "Recommended for skill improvement."
