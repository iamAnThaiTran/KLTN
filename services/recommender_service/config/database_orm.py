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

# Construct DATABASE_URL from environment variables
# Docker Compose provides: DB_HOST, DB_PORT, POSTGRES_USER, POSTGRES_PASSWORD
# Or single DATABASE_URL can be provided
db_host = os.getenv("DB_HOST", "localhost")
db_port = os.getenv("DB_PORT", "5432")
db_user = os.getenv("POSTGRES_USER", "user")
db_password = os.getenv("POSTGRES_PASSWORD", "password")
db_name = os.getenv("DB_NAME", "kltn")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
)

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
from models.user_models import Category, User, SearchHistory, UserPreferences  # ✅ LOCAL - noqa: F401, E402


def get_db():
    """Dependency injection for database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
