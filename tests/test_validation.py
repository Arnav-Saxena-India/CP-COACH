"""
Unit Tests for Input Validation.
"""

import pytest
from app.validation import (
    validate_cf_handle,
    validate_topic,
    validate_rating,
    validate_rating_offset,
    sanitize_handle,
    sanitize_topic,
)


class TestHandleValidation:
    """Tests for CF handle validation."""
    
    def test_valid_handles(self):
        """Test various valid handle formats."""
        valid_handles = ["tourist", "Petr", "user_123", "user-name", "abc"]
        
        for handle in valid_handles:
            is_valid, error = validate_cf_handle(handle)
            assert is_valid, f"Handle '{handle}' should be valid, got error: {error}"
            
    def test_empty_handle(self):
        """Empty handle should be invalid."""
        is_valid, error = validate_cf_handle("")
        assert not is_valid
        assert "empty" in error.lower()
        
    def test_handle_too_short(self):
        """Handle shorter than 3 chars should be invalid."""
        is_valid, error = validate_cf_handle("ab")
        assert not is_valid
        assert "3" in error
        
    def test_handle_too_long(self):
        """Handle longer than 24 chars should be invalid."""
        is_valid, error = validate_cf_handle("a" * 25)
        assert not is_valid
        assert "24" in error
        
    def test_invalid_characters(self):
        """Handle with special characters should be invalid."""
        invalid_handles = ["user@name", "user name", "user.name", "user#123"]
        
        for handle in invalid_handles:
            is_valid, error = validate_cf_handle(handle)
            assert not is_valid, f"Handle '{handle}' should be invalid"


class TestTopicValidation:
    """Tests for topic validation."""
    
    def test_valid_topics(self):
        """Test various valid topic formats."""
        valid_topics = ["dp", "dynamic programming", "two-pointers", "graphs"]
        
        for topic in valid_topics:
            is_valid, error = validate_topic(topic)
            assert is_valid, f"Topic '{topic}' should be valid"
            
    def test_empty_topic(self):
        """Empty topic should be invalid."""
        is_valid, error = validate_topic("")
        assert not is_valid
        
    def test_topic_too_short(self):
        """Topic shorter than 2 chars should be invalid."""
        is_valid, error = validate_topic("a")
        assert not is_valid


class TestRatingValidation:
    """Tests for rating validation."""
    
    def test_valid_ratings(self):
        """Test valid rating values."""
        valid_ratings = [0, 800, 1200, 2000, 3500]
        
        for rating in valid_ratings:
            is_valid, error = validate_rating(rating)
            assert is_valid, f"Rating {rating} should be valid"
            
    def test_negative_rating(self):
        """Negative rating should be invalid."""
        is_valid, error = validate_rating(-100)
        assert not is_valid
        
    def test_rating_too_high(self):
        """Rating above 4000 should be invalid."""
        is_valid, error = validate_rating(5000)
        assert not is_valid


class TestRatingOffsetValidation:
    """Tests for rating offset validation."""
    
    def test_valid_offsets(self):
        """Test valid offset values."""
        valid_offsets = [-500, -100, 0, 100, 500]
        
        for offset in valid_offsets:
            is_valid, error = validate_rating_offset(offset)
            assert is_valid, f"Offset {offset} should be valid"
            
    def test_offset_too_large(self):
        """Offset larger than ±500 should be invalid."""
        is_valid, error = validate_rating_offset(600)
        assert not is_valid
        
        is_valid, error = validate_rating_offset(-600)
        assert not is_valid


class TestSanitization:
    """Tests for input sanitization functions."""
    
    def test_sanitize_handle_strips_whitespace(self):
        """Handle sanitization should strip whitespace."""
        assert sanitize_handle("  tourist  ") == "tourist"
        assert sanitize_handle("Petr\n") == "Petr"
        
    def test_sanitize_topic_lowercases(self):
        """Topic sanitization should lowercase."""
        assert sanitize_topic("DP") == "dp"
        assert sanitize_topic("  GRAPHS  ") == "graphs"
        
    def test_sanitize_handles_none(self):
        """Sanitization should handle None gracefully."""
        assert sanitize_handle(None) == ""
        assert sanitize_topic(None) == ""
