"""
SQLAlchemy ORM models for the CP Coach application.
Defines User, Problem, and SolvedProblem tables.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    """
    User model representing a Codeforces user.
    Stores handle, rating, and tracks solved problems.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    handle = Column(String, unique=True, index=True, nullable=False)
    rating = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Track if user solved their last recommended problem (for heuristic)
    last_problem_solved = Column(Boolean, default=False)
    
    # Relationship to solved problems
    solved_problems = relationship("SolvedProblem", back_populates="user")


class Problem(Base):
    """
    Problem model representing a competitive programming problem.
    Contains problem metadata and Codeforces link.
    """
    __tablename__ = "problems"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    rating = Column(Integer, nullable=False)
    tags = Column(String, nullable=False)  # Comma-separated tags
    url = Column(String, nullable=False)
    contest_id = Column(Integer, nullable=True)
    problem_index = Column(String, nullable=True)
    
    # Relationship to solved instances
    solved_by = relationship("SolvedProblem", back_populates="problem")


class SolvedProblem(Base):
    """
    Junction table tracking which users have solved which problems.
    Used to filter out already-solved problems from recommendations.
    """
    __tablename__ = "solved_problems"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    solved_at = Column(DateTime, default=datetime.utcnow)
    verdict = Column(String, default="AC")  # "AC" (Accepted) or "WA" (Wrong Answer)
    
    # Relationships
    user = relationship("User", back_populates="solved_problems")
    problem = relationship("Problem", back_populates="solved_by")


class UserSkill(Base):
    """
    Lightweight skill tracking table.
    Tracks solve count and last practice time per topic for each user.
    
    Note: This is a simple counter, not a mastery/skill graph system.
    """
    __tablename__ = "user_skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    topic = Column(String, nullable=False, index=True)  # e.g., "dp", "graphs"
    solve_count = Column(Integer, default=0)  # Number of AC solves for this topic
    last_practiced_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to user
    user = relationship("User", backref="skills")


class SkippedProblem(Base):
    """
    Track problems that users have skipped.
    Used to delay re-recommending skipped problems and auto-mark as solved on repeated skips.
    """
    __tablename__ = "skipped_problems"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    problem_id = Column(Integer, ForeignKey("problems.id"), nullable=False)
    skip_count = Column(Integer, default=1)  # Number of times skipped
    skipped_at = Column(DateTime, default=datetime.utcnow)  # Last skip time
    
    # Relationships
    user = relationship("User", backref="skipped_problems")
    problem = relationship("Problem", backref="skipped_by")


class UserContestProblemStat(Base):
    """
    Track user performance on contest problems.
    Used for weakness detection and upsolving recommendations.
    """
    __tablename__ = "user_contest_problem_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    contest_id = Column(Integer, nullable=False, index=True)
    problem_id = Column(String, nullable=False)  # e.g., "1900A"
    problem_name = Column(String, nullable=True)
    problem_rating = Column(Integer, nullable=True)
    tags = Column(String, nullable=True)  # Comma-separated
    
    # Outcome tracking
    attempted = Column(Boolean, default=False)
    solved = Column(Boolean, default=False)
    attempt_count = Column(Integer, default=0)
    solved_after_contest = Column(Boolean, default=False)
    time_to_ac = Column(Integer, nullable=True)  # Seconds from contest start
    
    # Timestamps
    first_attempt_at = Column(DateTime, nullable=True)
    solved_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", backref="contest_stats")


class UserAnalysisCache(Base):
    """
    Cache for AI-generated weakness analysis explanations.
    Helps avoid rate limits and reduces API costs.
    """
    __tablename__ = "user_analysis_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    summary_hash = Column(String, nullable=True)  # Hash of input data to detect changes
    explanation = Column(String, nullable=False)  # The AI text
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("User", backref="analysis_cache")
