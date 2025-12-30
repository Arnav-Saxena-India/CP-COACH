"""
Unit Tests for Scoring Logic.
"""

import pytest
from app.scoring import (
    calculate_weakness_score,
    aggregate_topic_weakness,
    rank_weak_topics,
    calculate_problem_impact_score,
)


class TestWeaknessScoring:
    """Tests for weakness score calculation."""
    
    def test_no_attempts_returns_zero(self):
        """No attempts should return zero weakness."""
        score = calculate_weakness_score(
            attempts=0, successes=0, 
            problem_rating=1200, user_rating=1000
        )
        assert score == 0.0
        
    def test_all_success_returns_zero(self):
        """All successful attempts should return zero weakness."""
        score = calculate_weakness_score(
            attempts=5, successes=5,
            problem_rating=1200, user_rating=1000
        )
        assert score == 0.0
        
    def test_failure_increases_score(self):
        """Failures should increase weakness score."""
        score = calculate_weakness_score(
            attempts=5, successes=2,
            problem_rating=1200, user_rating=1000
        )
        assert score > 0.0
        
    def test_harder_problems_higher_weight(self):
        """Failing harder problems should have higher weight."""
        easy_problem_score = calculate_weakness_score(
            attempts=5, successes=2,
            problem_rating=1000, user_rating=1200
        )
        hard_problem_score = calculate_weakness_score(
            attempts=5, successes=2,
            problem_rating=1500, user_rating=1200
        )
        assert hard_problem_score > easy_problem_score
        
    def test_time_decay_reduces_score(self):
        """Recent failures should have higher weight than old ones."""
        recent_score = calculate_weakness_score(
            attempts=5, successes=2,
            problem_rating=1200, user_rating=1000,
            days_ago=0.0
        )
        old_score = calculate_weakness_score(
            attempts=5, successes=2,
            problem_rating=1200, user_rating=1000,
            days_ago=30.0
        )
        assert recent_score > old_score


class TestTopicAggregation:
    """Tests for topic weakness aggregation."""
    
    def test_empty_submissions(self):
        """Empty submissions should return empty dict."""
        result = aggregate_topic_weakness([], user_rating=1000)
        assert result == {}
        
    def test_aggregates_by_topic(self, sample_cf_submissions):
        """Should aggregate scores by topic."""
        result = aggregate_topic_weakness(sample_cf_submissions, user_rating=1200)
        
        # Should have topics from the submissions
        assert "greedy" in result or "dp" in result or "implementation" in result
        
    def test_tracks_attempts_and_successes(self, sample_cf_submission):
        """Should track attempt and success counts."""
        result = aggregate_topic_weakness([sample_cf_submission], user_rating=1000)
        
        topic_stats = list(result.values())[0]
        assert topic_stats["attempts"] > 0
        assert topic_stats["successes"] >= 0


class TestWeakTopicRanking:
    """Tests for weak topic ranking."""
    
    def test_ranks_by_score_descending(self):
        """Topics should be ranked by score descending."""
        topic_scores = {
            "dp": {"score": 0.5, "attempts": 10, "successes": 5},
            "greedy": {"score": 0.8, "attempts": 10, "successes": 2},
            "math": {"score": 0.3, "attempts": 10, "successes": 7},
        }
        
        ranked = rank_weak_topics(topic_scores, min_attempts=5)
        
        # Highest score first
        assert ranked[0][0] == "greedy"
        assert ranked[1][0] == "dp"
        assert ranked[2][0] == "math"
        
    def test_filters_by_min_attempts(self):
        """Topics with too few attempts should be filtered."""
        topic_scores = {
            "dp": {"score": 0.5, "attempts": 10, "successes": 5},
            "rare_topic": {"score": 0.9, "attempts": 1, "successes": 0},
        }
        
        ranked = rank_weak_topics(topic_scores, min_attempts=5)
        
        # rare_topic should be filtered out
        topics = [t[0] for t in ranked]
        assert "rare_topic" not in topics
        assert "dp" in topics


class TestImpactScoring:
    """Tests for problem impact score calculation."""
    
    def test_weak_topic_match_increases_score(self):
        """Problems matching weak topics should have higher impact."""
        problem = {"tags": "dp,implementation", "rating": 1200}
        
        score_with_match = calculate_problem_impact_score(
            problem, weak_topics=["dp"], weak_rating_bands=[], user_rating=1000
        )
        score_without_match = calculate_problem_impact_score(
            problem, weak_topics=["graphs"], weak_rating_bands=[], user_rating=1000
        )
        
        assert score_with_match > score_without_match
        
    def test_rating_band_match_increases_score(self):
        """Problems in weak rating bands should have higher impact."""
        problem = {"tags": "dp", "rating": 1200}
        
        score_with_match = calculate_problem_impact_score(
            problem, weak_topics=[], 
            weak_rating_bands=[(1100, 1300)], user_rating=1000
        )
        score_without_match = calculate_problem_impact_score(
            problem, weak_topics=[], 
            weak_rating_bands=[(1500, 1700)], user_rating=1000
        )
        
        assert score_with_match > score_without_match
