"""
Unit Tests for CF Data Parsing.
"""

import pytest
from app.config import normalize_tag, normalize_tags, get_rating_bucket


class TestTagNormalization:
    """Tests for tag normalization functions."""
    
    def test_normalize_common_tags(self):
        """Test normalization of commonly used tags."""
        assert normalize_tag("dp") == "dp"
        assert normalize_tag("dynamic programming") == "dp"
        assert normalize_tag("DP") == "dp"
        
    def test_normalize_graph_tags(self):
        """Test graph-related tag normalization."""
        assert normalize_tag("graphs") == "graphs"
        assert normalize_tag("graph") == "graphs"
        
    def test_normalize_ds_tags(self):
        """Test data structure tag normalization."""
        assert normalize_tag("data structures") == "data structures"
        assert normalize_tag("ds") == "data structures"
        
    def test_normalize_unknown_tag(self):
        """Test that unknown tags pass through lowercased."""
        assert normalize_tag("Some New Tag") == "some new tag"
        assert normalize_tag("CUSTOM") == "custom"
        
    def test_normalize_tags_string(self):
        """Test normalization of comma-separated tag string."""
        result = normalize_tags("dp,graphs,implementation")
        assert "dp" in result
        assert "graphs" in result
        assert "implementation" in result
        
    def test_normalize_tags_removes_duplicates(self):
        """Test that duplicate tags are removed."""
        result = normalize_tags("dp,dynamic programming,dp")
        # Should only have "dp" once
        assert result.count("dp") == 1
        
    def test_normalize_empty_tags(self):
        """Test handling of empty tags string."""
        assert normalize_tags("") == ""
        assert normalize_tags(None) == ""


class TestRatingBucket:
    """Tests for rating bucket classification."""
    
    def test_beginner_bucket(self):
        """Test beginner rating bucket (<1200)."""
        assert get_rating_bucket(800) == "beginner"
        assert get_rating_bucket(1000) == "beginner"
        assert get_rating_bucket(1199) == "beginner"
        
    def test_intermediate_bucket(self):
        """Test intermediate rating bucket (1200-1600)."""
        assert get_rating_bucket(1200) == "intermediate"
        assert get_rating_bucket(1400) == "intermediate"
        assert get_rating_bucket(1599) == "intermediate"
        
    def test_advanced_bucket(self):
        """Test advanced rating bucket (>1600)."""
        assert get_rating_bucket(1600) == "advanced"
        assert get_rating_bucket(1900) == "advanced"
        assert get_rating_bucket(2400) == "advanced"
        
    def test_edge_cases(self):
        """Test edge cases for bucket boundaries."""
        assert get_rating_bucket(0) == "beginner"
        assert get_rating_bucket(4000) == "advanced"
