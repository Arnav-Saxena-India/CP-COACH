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
# Llama3-70b is extremely fast and capable (Groq LPU)
MODEL_NAME = "llama3-70b-8192"

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
