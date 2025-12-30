"""
Test Configuration and Fixtures for CP Coach.
"""

import pytest
import sys
import os

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_cf_submission():
    """Sample Codeforces submission for testing."""
    return {
        "id": 123456789,
        "contestId": 1900,
        "problem": {
            "contestId": 1900,
            "index": "A",
            "name": "Cover in Water",
            "rating": 800,
            "tags": ["greedy", "implementation"]
        },
        "verdict": "OK",
        "creationTimeSeconds": 1700000000
    }


@pytest.fixture
def sample_cf_submissions():
    """Multiple submissions for testing."""
    return [
        {
            "id": 1,
            "contestId": 1900,
            "problem": {"contestId": 1900, "index": "A", "name": "Problem A", "rating": 800, "tags": ["greedy"]},
            "verdict": "OK",
            "creationTimeSeconds": 1700000000
        },
        {
            "id": 2,
            "contestId": 1900,
            "problem": {"contestId": 1900, "index": "B", "name": "Problem B", "rating": 1200, "tags": ["dp"]},
            "verdict": "WRONG_ANSWER",
            "creationTimeSeconds": 1700001000
        },
        {
            "id": 3,
            "contestId": 1901,
            "problem": {"contestId": 1901, "index": "A", "name": "Problem C", "rating": 1000, "tags": ["implementation"]},
            "verdict": "OK",
            "creationTimeSeconds": 1700002000
        },
    ]


@pytest.fixture
def empty_cf_data():
    """Empty Codeforces data for testing edge cases."""
    return []


@pytest.fixture
def heavy_cf_data():
    """Large dataset for performance testing."""
    data = []
    tags = ["dp", "greedy", "implementation", "math", "graphs", "strings"]
    for i in range(1000):
        data.append({
            "id": i,
            "contestId": 1000 + (i % 100),
            "problem": {
                "contestId": 1000 + (i % 100),
                "index": chr(65 + (i % 6)),
                "name": f"Problem {i}",
                "rating": 800 + (i % 16) * 100,
                "tags": [tags[i % len(tags)]]
            },
            "verdict": "OK" if i % 3 == 0 else "WRONG_ANSWER",
            "creationTimeSeconds": 1700000000 + i * 100
        })
    return data


@pytest.fixture
def sample_user_info():
    """Sample user info from CF API."""
    return {
        "handle": "testuser",
        "rating": 1500,
        "maxRating": 1600,
        "rank": "specialist",
        "maxRank": "expert"
    }
