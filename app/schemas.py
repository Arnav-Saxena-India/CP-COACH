"""
Pydantic schemas for request/response validation.
Defines data transfer objects for API endpoints.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# ============ User Schemas ============

class UserBase(BaseModel):
    """Base schema for user data."""
    handle: str


class UserResponse(BaseModel):
    """Response schema for user profile."""
    id: int
    handle: str
    rating: int
    daily_solved_count: int = 0
    created_at: datetime
    last_problem_solved: bool

    class Config:
        from_attributes = True


# ============ Problem Schemas ============

class ProblemBase(BaseModel):
    """Base schema for problem data."""
    name: str
    rating: int
    tags: str
    url: str


class ProblemResponse(BaseModel):
    """Response schema for a single problem."""
    id: int
    name: str
    rating: int
    tags: str
    url: str

    class Config:
        from_attributes = True


class ProblemWithExplanation(BaseModel):
    """Response schema for a recommended problem with explanation."""
    id: int
    name: str
    rating: int
    tags: str
    url: str
    explanation: str


# ============ Recommendation Schemas ============

class RecommendationResponse(BaseModel):
    """Response schema for problem recommendations."""
    target_rating: int
    message: Optional[str] = None
    problems: List[ProblemWithExplanation]
    daily_count: Optional[int] = None  # Problems solved today


# ============ Error Schemas ============

class ErrorResponse(BaseModel):
    """Schema for error responses."""
    detail: str
