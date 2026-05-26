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

from fastapi import FastAPI, HTTPException, Body, Query, Request
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

from sqlalchemy import Column, Integer, String, Float, Text, TIMESTAMP, Boolean, JSON, ARRAY, DECIMAL, func
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
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now())

class SearchHistory(Base):
    __tablename__ = "search_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), nullable=False)
    query = Column(String(500))
    category = Column(String(255))
    query_type = Column(String(50))
    filters = Column(JSON)
    results_count = Column(Integer)
    selected_product_id = Column(String(100))
    searched_at = Column(TIMESTAMP, default=func.now())

class Favorite(Base):
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))
    product_id = Column(String(100))
    sku_id = Column(String(100))
    added_to_wishlist = Column(Boolean, default=False)
    price_when_added = Column(Float)
    current_price = Column(Float)
    added_at = Column(TIMESTAMP, default=func.now())

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
    created_at = Column(TIMESTAMP, default=func.now())

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
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now())

class ComparisonHistory(Base):
    __tablename__ = "comparison_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100))
    comparison_id = Column(String(100))
    product_ids = Column(ARRAY(String))
    comparison_date = Column(TIMESTAMP, default=func.now())
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
    email: str = Body(...),
    full_name: Optional[str] = Body(None),
    password: Optional[str] = Body(None),
    provider: str = Body("local"),
    provider_id: Optional[str] = Body(None)
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
    query: str = Body(...),
    category: Optional[str] = Body(None),
    filters: Optional[Dict[str, Any]] = Body(None),
    results_count: int = Body(0)
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
    product_id: str = Body(...),
    sku_id: Optional[str] = Body(None),
    price: Optional[float] = Body(None)
):
    """Add product to user's favorites"""
    db = SessionLocal()
    try:
        # Check if already favorited
        existing = db.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.product_id == product_id
        ).first()
        
        if existing:
            return {
                "success": True,
                "user_id": user_id,
                "product_id": product_id,
                "is_favorite": True,
                "added_at": existing.added_at.isoformat() if existing.added_at else None,
                "message": "Already in favorites"
            }
        
        favorite = Favorite(
            user_id=user_id,
            product_id=product_id,
            sku_id=sku_id,
            price_when_added=price
        )
        db.add(favorite)
        db.commit()
        db.refresh(favorite)
        
        return {
            "success": True,
            "user_id": user_id,
            "product_id": product_id,
            "is_favorite": True,
            "added_at": favorite.added_at.isoformat() if favorite.added_at else None
        }
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
        
        if not favorite:
            raise HTTPException(status_code=404, detail="Favorite not found")
        
        db.delete(favorite)
        db.commit()
        
        return {
            "success": True,
            "user_id": user_id,
            "product_id": product_id,
            "is_favorite": False
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Remove favorite failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/users/{user_id}/favorites")
async def get_favorites(user_id: str, limit: int = 50, offset: int = 0):
    """Get user's favorite products"""
    db = SessionLocal()
    try:
        # Query total count
        total_query = db.query(Favorite).filter(Favorite.user_id == user_id)
        total = total_query.count()
        
        # Query with pagination
        favorites = total_query.order_by(Favorite.added_at.desc()).offset(offset).limit(limit).all()
        
        # Fetch product details from Product Service
        import httpx
        import time
        
        favorites_with_products = []
        
        for fav in favorites:
            product = None
            try:
                # Call product service to get product details (synchronous)
                response = httpx.get(
                    f"http://product-service:8001/api/products/{fav.product_id}",
                    timeout=10.0,
                    headers={"Accept": "application/json"}
                )
                if response.status_code == 200:
                    product = response.json()
                else:
                    logger.warning(f"Product service returned {response.status_code} for product {fav.product_id}")
            except httpx.TimeoutException:
                logger.warning(f"Timeout fetching product {fav.product_id}")
            except httpx.ConnectError as e:
                logger.warning(f"Connection error to product service: {e}")
            except Exception as e:
                logger.warning(f"Failed to fetch product {fav.product_id}: {e}")
            
            favorites_with_products.append({
                "id": fav.id,
                "user_id": fav.user_id,
                "product_id": fav.product_id,
                "added_at": fav.added_at.isoformat() if fav.added_at else None,
                "product": product
            })
        
        return {
            "user_id": user_id,
            "total": total,
            "count": len(favorites_with_products),
            "limit": limit,
            "offset": offset,
            "favorites": favorites_with_products
        }
    except Exception as e:
        logger.error(f"Get favorites failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/users/{user_id}/favorites/{product_id}/status")
async def check_favorite_status(user_id: str, product_id: str):
    """Check if a product is in user's favorites"""
    db = SessionLocal()
    try:
        favorite = db.query(Favorite).filter(
            Favorite.user_id == user_id,
            Favorite.product_id == product_id
        ).first()
        
        return {
            "user_id": user_id,
            "product_id": product_id,
            "is_favorite": favorite is not None
        }
    except Exception as e:
        logger.error(f"Check favorite status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/api/users/{user_id}/favorites")
async def clear_favorites(user_id: str):
    """Clear all favorites for the user"""
    db = SessionLocal()
    try:
        # Delete all favorites for user
        result = db.query(Favorite).filter(Favorite.user_id == user_id).delete()
        db.commit()
        
        return {
            "success": True,
            "user_id": user_id,
            "deleted_count": result
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Clear favorites failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Review APIs
# ============================================================================

@app.post("/api/users/{user_id}/reviews")
async def submit_review(
    user_id: str,
    product_id: str = Body(...),
    rating: int = Body(...),
    review_text: Optional[str] = Body(None),
    images: Optional[List[str]] = Body(None),
    sku_id: Optional[str] = Body(None)
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
    comparison_id: str = Body(...),
    product_ids: List[str] = Body(...),
    winning_product_id: Optional[str] = Body(None)
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
# Recommendation Criteria APIs
# ============================================================================

@app.get("/api/users/me/recommendation-criteria")
async def get_my_recommendation_criteria(
    request: Request,
    days: int = 90
):
    """
    Get recommendation criteria for authenticated user using Authorization header.
    
    This is simpler version of /api/users/{user_id}/recommendation-criteria
    - Extracts user_id from Authorization header
    - No need to pass user_id in URL
    
    For use by Product Service when it receives /api/recommendations/homepage with token
    """
    # Extract Authorization header
    auth_header = request.headers.get("Authorization", "")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")
    
    token = auth_header.replace("Bearer ", "")
    
    # Extract user_id from token
    # Use same JWT_SECRET as auth_routes.py for consistency
    try:
        import jwt
        import os
        
        # Get JWT secret from environment - MUST match auth_routes.py
        # Default: "your-secret-key-change-in-production" (36 bytes - sufficient for HS256)
        jwt_secret = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        
        # Decode token with signature verification
        decoded_token = jwt.decode(token, jwt_secret, algorithms=["HS256"])
        user_id = decoded_token.get("user_id") or decoded_token.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token format - no user_id or sub")
            
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidSignatureError:
        logger.warning(f"Invalid token signature - ensure JWT_SECRET matches across services")
        raise HTTPException(status_code=401, detail="Invalid token signature")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    except Exception as e:
        logger.error(f"Token parsing error: {e}")
        raise HTTPException(status_code=401, detail="Token validation failed")
    
    # Now call the existing function with extracted user_id
    return await get_recommendation_criteria(user_id, days)

@app.get("/api/users/{user_id}/recommendation-criteria")
async def get_recommendation_criteria(user_id: str, days: int = 90):
    """
    Get recommendation criteria for a user based on their behavior.
    
    This endpoint builds recommendation criteria from:
    - Search history (top categories, keywords)
    - Favorite products (preferred brands, categories)
    - User preferences (price range, categories, brands)
    
    Returns:
    {
        "user_id": "user_123",
        "criteria": {
            "top_categories": ["Giày", "Đồng hồ"],
            "top_brands": ["Nike", "Apple"],
            "keywords": ["chạy bộ", "thông minh"],
            "price_range": {"min": 1000000, "max": 50000000},
            "count": {
                "searches": 25,
                "favorites": 5
            }
        },
        "recommendation_type": "personalized",
        "has_history": true
    }
    """
    db = SessionLocal()
    try:
        # Get user preferences
        prefs = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
        
        # Get recent search history (last N days)
        cutoff_date = datetime.utcnow() - __import__('datetime').timedelta(days=days)
        searches = db.query(SearchHistory).filter(
            SearchHistory.user_id == user_id,
            SearchHistory.searched_at >= cutoff_date
        ).all()
        
        # Get favorites
        favorites = db.query(Favorite).filter(Favorite.user_id == user_id).all()
        
        # Extract categories and keywords from search history
        categories_count = {}
        keywords = []
        
        for search in searches:
            if search.category:
                categories_count[search.category] = categories_count.get(search.category, 0) + 1
            if search.query:
                keywords.append(search.query.lower())
        
        # Get top categories
        top_categories = sorted(categories_count.items(), key=lambda x: x[1], reverse=True)
        top_categories_list = [cat[0] for cat in top_categories[:5]]
        
        # Extract brands from searches and preferences
        brands_from_prefs = prefs.brands if prefs and prefs.brands else []
        top_brands = list(set(brands_from_prefs))[:5]
        
        # Deduplicate keywords
        unique_keywords = list(set(keywords))[:5]
        
        # Get price range from preferences
        price_range = {
            "min": float(prefs.price_range_min) if (prefs and prefs.price_range_min) else 0,
            "max": float(prefs.price_range_max) if (prefs and prefs.price_range_max) else 1000000000
        }
        
        # Check if user has any history
        has_history = len(searches) > 0 or len(favorites) > 0
        
        return {
            "user_id": user_id,
            "criteria": {
                "top_categories": top_categories_list,
                "top_brands": top_brands,
                "keywords": unique_keywords,
                "price_range": price_range,
                "count": {
                    "searches": len(searches),
                    "favorites": len(favorites)
                }
            },
            "recommendation_type": "personalized" if has_history else "trending",
            "has_history": has_history
        }
    except Exception as e:
        logger.error(f"[get_recommendation_criteria] Error: {e}")
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
