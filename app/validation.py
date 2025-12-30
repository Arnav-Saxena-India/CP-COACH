"""
Input Validation Utilities for CP Coach.

Provides validation functions for user input with consistent error handling.
"""

import re
from typing import Optional, Tuple
from .config import CF_HANDLE_PATTERN


def validate_cf_handle(handle: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Codeforces handle format.
    
    Args:
        handle: The CF handle to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        If valid, returns (True, None)
        If invalid, returns (False, "error description")
    """
    if not handle:
        return False, "Handle cannot be empty"
    
    handle = handle.strip()
    
    if len(handle) < 3:
        return False, "Handle must be at least 3 characters"
    
    if len(handle) > 24:
        return False, "Handle must be at most 24 characters"
    
    if not re.match(CF_HANDLE_PATTERN, handle):
        return False, "Handle can only contain letters, numbers, underscores, and hyphens"
    
    return True, None


def validate_topic(topic: str, valid_topics: list = None) -> Tuple[bool, Optional[str]]:
    """
    Validate topic/tag input.
    
    Args:
        topic: The topic to validate
        valid_topics: Optional list of allowed topics
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not topic:
        return False, "Topic cannot be empty"
    
    topic = topic.strip().lower()
    
    if len(topic) < 2:
        return False, "Topic must be at least 2 characters"
    
    if len(topic) > 50:
        return False, "Topic must be at most 50 characters"
    
    # Only allow alphanumeric, spaces, and hyphens
    if not re.match(r"^[a-zA-Z0-9\s\-]+$", topic):
        return False, "Topic contains invalid characters"
    
    if valid_topics and topic not in [t.lower() for t in valid_topics]:
        return False, f"Unknown topic: {topic}"
    
    return True, None


def validate_rating(rating: int) -> Tuple[bool, Optional[str]]:
    """
    Validate rating value.
    
    Args:
        rating: The rating to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(rating, int):
        return False, "Rating must be an integer"
    
    if rating < 0:
        return False, "Rating cannot be negative"
    
    if rating > 4000:
        return False, "Rating exceeds maximum (4000)"
    
    return True, None


def validate_rating_offset(offset: int) -> Tuple[bool, Optional[str]]:
    """
    Validate rating offset value.
    
    Args:
        offset: The offset to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(offset, int):
        return False, "Offset must be an integer"
    
    if abs(offset) > 500:
        return False, "Offset must be between -500 and 500"
    
    return True, None


def sanitize_handle(handle: str) -> str:
    """
    Sanitize a CF handle by stripping whitespace.
    
    Args:
        handle: Raw handle input
        
    Returns:
        Sanitized handle
    """
    return handle.strip() if handle else ""


def sanitize_topic(topic: str) -> str:
    """
    Sanitize a topic by stripping whitespace and lowercasing.
    
    Args:
        topic: Raw topic input
        
    Returns:
        Sanitized topic
    """
    return topic.strip().lower() if topic else ""
