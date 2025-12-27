"""
AI Coach Module.

Uses Google Gemini to generate human-readable explanations
of weakness analysis results.

IMPORTANT: AI does NOT compute weaknesses - it only explains them.
All analysis is done in weakness_analysis.py (deterministic).
"""

import json
import requests
from typing import Dict, Optional


# =============================================================================
# GEMINI API CONFIGURATION
# =============================================================================

import os

# =============================================================================
# GEMINI API CONFIGURATION
# =============================================================================

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


# =============================================================================
# PROMPT TEMPLATE
# =============================================================================

WEAKNESS_PROMPT = """You are a competitive programming coach.

Based ONLY on the structured performance summary below:
1. Explain the user's weak areas in plain language.
2. Explain why these weaknesses are likely occurring.
3. Suggest a focused upsolving strategy.

Rules:
- Do NOT recommend new problems.
- Do NOT change priorities.
- Do NOT mention ratings explicitly unless relevant.
- Keep explanation concise and actionable.

Performance Summary:
{summary_json}

Provide:
1. A short paragraph explaining weaknesses.
2. 3-5 bullet points on how to upsolve effectively.
"""


# =============================================================================
# AI EXPLANATION GENERATION
# =============================================================================

def generate_weakness_explanation(summary: Dict) -> str:
    """
    Generate AI explanation of weakness analysis.
    
    Uses Google Gemini API to interpret the summary and provide
    coaching advice. The AI receives ONLY summarized statistics,
    never raw submission data.
    
    Args:
        summary: Compact summary dict from prepare_weakness_summary()
        
    Returns:
        Human-readable coaching explanation string
    """
    if not GEMINI_API_KEY:
        return "AI explanation unavailable - API key not configured."
    
    try:
        # Format prompt with summary
        prompt = WEAKNESS_PROMPT.format(
            summary_json=json.dumps(summary, indent=2)
        )
        
        # Call Gemini API
        response = requests.post(
            f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 500
                }
            },
            timeout=30
        )
        
        if response.status_code != 200:
            return f"AI explanation unavailable - API error ({response.status_code})"
        
        data = response.json()
        
        # Extract text from response
        candidates = data.get("candidates", [])
        if not candidates:
            return "AI explanation unavailable - empty response"
        
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
            return "AI explanation unavailable - no content"
        
        explanation = parts[0].get("text", "")
        return explanation.strip()
        
    except requests.Timeout:
        return "AI explanation unavailable - request timed out"
    except Exception as e:
        return f"AI explanation unavailable - {str(e)}"


def generate_upsolve_reason(candidate: Dict) -> str:
    """
    Generate a short reason for why this problem is recommended for upsolving.
    
    This is deterministic, not AI-generated.
    
    Args:
        candidate: Upsolve candidate dict
        
    Returns:
        Short reason string
    """
    reasons = candidate.get("reasons", [])
    if reasons:
        return "; ".join(reasons)
    return "Attempted but unsolved in contest"
