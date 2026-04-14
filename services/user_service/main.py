"""
UserService - Microservice for user management and personalization
Port: 8004

Handles:
- User authentication and profiles
- User preferences and settings
- Search history tracking
- Favorites and wishlists
- Price alerts
- Product reviews
- Comparison history
"""

from fastapi import FastAPI, HTTPException, Body, Query
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import datetime
import uuid
from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# ============================================================================
# Environment Configuration
# ============================================================================

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = "user_db"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ============================================================================
# Password Hashing
# ============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ============================================================================
# FastAPI Setup
# ============================================================================

app = FastAPI(
    title="UserService",
    description="Microservice for user management and personalization",
    version="1.0.0"
)

# CORS is handled by API Gateway (nginx)
# Don't add CORS middleware here to avoid duplicate headers

# ============================================================================
# Database Setup
# ============================================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# Data Models (SQLAlchemy)
# ============================================================================

from sqlalchemy import Column, Integer, String, Float, Text, TIMESTAMP, Boolean, JSON, ARRAY, DECIMAL
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), unique=True)
    username = Column(String(255), unique=True, nullable=True)
    email = Column(String(255), unique=True)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255))
    phone = Column(String(20))
    provider = Column(String(50), default="local")  # local, google, facebook, etc.
    provider_id = Column(String(255))
    oauth_provider = Column(String(50), nullable=True)  # google, facebook, etc.
    oauth_id = Column(String(255), nullable=True, unique=True)
    oauth_token = Column(String(2000), nullable=True)  # JWT tokens can be long
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    last_login = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)

class UserPreference(Base):
    __tablename__ = "user_preferences"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), unique=True)
    language = Column(String(20), default="en")
    preferred_currency = Column(String(10), default="USD")
    price_range_min = Column(Float)
    price_range_max = Column(Float)
    categories = Column(ARRAY(String))
    brands = Column(ARRAY(String))
    notification_email = Column(Boolean, default=True)
    notification_push = Column(Boolean, default=False)
    notification_sms = Column(Boolean, default=False)
    dark_mode = Column(Boolean, default=False)
    comparison_limit = Column(Integer, default=5)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)

class SearchHistory(Base):
    __tablename__ = "search_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))
    query = Column(String(500))
    category = Column(String(255))
    query_type = Column(String(50))
    filters = Column(JSON)
    results_count = Column(Integer)
    selected_product_id = Column(String(100))
    searched_at = Column(TIMESTAMP, default=datetime.utcnow)

class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))
    product_id = Column(String(100))
    sku_id = Column(String(100))
    added_to_wishlist = Column(Boolean, default=False)
    price_when_added = Column(Float)
    current_price = Column(Float)
    added_at = Column(TIMESTAMP, default=datetime.utcnow)

class PriceAlert(Base):
    __tablename__ = "price_alerts"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))
    product_id = Column(String(100))
    target_price = Column(Float)
    current_price = Column(Float)
    alert_type = Column(String(50))
    is_active = Column(Boolean, default=True)
    triggered_count = Column(Integer, default=0)
    last_triggered = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

class UserReview(Base):
    __tablename__ = "user_reviews"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))
    product_id = Column(String(100))
    sku_id = Column(String(100))
    rating = Column(Integer)
    review_text = Column(Text)
    review_images = Column(ARRAY(String))
    helpful_count = Column(Integer, default=0)
    unhelpful_count = Column(Integer, default=0)
    verified_purchase = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)

class ComparisonHistory(Base):
    __tablename__ = "comparison_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))
    comparison_id = Column(String(100))
    product_ids = Column(ARRAY(String))
    comparison_date = Column(TIMESTAMP, default=datetime.utcnow)
    winning_product_id = Column(String(100))
    action = Column(String(50))
    metadata_info = Column(JSON)

# ============================================================================
# Create all tables
# ============================================================================
try:
    Base.metadata.create_all(engine)
except Exception as e:
    logger.error(f"Error creating tables: {e}")

# ============================================================================
# Health Check
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Service health check endpoint"""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "UserService",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

# ============================================================================
# User Profile APIs
# ============================================================================

@app.get("/api/users/{user_id}")
async def get_user(user_id: str):
    """Get user profile information"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "user_id": user.user_id,
            "email": user.email,
            "full_name": user.full_name,
            "provider": user.provider,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    except Exception as e:
        logger.error(f"Get user failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/users")
