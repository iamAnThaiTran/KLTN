# app/models/user_models.py
"""
SQLAlchemy ORM models for User, SearchHistory, UserPreferences
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Numeric, UniqueConstraint, ARRAY
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
from sqlalchemy.orm import relationship
from app.config.database_orm import Base


class Category(Base):
    """Product category (ORM model for database categories table)"""
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    icon = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Category(id={self.id}, name={self.name}, slug={self.slug})>"


class User(Base):
    """User model for authentication and personalization"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # NULL for OAuth users
    full_name = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    role = Column(String(50), default="user", nullable=False)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    last_login = Column(DateTime, nullable=True)
    # OAuth fields (for Google, Facebook, etc.)
    oauth_provider = Column(String(50), nullable=True)  # 'google', 'facebook'
    oauth_id = Column(String(255), nullable=True, unique=True)  # Provider's user ID
    oauth_token = Column(String(500), nullable=True)  # Access token
    oauth_refresh_token = Column(String(500), nullable=True)  # Refresh token
    oauth_token_expires_at = Column(DateTime, nullable=True)  # Token expiry
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    search_history = relationship("SearchHistory", back_populates="user", cascade="all, delete-orphan")
    user_preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, full_name={self.full_name})>"


class SearchHistory(Base):
    """Search history for each user query"""
    __tablename__ = "search_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    query = Column(String(500), nullable=False)
    category_id = Column(Integer, nullable=True)
    category_name = Column(String(255), nullable=True)  # Cache category name from query result
    result_count = Column(Integer, default=0)
    clicked_product_id = Column(Integer, nullable=True)
    searched_at = Column(DateTime, default=datetime.utcnow, index=True)
    session_id = Column(String(100), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="search_history")

    def __repr__(self):
        return f"<SearchHistory(id={self.id}, user_id={self.user_id}, query={self.query}, category={self.category_name})>"


class UserPreferences(Base):
    """User preferences for personalization and recommendations"""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    # Fixed: Changed from JSON to PostgreSQL native ARRAY to match SQL schema
    preferred_categories = Column(PG_ARRAY(Integer), default=list)  # INT[] in SQL
    preferred_brands = Column(PG_ARRAY(String(255)), default=list)  # TEXT[] in SQL
    price_range_min = Column(Numeric(12, 2), nullable=True)
    price_range_max = Column(Numeric(12, 2), nullable=True)
    notification_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="user_preferences")

    def __repr__(self):
        return f"<UserPreferences(user_id={self.user_id}, categories={self.preferred_categories})>"


class Favorite(Base):
    """User favorite products (wishlist)"""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, nullable=False, index=True)
    added_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="favorites")

    def __repr__(self):
        return f"<Favorite(user_id={self.user_id}, product_id={self.product_id}, added_at={self.added_at})>"
