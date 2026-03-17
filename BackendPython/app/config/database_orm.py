# app/config/database_orm.py
"""
SQLAlchemy database configuration for ORM operations
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/kltn")

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True to see SQL queries
    poolclass=NullPool,  # Disable connection pooling for simplicity
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for all ORM models
Base = declarative_base()

# Import all models after Base is defined
# This ensures SQLAlchemy knows about all models for create_all()
from app.models.user_models import Category, User, SearchHistory, UserPreferences  # noqa: F401, E402


def get_db():
    """Dependency injection for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