async def create_user(
    email: str = Body(..., embed=True),
    full_name: Optional[str] = Body(None, embed=True),
    password: Optional[str] = Body(None, embed=True),
    provider: str = Body("local", embed=True),
    provider_id: Optional[str] = Body(None, embed=True)
):
    """Create a new user account"""
    db = SessionLocal()
    try:
        # Generate unique user ID
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        
        # Check if email already exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Hash password if provided
        hashed_password = pwd_context.hash(password) if password else None
        
        user = User(
            user_id=user_id,
            email=email,
            full_name=full_name or "",
            hashed_password=hashed_password,
            provider=provider,
            provider_id=provider_id,
            is_active=True
        )
        db.add(user)
        
        # Create preferences record
        prefs = UserPreference(user_id=user_id)
        db.add(prefs)
        
        db.commit()
        
        return {
            "user_id": user_id,
            "email": email,
            "status": "created"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Create user failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/api/users/{user_id}")
async def update_user(user_id: str, update_data: Dict[str, Any] = Body(...)):
    """Update user profile"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        for key, value in update_data.items():
            if hasattr(user, key) and key not in ["user_id", "hashed_password"]:
                setattr(user, key, value)
        
        user.updated_at = datetime.utcnow()
        db.commit()
        
        return {"status": "updated", "user_id": user_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Update user failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# User Preferences APIs
# ============================================================================

@app.get("/api/users/{user_id}/preferences")
async def get_preferences(user_id: str):
    """Get user preferences and settings"""
    db = SessionLocal()
    try:
        prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        if not prefs:
            raise HTTPException(status_code=404, detail="Preferences not found")
        
        return {
            "language": prefs.language,
            "currency": prefs.preferred_currency,
            "categories": prefs.categories or [],
            "brands": prefs.brands or [],
            "notifications": {
                "email": prefs.notification_email,
                "push": prefs.notification_push,
                "sms": prefs.notification_sms
            }
        }
    except Exception as e:
        logger.error(f"Get preferences failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/api/users/{user_id}/preferences")
async def update_preferences(user_id: str, preferences: Dict[str, Any] = Body(...)):
    """Update user preferences"""
    db = SessionLocal()
    try:
        prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        if not prefs:
            raise HTTPException(status_code=404, detail="Preferences not found")
        
        for key, value in preferences.items():
            if hasattr(prefs, key):
                setattr(prefs, key, value)
        
        prefs.updated_at = datetime.utcnow()
        db.commit()
        
        return {"status": "updated", "user_id": user_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Update preferences failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Search History APIs
# ============================================================================

@app.post("/api/users/{user_id}/search-history")
async def record_search(
    user_id: str,
    query: str = Body(..., embed=True),
    category: Optional[str] = Body(None, embed=True),
    filters: Optional[Dict[str, Any]] = Body(None, embed=True),
    results_count: int = Body(0, embed=True)
):
    """Record a search in user history"""
    db = SessionLocal()
    try:
        search = SearchHistory(
            user_id=user_id,
            query=query,
            category=category,
            filters=filters,
            results_count=results_count
        )
        db.add(search)
        db.commit()
        
        return {"status": "recorded"}
    except Exception as e:
        db.rollback()
        logger.error(f"Record search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/users/{user_id}/search-history")
async def get_search_history(user_id: str, limit: int = 20, offset: int = 0):
    """Get user's search history"""
    db = SessionLocal()
    try:
        searches = db.query(SearchHistory).filter(
            SearchHistory.user_id == user_id
        ).order_by(SearchHistory.searched_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "searches": [
                {
                    "query": s.query,
                    "category": s.category,
                    "searched_at": s.searched_at.isoformat() if s.searched_at else None
                }
                for s in searches
            ]
        }
    except Exception as e:
        logger.error(f"Get search history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Favorites / Wishlist APIs
# ============================================================================

@app.post("/api/users/{user_id}/favorites")
async def add_favorite(
    user_id: str,
    product_id: str = Body(..., embed=True),
    sku_id: Optional[str] = Body(None, embed=True),
    price: Optional[float] = Body(None, embed=True)
):
    """Add product to user's wishlist"""
    db = SessionLocal()
    try:
        favorite = Favorite(
            user_id=user_id,
            product_id=product_id,
            sku_id=sku_id,
            price_when_added=price
        )
        db.add(favorite)
        db.commit()
        
        return {"status": "added", "product_id": product_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Add favorite failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/api/users/{user_id}/favorites/{product_id}")
async def remove_favorite(user_id: str, product_id: str):
    """Remove product from favorites"""
    db = SessionLocal()
    try:
        favorite = db.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.product_id == product_id
        ).first()
        if favorite:
            db.delete(favorite)
            db.commit()
        
        return {"status": "removed", "product_id": product_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Remove favorite failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/users/{user_id}/favorites")
async def get_favorites(user_id: str, limit: int = 20, offset: int = 0):
    """Get user's favorite products"""
    db = SessionLocal()
    try:
        favorites = db.query(Favorite).filter(
            Favorite.user_id == user_id
        ).offset(offset).limit(limit).all()
        
        return {
            "favorites": [
                {
                    "product_id": f.product_id,
                    "added_at": f.added_at.isoformat() if f.added_at else None
                }
                for f in favorites
            ]
        }
    except Exception as e:
        logger.error(f"Get favorites failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Review APIs
# ============================================================================

@app.post("/api/users/{user_id}/reviews")
async def submit_review(
    user_id: str,
    product_id: str = Body(..., embed=True),
    rating: int = Body(..., embed=True),
    review_text: Optional[str] = Body(None, embed=True),
    images: Optional[List[str]] = Body(None, embed=True),
    sku_id: Optional[str] = Body(None, embed=True)
):
    """Submit a product review"""
    db = SessionLocal()
    try:
        review = UserReview(
            user_id=user_id,
            product_id=product_id,
            sku_id=sku_id,
            rating=rating,
            review_text=review_text,
            review_images=images
        )
        db.add(review)
        db.commit()
        
        return {"status": "submitted"}
    except Exception as e:
        db.rollback()
        logger.error(f"Submit review failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/users/{user_id}/reviews")
async def get_user_reviews(user_id: str, limit: int = 20, offset: int = 0):
    """Get reviews submitted by user"""
    db = SessionLocal()
    try:
        reviews = db.query(UserReview).filter(
            UserReview.user_id == user_id
        ).offset(offset).limit(limit).all()
        
        return {
            "reviews": [
                {
                    "product_id": r.product_id,
                    "rating": r.rating,
                    "review_text": r.review_text
                }
                for r in reviews
            ]
        }
    except Exception as e:
        logger.error(f"Get reviews failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Comparison History APIs
# ============================================================================

@app.post("/api/users/{user_id}/comparisons")
async def record_comparison(
    user_id: str,
    comparison_id: str = Body(..., embed=True),
    product_ids: List[str] = Body(..., embed=True),
    winning_product_id: Optional[str] = Body(None, embed=True)
):
    """Record a product comparison"""
    db = SessionLocal()
    try:
        comparison = ComparisonHistory(
            user_id=user_id,
            comparison_id=comparison_id,
            product_ids=product_ids,
            winning_product_id=winning_product_id
        )
        db.add(comparison)
        db.commit()
        
        return {"status": "recorded"}
    except Exception as e:
        db.rollback()
        logger.error(f"Record comparison failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/users/{user_id}/comparisons")
async def get_comparison_history(user_id: str, limit: int = 20, offset: int = 0):
    """Get user's comparison history"""
    db = SessionLocal()
    try:
        comparisons = db.query(ComparisonHistory).filter(
            ComparisonHistory.user_id == user_id
        ).order_by(ComparisonHistory.comparison_date.desc()).offset(offset).limit(limit).all()
        
        return {
            "comparisons": [
                {
                    "comparison_id": c.comparison_id,
                    "products_compared": len(c.product_ids) if c.product_ids else 0,
                    "comparison_date": c.comparison_date.isoformat() if c.comparison_date else None
                }
                for c in comparisons
            ]
        }
    except Exception as e:
        logger.error(f"Get comparison history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Startup and Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("UserService starting up...")
    import asyncio
    max_retries = 10
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            with SessionLocal() as db:
                db.execute(text("SELECT 1"))
            logger.info("Database connection verified")
            return
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Database connection failed (attempt {attempt + 1}/{max_retries}): {e}")
                await asyncio.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to database after {max_retries} attempts: {e}")
                raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("UserService shutting down...")
    engine.dispose()

# ============================================================================
# Include Auth Routes
# ============================================================================

from auth_routes import router as auth_router
app.include_router(auth_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8004,
        reload=False,
        log_level="info"
    )
