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
    1. First insight - What to notice/try first
    2. Key realization - The "aha" moment
    3. Solution direction - How to approach it
    4. Gotcha - Edge case or common mistake
    
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
        
        prompt = f"""You are helping a student who is STUCK on this competitive programming problem. They've been staring at it for 10 minutes and don't know where to start.

Problem: "{problem_name}"
Rating: {problem_rating}
Tags: {problem_tags}

Your job: Give 4 progressive hints that ACTUALLY HELP. NOT generic advice like "think about DP" - they already know the tags!

Generate hints that answer WHAT A STUCK PERSON ACTUALLY NEEDS:

Hint 1 - "What should I try first?"
→ Give a SPECIFIC starting point. Example: "Try drawing out what happens for N=5" or "What if you processed elements from right to left?"

Hint 2 - "What's the key insight?"  
→ The realization that unlocks the problem. Example: "Notice that once you pick element i, all elements before it become irrelevant" or "The answer only depends on the parity of the count"

Hint 3 - "How do I structure my solution?"
→ Concrete approach. Example: "Maintain a running maximum as you iterate" or "Use a map to count occurrences, then check which keys satisfy the condition"

Hint 4 - "What could go wrong?"
→ Specific gotcha. Example: "Empty array returns 0, not -1" or "Don't forget: indices are 1-based in input"

Return ONLY valid JSON:
{{
    "hint_1": "...",
    "hint_2": "...",
    "hint_3": "...",
    "hint_4": "..."
}}

RULES:
- Each hint must be SPECIFIC to THIS problem, not generic tag advice
- Use simple language a beginner can understand
- Give actionable hints ("Try X" not "Think about X")
- Never give the actual solution or code
- Max 40 words per hint"""

        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a patient tutor helping a stuck student. Give specific, actionable hints - not generic advice."},
                {"role": "user", "content": prompt}
            ],
            model=MODEL_NAME,
            temperature=0.8,
            max_tokens=500
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
            "hint_1": hints.get("hint_1", "Try working through a small example by hand."),
            "hint_2": hints.get("hint_2", "Look for a pattern in your examples."),
            "hint_3": hints.get("hint_3", "Think about what data structure would help here."),
            "hint_4": hints.get("hint_4", "Check edge cases: empty input, single element, all same values.")
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
    These are more actionable than before.
    """
    tags_list = [t.strip().lower() for t in problem_tags.split(",")]
    primary_tag = tags_list[0] if tags_list else "implementation"
    
    # Tag-specific actionable hints
    tag_hints = {
        "dp": {
            "hint_1": "Try solving it for very small inputs (N=1, N=2, N=3) by hand. Write down the answers.",
            "hint_2": "Ask yourself: 'If I knew the answer for the first i elements, how does adding element i+1 change things?'",
            "hint_3": "Create an array dp[] where dp[i] stores the answer for the subproblem ending at index i. Fill it left to right.",
            "hint_4": "Double-check: Is your base case (dp[0]) correct? Off-by-one errors are the #1 DP bug."
        },
        "greedy": {
            "hint_1": "Sort the input by some criteria. Try sorting by size, by value, by ratio, or by end time.",
            "hint_2": "At each step, ask: 'What's the best local choice right now?' Often it's the min or max of something.",
            "hint_3": "Iterate through sorted elements. For each, decide: take it or skip it? Track your running total/count.",
            "hint_4": "Test with a case where greedy might fail. If order matters, make sure you're sorting correctly."
        },
        "graphs": {
            "hint_1": "First, build the graph: create an adjacency list from the input edges.",
            "hint_2": "Do you need shortest path (BFS), all reachable nodes (DFS), or connected components (Union-Find)?",
            "hint_3": "Start BFS/DFS from the source. Use a visited[] array to avoid infinite loops.",
            "hint_4": "Watch out: Is the graph 0-indexed or 1-indexed? Are there self-loops or multiple edges?"
        },
        "binary search": {
            "hint_1": "If the answer is a number in a range, binary search on the answer itself.",
            "hint_2": "Write a check(x) function that returns true if x is achievable. This must be monotonic.",
            "hint_3": "Use lo=minimum possible answer, hi=maximum. While lo < hi, check mid and narrow the range.",
            "hint_4": "Be careful with lo, hi bounds and whether to use mid or mid+1. Off-by-one errors are common."
        },
        "math": {
            "hint_1": "Write down the answer for N=1,2,3,4,5. Look for a pattern or formula.",
            "hint_2": "Check if the pattern relates to: N itself, N², powers of 2, factorials, or Fibonacci.",
            "hint_3": "If you found a formula, implement it. Use modular arithmetic if numbers get large.",
            "hint_4": "Watch for overflow! Use 'long long' in C++ or handle mod operations carefully."
        },
        "implementation": {
            "hint_1": "Read the problem statement again slowly. Underline every condition and constraint.",
            "hint_2": "Simulate the process exactly as described, step by step. Use arrays to track state.",
            "hint_3": "Write the straightforward solution first. Don't optimize until it works.",
            "hint_4": "Test with the given examples AND edge cases: N=1, empty input, all elements same."
        },
        "data structures": {
            "hint_1": "What operations do you need? Fast lookup → set/map. Fast min/max → heap. Range queries → segment tree.",
            "hint_2": "If brute force is O(N²), think about what data structure could speed up the inner loop.",
            "hint_3": "Choose the right tool: deque for sliding window, stack for 'next greater', map for counting.",
            "hint_4": "Make sure you're not doing O(N) operations inside a loop when O(log N) is possible."
        },
        "two pointers": {
            "hint_1": "Try using two pointers: one at the start, one at the end. Move them based on a condition.",
            "hint_2": "If looking for a subarray with property X, use a sliding window: expand right, shrink left.",
            "hint_3": "Maintain what you need (sum, count, max) as you move pointers. Update incrementally.",
            "hint_4": "Make sure you handle the case when left pointer catches up to right pointer."
        },
        "strings": {
            "hint_1": "If comparing strings, think about sorting them or using a hash/set.",
            "hint_2": "For substring problems, sliding window often works. Track character counts in the window.",
            "hint_3": "Build your solution character by character. Use a StringBuilder or list for efficiency.",
            "hint_4": "Edge cases: empty string, single character, all same characters."
        },
        "trees": {
            "hint_1": "Start with a DFS from the root. Process each node and its subtree.",
            "hint_2": "Think recursively: the answer for a node often depends on answers from its children.",
            "hint_3": "Return information up from children to parent. Sometimes you need to track depth or subtree size.",
            "hint_4": "Don't forget the base case: what happens at a leaf node?"
        }
    }
    
    # Get hints for primary tag, or default
    if primary_tag in tag_hints:
        return tag_hints[primary_tag]
    
    # Check secondary tags
    for tag in tags_list[1:]:
        if tag in tag_hints:
            return tag_hints[tag]
    
    # Default actionable hints
    return {
        "hint_1": "Start by working through the sample input by hand. Trace each step.",
        "hint_2": "What pattern do you see? Is there something you can sort, count, or track?",
        "hint_3": "Write the brute force solution first. Then think about how to optimize.",
        "hint_4": "Before submitting: test with N=1, test with maximum N, test with edge cases."
    }


