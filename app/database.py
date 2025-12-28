"""
Database configuration module.
Sets up SQLAlchemy with SQLite for local development.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os

# Database URL from environment or local SQLite fallback
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cp_coach.db")

# Fix for Railway/Heroku "postgres://" scheme which SQLAlchemy 1.4+ deprecated
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Session factory for database operations
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """
    Dependency function to get database session.
    Yields a session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def run_migrations(engine):
    """
    Simple migration script to update SQLite schema if columns are missing.
    Useful for Render deployments where we can't easily run Alembic.
    """
    from sqlalchemy import text
    import logging
    
    logger = logging.getLogger(__name__)

    with engine.connect() as conn:
        # Check solved_problems table
        try:
            # SQLite specific pragmas to check columns
            columns = conn.execute(text("PRAGMA table_info(solved_problems)")).fetchall()
            col_names = [col[1] for col in columns]
            
            if 'time_taken_seconds' not in col_names:
                logger.info("Migrating: Adding time_taken_seconds to solved_problems")
                conn.execute(text("ALTER TABLE solved_problems ADD COLUMN time_taken_seconds INTEGER"))
                
            if 'is_slow_solve' not in col_names:
                logger.info("Migrating: Adding is_slow_solve to solved_problems")
                conn.execute(text("ALTER TABLE solved_problems ADD COLUMN is_slow_solve BOOLEAN"))
                
        except Exception as e:
            logger.warning(f"Migration check failed for solved_problems: {e}")

        # Check skipped_problems table
        try:
            columns = conn.execute(text("PRAGMA table_info(skipped_problems)")).fetchall()
            col_names = [col[1] for col in columns]
            
            if 'feedback' not in col_names:
                logger.info("Migrating: Adding feedback to skipped_problems")
                conn.execute(text("ALTER TABLE skipped_problems ADD COLUMN feedback VARCHAR"))
                
        except Exception as e:
            logger.warning(f"Migration check failed for skipped_problems: {e}")

        # Check user_skills table
        try:
            columns = conn.execute(text("PRAGMA table_info(user_skills)")).fetchall()
            col_names = [col[1] for col in columns]
            
            if 'max_solved_rating' not in col_names:
                logger.info("Migrating: Adding max_solved_rating to user_skills")
                conn.execute(text("ALTER TABLE user_skills ADD COLUMN max_solved_rating INTEGER DEFAULT 0"))
                
        except Exception as e:
            logger.warning(f"Migration check failed for user_skills: {e}")
            
        conn.commit()
