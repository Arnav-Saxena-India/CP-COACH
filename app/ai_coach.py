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


def generate_layered_hints(problem_name: str, problem_rating: int, problem_tags: str) -> dict:
    """
    Generate 4 layered progressive hints for a problem using Groq.
    
    Layers:
    1. Pattern identification (just the technique name)
    2. Key observation (the "aha" insight)
    3. Approach skeleton (how to structure the solution)
    4. Implementation trap (edge case/common mistake)
    
    Args:
        problem_name: Name of the problem
        problem_rating: Problem difficulty rating
        problem_tags: Comma-separated tags
        
    Returns:
        Dict with hint_1 through hint_4 keys
    """
    if not os.getenv("GROQ_API_KEY"):
        return _generate_fallback_hints(problem_tags, problem_rating)
    
    try:
        # Parse primary tag
        tags_list = [t.strip() for t in problem_tags.split(",")]
        primary_tag = tags_list[0] if tags_list else "implementation"
        
        prompt = f"""You are a competitive programming coach. Generate 4 progressive hints for this problem that teach THINKING, not the solution.

Problem: {problem_name}
Rating: {problem_rating}
Tags: {problem_tags}

Generate exactly 4 hints in this format (JSON):
{{
    "hint_1_pattern": "One sentence identifying the problem type/pattern (e.g., 'This is a classic greedy problem')",
    "hint_2_observation": "The key insight or observation needed (e.g., 'Think about what happens if you always pick the maximum element')",
    "hint_3_approach": "A high-level approach skeleton without code (e.g., 'Sort by X, then iterate and track Y')",
    "hint_4_trap": "A common mistake or edge case to watch for (e.g., 'Watch out for N=1 case')"
}}

Rules:
- Keep each hint under 50 words
- Never give the actual solution or pseudo-code
- Make hints progressively more specific
- Be encouraging, not condescending
- Return ONLY valid JSON, no extra text"""

        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful CP coach. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            model=MODEL_NAME,
            temperature=0.7,
            max_tokens=400
        )
        
        response_text = completion.choices[0].message.content.strip()
        
        # Try to parse JSON from response
        # Handle potential markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        hints = json.loads(response_text)
        
        return {
            "hint_1": hints.get("hint_1_pattern", f"This is a {primary_tag} problem."),
            "hint_2": hints.get("hint_2_observation", "Think about the key constraint."),
            "hint_3": hints.get("hint_3_approach", "Break down the problem step by step."),
            "hint_4": hints.get("hint_4_trap", "Check edge cases carefully.")
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse hints JSON: {e}")
        return _generate_fallback_hints(problem_tags, problem_rating)
    except Exception as e:
        logger.error(f"Hint generation error: {e}")
        return _generate_fallback_hints(problem_tags, problem_rating)


def _generate_fallback_hints(problem_tags: str, problem_rating: int) -> dict:
    """
    Generate rule-based fallback hints when AI is unavailable.
    """
    tags_list = [t.strip().lower() for t in problem_tags.split(",")]
    primary_tag = tags_list[0] if tags_list else "implementation"
    
    # Tag-specific hints
    tag_hints = {
        "dp": {
            "hint_1": "This is a Dynamic Programming problem.",
            "hint_2": "Think about what state you need to track and how states transition.",
            "hint_3": "Define your DP state, base case, and recurrence relation.",
            "hint_4": "Watch for off-by-one errors and make sure your base case is correct."
        },
        "greedy": {
            "hint_1": "This is a Greedy problem.",
            "hint_2": "Think about what local choice leads to a global optimum.",
            "hint_3": "Sort by some criteria, then iterate making locally optimal choices.",
            "hint_4": "Make sure to prove (or convince yourself) that greedy works here."
        },
        "graphs": {
            "hint_1": "This is a Graph problem.",
            "hint_2": "Think about what type of traversal/algorithm fits: BFS, DFS, or shortest path?",
            "hint_3": "Build the graph representation first, then apply the right algorithm.",
            "hint_4": "Watch for disconnected components and 0-indexed vs 1-indexed nodes."
        },
        "binary search": {
            "hint_1": "This is a Binary Search problem.",
            "hint_2": "Think about what you're binary searching on - the answer itself?",
            "hint_3": "Define your search space and monotonic check function.",
            "hint_4": "Be careful with integer overflow and off-by-one in boundaries."
        },
        "math": {
            "hint_1": "This is a Math problem.",
            "hint_2": "Look for a pattern or formula by working through small examples.",
            "hint_3": "Try to find a closed-form solution or identify a known sequence.",
            "hint_4": "Watch for modular arithmetic and integer overflow."
        },
        "implementation": {
            "hint_1": "This is an Implementation problem.",
            "hint_2": "Carefully read the problem statement - the devil is in the details.",
            "hint_3": "Simulate the process exactly as described, then optimize if needed.",
            "hint_4": "Test with the sample cases and edge cases like empty input."
        },
        "data structures": {
            "hint_1": "This requires the right Data Structure.",
            "hint_2": "Think about what operations you need: fast lookup, range queries, or updates?",
            "hint_3": "Choose: set/map for lookup, segment tree for ranges, stack for LIFO.",
            "hint_4": "Make sure your data structure choice matches the complexity requirement."
        },
        "two pointers": {
            "hint_1": "This is a Two Pointers problem.",
            "hint_2": "Think about maintaining a window or meeting in the middle.",
            "hint_3": "Initialize pointers at start/end or both at start, move based on condition.",
            "hint_4": "Be careful about when to move which pointer."
        }
    }
    
    # Get hints for primary tag, or default to implementation
    if primary_tag in tag_hints:
        return tag_hints[primary_tag]
    
    # Check secondary tags
    for tag in tags_list[1:]:
        if tag in tag_hints:
            return tag_hints[tag]
    
    # Default generic hints
    return {
        "hint_1": f"This is a {primary_tag} problem at rating {problem_rating}.",
        "hint_2": "Start by understanding what the problem is really asking.",
        "hint_3": "Break down the problem into smaller subproblems.",
        "hint_4": "Test your solution with edge cases before submitting."
    }

